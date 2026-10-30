"""Local conversion of the contract-selected ZIPs that never reached Parquet (no download; GDB attributes only).

    python -m motor_v2.convert_zips [--only 4950]

The historical pipeline refused these 12 items because BASE.DAT_FNL differs from the competence the inventory attributes to
them. Here they are converted anyway, into a SEPARATE research root (never the ordinary Parquet tree read by the executors),
and classified by what their own BASE and records say:

  competencia_confirmada                       BASE period ends on {year}-12-31            -> usable as the ordinary competence
  competencia_confirmada_data_base_divergente  BASE ends in {year}, not on 12-31            -> quarantine (interval not annual)
  duplicata_da_competencia_Y                   BASE says Y and every entity count equals the ordinary item of Y
  competencia_divergente_Y                     BASE says Y, counts differ from the ordinary item of Y (or none exists)
  competencia_indeterminada                    BASE dates are an extraction date, not a reference period

Only `competencia_confirmada` may enter training; everything else is recorded with its reason and kept out of the panels.
Each layer is streamed GDB -> Parquet and must reproduce the GDB feature count; DIST and DATA_BASE are checked per entity."""
import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import zipfile
from pathlib import Path

import duckdb
import pyarrow.parquet as pq
import pyogrio

HIST = Path('D:/NUCLEO_BDGD_2022_2024')
OUT = Path('D:/NUCLEO_BDGD_2025/motor_v2/conversao_zips_contrato')
INVENTORY = Path('D:/NUCLEO_BDGD_2025/motor_v2/inventario_v2/INVENTARIO_PUBLICACOES_LOCAIS.csv')
VERSION = 'convert-zips-1'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        while b := f.read(8 * 2**20):
            h.update(b)
    return h.hexdigest()


def atomic(p, x):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True); t = p.with_suffix(p.suffix + '.tmp')
    t.write_text(json.dumps(x, ensure_ascii=False, indent=2, default=str), encoding='utf-8'); os.replace(t, p)


def date(v):
    v = str(v or '').strip()
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%Y/%m/%d', '%Y-%m-%d %H:%M:%S'):
        try:
            return dt.datetime.strptime(v, fmt).date()
        except ValueError:
            pass
    return None


def local_zip(year, dist, item):
    """The archive must already be on disk with a matching checksum receipt; nothing is fetched."""
    folder = HIST / 'raw' / str(year) / str(dist) / item
    z, meta = folder / (item + '.zip'), folder / 'download.json'
    if not z.exists() or not meta.exists():
        raise FileNotFoundError('ZIP not available locally; download is not authorised')
    m = json.loads(meta.read_text(encoding='utf-8'))
    if not m.get('zip_integro') or z.stat().st_size != m['bytes']:
        raise ValueError('local ZIP does not match its receipt')
    digest = sha(z)
    if digest != m['sha256']:
        raise ValueError('local ZIP checksum differs from its receipt')
    return z, digest


def gdb_source(z):
    with zipfile.ZipFile(z) as a:
        roots = set()
        for n in a.namelist():
            if '\\' in n or '..' in Path(n).parts or n.startswith('/'):
                raise ValueError('unsafe archive member')
            for i, s in enumerate(n.split('/')):
                if s.lower().endswith('.gdb'):
                    roots.add('/'.join(n.split('/')[:i + 1]))
    if len(roots) != 1:
        raise ValueError('expected exactly one GDB')
    return f'/vsizip/{z.as_posix()}/{next(iter(roots))}'


def convert_layer(src, layer, dest, expected, source_sha):
    marker = dest.with_suffix('.ok.json')
    if marker.exists() and dest.exists():
        rec = json.loads(marker.read_text(encoding='utf-8'))
        if rec['source_sha'] == source_sha and rec['rows'] == expected and pq.ParquetFile(dest).metadata.num_rows == expected and sha(dest) == rec['sha256']:
            return rec
    dest.parent.mkdir(parents=True, exist_ok=True)
    part, n = dest.with_suffix('.partial.parquet'), 0
    with pyogrio.open_arrow(src, layer=layer, read_geometry=False, use_pyarrow=True, batch_size=16384) as (_, reader):
        with pq.ParquetWriter(part, reader.schema, compression='zstd') as w:
            for b in reader:
                w.write_batch(b); n += b.num_rows
    if n != expected:
        raise ValueError(f'GDB-Parquet row mismatch in {layer}: {n} != {expected}')
    os.replace(part, dest)
    rec = dict(rows=n, source_sha=source_sha, sha256=sha(dest), attributes_only=True, version=VERSION)
    atomic(marker, rec)
    return rec


