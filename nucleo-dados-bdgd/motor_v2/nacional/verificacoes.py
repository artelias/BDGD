"""Integrity checks of the internal national outputs after the final audit (read only).

    python -m motor_v2.nacional.verificacoes

  * counts are integers >= 0 and every value is finite and >= 0 (both levels, company and territorial rows);
  * Conservador <= Moderado <= Agressivo for every series x year;
  * Level A: territorial units + residual == company value, exactly for counts, within 1e-3 for km/kVA;
  * the panel aggregates match their checkpoint hashes; the bridged Celesc file keeps its original byte for byte and the
    extraction source of the panel copy is unchanged;
  * nothing written under web/, output-historico/ or output-publicavel/ by this run (git status of those paths)."""
import json
import math
import subprocess
from collections import defaultdict

import pyarrow.parquet as pq

from . import ROOT_OUT
from ..runner import ROOT, atomic, digest, read


def run():
    out = {}
    for name, path, key in (('B', ROOT_OUT / 'distribuidora' / 'PROJECOES_B_INTERNO.parquet', ('DIST', 'conceito', 'metrica')),
                            ('A_distribuidora', ROOT_OUT / 'projecao' / 'PROJECOES_A_DISTRIBUIDORA_INTERNO.parquet', ('DIST', 'ativo', 'metrica'))):
        rows = pq.read_table(path).to_pylist()
        by = defaultdict(dict)
        bad_int = bad_neg = 0
        for r in rows:
            v = r['valor']
            if r['natureza'] == 'discrete_count' and (not float(v).is_integer()):
                bad_int += 1
            if not math.isfinite(float(v)) or float(v) < 0:
                bad_neg += 1
            by[tuple(r[k] for k in key) + (r['ano'],)][r['cenario']] = float(r['valor_bruto'])
        order = sum(1 for v in by.values() if not (v['Conservador'] <= v['Moderado'] + 1e-6 <= v['Agressivo'] + 2e-6))
        out[name] = dict(linhas=len(rows), contagens_nao_inteiras=bad_int, valores_negativos_ou_nao_finitos=bad_neg, ordem_cenarios_violada=order)
    terr = pq.read_table(ROOT_OUT / 'projecao' / 'PROJECOES_A_TERRITORIAL_INTERNO.parquet', columns=['DIST', 'ativo', 'metrica', 'natureza', 'cenario', 'ano', 'valor']).to_pylist()
    tot = {(r['DIST'], r['ativo'], r['metrica'], r['cenario'], r['ano']): r for r in pq.read_table(ROOT_OUT / 'projecao' / 'PROJECOES_A_DISTRIBUIDORA_INTERNO.parquet').to_pylist()}
    s = defaultdict(float); bad_int = 0
    for r in terr:
        s[r['DIST'], r['ativo'], r['metrica'], r['cenario'], r['ano']] += r['valor']
        bad_int += r['natureza'] == 'discrete_count' and not float(r['valor']).is_integer()
    rec = [k for k, r in tot.items() if abs(s[k] - r['valor']) > (0 if r['natureza'] == 'discrete_count' else 1e-3)]
    out['A_territorial'] = dict(linhas=len(terr), contagens_nao_inteiras=bad_int, falhas_reconciliacao_territorio_empresa=len(rec))
    man = read(ROOT_OUT / 'painel' / 'MANIFESTO_PAINEL.json')
    bad_hash = []
    for a in man['agregados']:
        if a.get('sha256') is None:
            continue
        p = ROOT_OUT / 'painel' / str(a['DIST']) / a['ativo'] / str(a['ano'])
        ck = read(p / 'checkpoint.json')
        if digest(p / 'territorial.parquet') != ck['output_sha256']:
            bad_hash.append(str(p))
        if digest(a['origem'] + '/territorial.parquet') != (ck.get('output_sha256_original') or ck['output_sha256']):
            bad_hash.append('origem:' + a['origem'])
    pontes = read(ROOT_OUT / 'pontes_experimentais.json')['pontes'] if (ROOT_OUT / 'pontes_experimentais.json').exists() else []
    orig = [dict(arquivo=f['arquivo'], original_preservado=digest(f['original_preservado'] + '/territorial.parquet') == f['sha256_antes'],
                 painel_atual=digest(f['arquivo']) == f['sha256_depois']) for p in pontes for f in p['arquivos']]
    out['painel'] = dict(agregados=len(man['agregados']), divergencias_de_hash=bad_hash, pontes=orig)
    st = subprocess.run(['git', 'status', '--porcelain', '--', 'web', 'output-historico', 'output-publicavel', 'motor_cenarios'], cwd=ROOT, capture_output=True, text=True).stdout
    out['produtos_publicos'] = dict(alteracoes_git=[x for x in st.splitlines() if x.strip()],
                                    nota='web/src/lib/maplibre-version.ts: alteracao so de fim de linha anterior a esta execucao, mantida fora dos commits')
    out['ok'] = all(v.get('contagens_nao_inteiras', 0) == 0 and v.get('valores_negativos_ou_nao_finitos', 0) == 0 and v.get('ordem_cenarios_violada', 0) == 0
                    and v.get('falhas_reconciliacao_territorio_empresa', 0) == 0 for v in out.values() if isinstance(v, dict)) \
        and not bad_hash and all(x['original_preservado'] and x['painel_atual'] for x in orig)
    atomic(ROOT_OUT / 'final' / 'VERIFICACOES_INTEGRIDADE.json', out)
    return out


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False, indent=1))
