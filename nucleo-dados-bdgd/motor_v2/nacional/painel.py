"""National panel: one directory {DIST}/{asset}/... holding the checkpointed aggregates of every extraction batch.

Files are copied byte for byte (result.json, {year}/territorial.parquet, {year}/checkpoint.json) and every aggregate is re-hashed
against its checkpoint after the copy, so the comparison loaders (which verify the same hashes) read exactly what was extracted.
The manifest lists the source root of each DIST x asset and the SHA-256 of every aggregate."""
import json
import shutil
from pathlib import Path

from . import LEVEL_A, ROOT_OUT
from ..runner import atomic, digest, read

PANEL = ROOT_OUT / 'painel'


def sources():
    """{(dist, asset): root} from the extraction status (retry root wins for retried UCBT DIST)."""
    st = read(ROOT_OUT / 'extracao' / 'STATUS.json')
    out = {}
    for bid, rec in sorted(st['lotes'].items()):
        et = rec.get('etapas', {})
        u = (et.get('ucbt') or {}).get('root'); a = (et.get('ativos') or {}).get('root')
        retry_ok = set(rec.get('ucbt_retry_ok', [])); r = (et.get('ucbt_retry') or {}).get('root')
        for d in rec['dists']:
            for asset in LEVEL_A:
                root = (r if d in retry_ok else u) if asset == 'ucbt_quantidade' else a
                if root and (Path(root) / str(d) / asset / 'result.json').exists():
                    out[d, asset] = root
    return out


def build():
    PANEL.mkdir(parents=True, exist_ok=True)
    manifest = []
    for (d, asset), root in sorted(sources().items()):
        src = Path(root) / str(d) / asset
        dst = PANEL / str(d) / asset
        res = read(src / 'result.json')
        dst.mkdir(parents=True, exist_ok=True)
        # years without an aggregate (failed extraction) are dropped from the panel copy and listed; aggregates stay byte-identical
        kept = [h for h in res['history'] if (src / str(h['year']) / 'territorial.parquet').exists()]
        for h in res['history']:
            if h not in kept:
                manifest.append(dict(DIST=d, ativo=asset, ano=h['year'], valor=None, item=(h.get('source') or {}).get('item'), origem=str(src),
                                     sha256=None, excluido='sem agregado: ' + str((h.get('qa') or {}).get('error'))))
        atomic(dst / 'result.json', dict(res, history=kept, panel_source=str(src / 'result.json'), panel_source_sha256=digest(src / 'result.json')))
        for h in kept:
            y = str(h['year'])
            (dst / y).mkdir(exist_ok=True)
            for f in ('territorial.parquet', 'checkpoint.json'):
                shutil.copyfile(src / y / f, dst / y / f)
            sha = digest(dst / y / 'territorial.parquet')
            if sha != read(dst / y / 'checkpoint.json')['output_sha256']:
                raise ValueError(f'hash mismatch after copy: {dst / y}')
            manifest.append(dict(DIST=d, ativo=asset, ano=h['year'], valor=h.get('value'), item=(h.get('source') or {}).get('item'),
                                 origem=str(src / y), sha256=sha))
    atomic(PANEL / 'MANIFESTO_PAINEL.json', dict(raiz=str(PANEL), agregados=manifest))
    return PANEL, manifest


def dists_with(asset, min_years=1):
    out = []
    for p in sorted(PANEL.glob(f'*/{asset}/result.json')):
        h = [x for x in read(p)['history'] if x.get('value') is not None]
        if len(h) >= min_years:
            out.append(int(p.parent.parent.name))
    return sorted(out)


if __name__ == '__main__':
    root, m = build()
    print(json.dumps(dict(painel=str(root), agregados=len(m))))