def entity_checks(con, path, dist):
    cols = {r[0] for r in con.execute('DESCRIBE SELECT * FROM read_parquet(?)', [str(path)]).fetchall()}
    out = dict(dist_ok=None, data_base_values=None)
    if 'DIST' in cols:
        out['dist_ok'] = con.execute('SELECT count(*) FILTER(WHERE trim(CAST(DIST AS VARCHAR)) IS DISTINCT FROM ?) FROM read_parquet(?)', [str(dist), str(path)]).fetchone()[0] == 0
    if 'DATA_BASE' in cols:
        vals = [r[0] for r in con.execute('SELECT DISTINCT CAST(DATA_BASE AS VARCHAR) FROM read_parquet(?) LIMIT 8', [str(path)]).fetchall()]
        out['data_base_values'] = sorted(str(date(v) or v) for v in vals)
    return out


def ordinary_counts(dist, year):
    """Entity row counts of the ordinary (contract) item of (dist, year), from its conversion receipts."""
    if year == 2025:
        conv = Path('D:/NUCLEO_BDGD_2025/staging_parquet') / f'DIST={dist}' / 'DATA_BASE=2025-12-31' / 'conversao.json'
        if not conv.exists():
            return None, None
        c = json.loads(conv.read_text(encoding='utf-8'))
        ents = c.get('entidades') or c.get('entities') or {}
        return None, {k: (v.get('linhas', v.get('rows')) if isinstance(v, dict) else v) for k, v in ents.items()} if isinstance(ents, dict) else None
    rows = [r for r in csv.DictReader(open(INVENTORY, encoding='utf-8-sig'))
            if r['dist'] == str(dist) and r['competencia'] == str(year) and r['natureza'] == 'ordinaria' and r['origem'] == 'parquet_2022_2024']
    if len(rows) != 1:
        return None, None
    item = rows[0]['item_id']
    folder = HIST / 'parquet' / str(year) / str(dist) / item
    return item, {p.name.removesuffix('.ok.json'): json.loads(p.read_text(encoding='utf-8'))['rows'] for p in folder.glob('*.ok.json')}


def classify(year, dist, base, counts):
    fnl, inc = date(base.get('DAT_FNL')), date(base.get('DAT_INC'))
    if fnl and inc and fnl == inc:
        return 'competencia_indeterminada', None, 'BASE.DAT_INC = DAT_FNL = data de extracao (%s); periodo de referencia nao declarado' % fnl
    if fnl is None:
        return 'competencia_indeterminada', None, 'BASE.DAT_FNL ilegivel'
    if fnl.year == year:
        if (fnl.month, fnl.day) == (12, 31):
            return 'competencia_confirmada', year, 'BASE confirma %s' % fnl
        return 'competencia_confirmada_data_base_divergente', year, 'BASE %s a %s: competencia %d, mas data-base nao e 31/12 (intervalo ate a competencia seguinte nao e anual)' % (inc, fnl, year)
    other, ref = ordinary_counts(dist, fnl.year)
    if ref:
        common = sorted(set(ref) & set(counts))
        equal = bool(common) and all(ref[e] == counts[e] for e in common) and set(ref) == set(counts)
        if equal:
            return 'duplicata_da_competencia_%d' % fnl.year, fnl.year, 'BASE %s a %s; contagens identicas as %d entidades do item ordinario %s de %d' % (inc, fnl, len(common), other, fnl.year)
        diff = {e: (counts[e], ref[e]) for e in common if counts[e] != ref[e]}
        return 'competencia_divergente_%d' % fnl.year, fnl.year, 'BASE %s a %s; difere do item ordinario %s de %d em %d entidades (ex.: %s)' % (inc, fnl, other, fnl.year, len(diff), dict(list(diff.items())[:3]))
    return 'competencia_divergente_%d' % fnl.year, fnl.year, 'BASE %s a %s; sem item ordinario local de %d para comparar' % (inc, fnl, fnl.year)


