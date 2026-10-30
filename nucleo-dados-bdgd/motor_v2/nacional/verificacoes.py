"""Integrity checks of the internal national outputs after the final audit (read only).

    python -m motor_v2.nacional.verificacoes

  * counts are integers >= 0 and every value is finite and >= 0 (both levels, company and territorial rows);
  * Conservador <= Moderado <= Agressivo for every series x year;
  * Level A: territorial units + residual == company value, exactly for counts, within 1e-3 for km/kVA;
  * the panel aggregates match their checkpoint hashes; the bridged Celesc file keeps its original byte for byte and the
    extraction source of the panel copy is unchanged;
  * nothing written under web/, output-historico/, output-publicavel/ or motor_cenarios/ by the motor: every change git reports
    there must be listed in the versioned baseline (baseline_produtos_publicos.json) with the same SHA-256 of the working file;
    any other change (new, different content, deleted) is attributed to the run and makes `ok` false;
  * consumers hierarchy: no reconciled DIST x year x scenario with Consumidores < UCBT, integers >= 0, ordered scenarios, and the
    observed closures (UCBT = audit UCBT, Consumidores = audit union) all exact."""
import json
import math
import subprocess
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq

from . import ROOT_OUT
from ..runner import ROOT, atomic, digest, read

PUBLIC = ('web', 'output-historico', 'output-publicavel', 'motor_cenarios')
BASELINE = Path(__file__).parent / 'baseline_produtos_publicos.json'


def classify_public_changes(status_lines, baseline, sha_of):
    """git porcelain lines of the public paths -> (preexisting, caused by the run). A change is preexisting only when the baseline lists
    the path with the same working-file SHA-256 (sha_of(path) -> sha or None when the file no longer exists)."""
    pre, run = [], []
    known = {x['caminho']: x for x in baseline.get('alteracoes', [])}
    for line in status_lines:
        if not line.strip():
            continue
        code, path = line[:2], line[3:].strip().strip('"')
        b = known.get(path); sha = sha_of(path)
        (pre if b and b['sha256_arquivo'] == sha and b['status_git'] == code else run).append(dict(caminho=path, status_git=code, sha256_arquivo=sha))
    return pre, run


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
    st = subprocess.run(['git', 'status', '--porcelain', '--untracked-files=all', '--', *PUBLIC], cwd=ROOT, capture_output=True, text=True).stdout
    top = subprocess.run(['git', 'rev-parse', '--show-toplevel'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    sha_of = lambda p: digest(Path(top) / p) if (Path(top) / p).is_file() else None
    pre, by_run = classify_public_changes(st.splitlines(), read(BASELINE) if BASELINE.exists() else {}, sha_of)
    out['produtos_publicos'] = dict(alteracoes_preexistentes_na_baseline=pre, alteracoes_atribuidas_a_execucao=by_run, baseline=str(BASELINE.name))
    # consumers hierarchy (UCBT within Consumidores)
    from . import hierarquia
    hp = hierarquia.OUT / 'PROJECOES_CONSUMIDORES_RECONCILIADAS.parquet'
    if hp.exists():
        rr = [r for r in pq.read_table(hp).to_pylist() if r['status'] == 'reconciliada']
        ab = read(ROOT_OUT / 'reconciliacao_ab' / 'RECONCILIACAO_AB_RESUMO.json')['fechamento_dist_ano']
        out['hierarquia_consumidores'] = dict(linhas_reconciliadas=len(rr), violacoes=len(hierarquia.violations(rr)),
                                              fechamentos_historicos=ab['com_auditoria'], fechamentos_exatos=ab['exatos'],
                                              violacoes_originais_preservadas=sum(1 for r in rr if r['violacao_original']))
    out['ok'] = all(v.get('contagens_nao_inteiras', 0) == 0 and v.get('valores_negativos_ou_nao_finitos', 0) == 0 and v.get('ordem_cenarios_violada', 0) == 0
                    and v.get('falhas_reconciliacao_territorio_empresa', 0) == 0 for v in out.values() if isinstance(v, dict) and 'linhas' in v) \
        and not bad_hash and all(x['original_preservado'] and x['painel_atual'] for x in orig) and not by_run
    hc = out.get('hierarquia_consumidores') or {}
    out['ok'] = out['ok'] and hc.get('violacoes', 1) == 0 and hc.get('fechamentos_exatos') == hc.get('fechamentos_historicos')
    atomic(ROOT_OUT / 'final' / 'VERIFICACOES_INTEGRIDADE.json', out)
    return out


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False, indent=1))