def run(only=None):
    items = [r for r in csv.DictReader(open(INVENTORY, encoding='utf-8-sig')) if r['origem'] == 'zip_bruto_sem_conversao']
    if only:
        items = [r for r in items if r['dist'] in only]
    con = duckdb.connect(); con.execute("SET memory_limit='512MB'; SET threads=2")
    results = []
    size = lambda r: (HIST / 'raw' / r['competencia'] / r['dist'] / r['item_id'] / (r['item_id'] + '.zip')).stat().st_size
    for r in sorted(items, key=size):                      # small archives first; Cemig (4 GB) last
        year, dist, item = int(r['competencia']), r['dist'], r['item_id']
        dest = OUT / str(year) / dist / item
        rec = dict(dist=dist, empresa=r['empresa'], competencia_atribuida=year, item_id=item, versao=r['versao'], started=dt.datetime.now().isoformat(timespec='seconds'))
        try:
            z, digest = local_zip(year, dist, item)
            src = gdb_source(z)
            layers = {n.removesuffix('_tab'): n for n, _ in pyogrio.list_layers(src)}
            base = pyogrio.read_arrow(src, layer=layers['BASE'], read_geometry=False)[1].to_pylist()
            if len(base) != 1 or str(base[0].get('DIST')).strip() != dist:
                raise ValueError('BASE must have one row with the inventoried DIST')
            counts, checks = {}, {}
            for ent, layer in sorted(layers.items()):
                if ent == 'BASE':
                    continue
                n = int(pyogrio.read_info(src, layer=layer, force_feature_count=True)['features'])
                convert_layer(src, layer, dest / f'{ent}.parquet', n, digest)
                counts[ent] = n
                checks[ent] = entity_checks(con, dest / f'{ent}.parquet', dist)
                print(dist, year, ent, n, flush=True)
            kind, ref_year, reason = classify(year, int(dist), base[0], counts)
            bad_dist = sorted(e for e, c in checks.items() if c['dist_ok'] is False)
            rec.update(zip_sha256=digest, base={k: str(v) for k, v in base[0].items()}, entidades=len(counts), registros=sum(counts.values()),
                       linhas_por_entidade=counts, entidades_com_dist_divergente=bad_dist,
                       data_base_nas_entidades=sorted({v for c in checks.values() for v in (c['data_base_values'] or [])}),
                       classificacao=kind, competencia_segundo_base=ref_year, motivo=reason,
                       uso_no_motor='treino_e_previsao' if kind == 'competencia_confirmada' and not bad_dist else 'quarentena',
                       caminho=str(dest), status='convertido')
        except Exception as e:
            rec.update(status='falha', erro=str(e), uso_no_motor='quarentena')
        rec['finished'] = dt.datetime.now().isoformat(timespec='seconds')
        atomic(dest / 'manifest.json', rec)
        results.append(rec)
    con.close()
    old = {}
    summary = OUT / 'CONVERSAO_ZIPS_CONTRATO.json'
    if summary.exists():
        old = {x['item_id']: x for x in json.loads(summary.read_text(encoding='utf-8'))['itens']}
    old.update({x['item_id']: x for x in results})
    atomic(summary, dict(versao=VERSION, raiz=str(OUT), regra='conversao local sem download; raiz separada da arvore ordinaria; so competencia_confirmada entra no treino',
                         itens=sorted(old.values(), key=lambda x: (x['dist'], x['competencia_atribuida']))))
    return results


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--only', nargs='*')
    for x in run(set(ap.parse_args().only or [])):
        print(json.dumps({k: x.get(k) for k in ('dist', 'competencia_atribuida', 'status', 'classificacao', 'motivo', 'erro')}, ensure_ascii=False))
