"""A x B reconciliation of consumers: Level A UCBT (territorial) against Level B `consumidores` (contract, UCBT+UCMT+UCAT).

    python -m motor_v2.nacional.reconciliacao_ab

Concept difference, measured, not assumed: both levels count active units under the same identity rule (UC-v3, COD_ID + PN_CON,
SIT_ATIV = AT); Level A keeps only the UCBT table (the territorial extractor reads UCBT.MUN), Level B is the union of UCBT, UCMT and
UCAT de-duplicated across tables. The ETL's own UC-v3 audit of the same publication (proc/{year}/{dist}/{item}/conceitos_r3.json
for 2022-2024; output-publicavel/2025-12-31/qa_uc_regra_v3.csv for 2025) gives each table's active units and the union, so
  B - A = UCMT + UCAT - (units present in more than one table) + (A - UCBT of the audit)
is verified per DIST x year. Coverage and inclusion criteria (eligibility before/after the policy change, anchor, completeness)
are listed per DIST; the national comparison uses only the cohort of DIST that are complete in BOTH levels."""
import csv
import json
from collections import defaultdict
from pathlib import Path

from . import ROOT_OUT
from . import elegibilidade
from .relatorio import write_csv
from ..runner import atomic, read

PROC = Path('D:/NUCLEO_BDGD_2022_2024/proc')
QA2025 = Path('D:/NUCLEO_BDGD_2025/output-publicavel/2025-12-31/qa_uc_regra_v3.csv')
OUT = ROOT_OUT / 'reconciliacao_ab'


def uc_audit():
    """{(dist, year): dict(ucbt, ucmt, ucat, uniao)} active UC-v3 units of the contract publication."""
    cc = elegibilidade.cells()
    out = {}
    for (d, c, y), r in cc.items():
        if c != 'consumidores' or y == 2025 or not r['publicacao_id']:
            continue
        p = PROC / str(y) / str(d) / r['publicacao_id'] / 'conceitos_r3.json'
        if p.exists():
            u = json.loads(p.read_text(encoding='utf-8')).get('uc_v3') or {}
            out[d, y] = dict(ucbt=(u.get('UCBT') or {}).get('unidades_ativas_v3', 0), ucmt=(u.get('UCMT') or {}).get('unidades_ativas_v3', 0),
                             ucat=(u.get('UCAT') or {}).get('unidades_ativas_v3', 0), uniao=(u.get('uniao') or {}).get('unidades_ativas_v3'), fonte=str(p))
    acc = defaultdict(dict)
    with open(QA2025, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            k = 'uniao' if r['entidade'].startswith('UC*') else r['entidade'].lower()
            acc[int(r['dist'])][k] = int(r['unidades_ativas_v3']) if r['unidades_ativas_v3'] else None
    for d, v in acc.items():
        out[d, 2025] = dict(ucbt=v.get('ucbt', 0), ucmt=v.get('ucmt', 0), ucat=v.get('ucat', 0), uniao=v.get('uniao'), fonte=str(QA2025))
    return out


def level_a():
    out = {}
    for p in sorted((ROOT_OUT / 'painel').glob('*/ucbt_quantidade/result.json')):
        for h in read(p)['history']:
            out[int(p.parent.parent.name), h['year']] = h.get('value')
    return out


def rcsv(p):
    return list(csv.DictReader(open(p, encoding='utf-8'))) if Path(p).exists() else []


def run(v1=ROOT_OUT / '_v1_d4982e8'):
    OUT.mkdir(parents=True, exist_ok=True)
    cc = elegibilidade.cells(); ua = uc_audit(); A = level_a()
    da = {int(r['DIST']): r for r in rcsv(ROOT_OUT / 'projecao' / 'DECISOES_A.csv') if r['ativo'] == 'ucbt'}
    db = {int(r['DIST']): r for r in rcsv(ROOT_OUT / 'distribuidora' / 'DECISOES_B.csv') if r['conceito'] == 'consumidores'}
    db1 = {int(r['DIST']): r for r in rcsv(v1 / 'distribuidora' / 'DECISOES_B.csv') if r['conceito'] == 'consumidores'}
    pa = defaultdict(dict); pb = defaultdict(dict)
    for r in rcsv(ROOT_OUT / 'projecao' / 'PROJECOES_A_DISTRIBUIDORA.csv'):
        if r['ativo'] == 'ucbt':
            pa[int(r['DIST'])][int(r['ano']), r['cenario']] = float(r['valor'])
    for r in rcsv(ROOT_OUT / 'distribuidora' / 'PROJECOES_B.csv'):
        if r['conceito'] == 'consumidores':
            pb[int(r['DIST'])][int(r['ano']), r['cenario']] = float(r['valor'])
    complete = lambda dec, proj: bool(dec and dec.get('status_projecao') == 'gerada' and str(dec.get('ancora_2025')) in ('True', 'true') and len(proj) == 15)
    rows, per_dist = [], []
    dists = sorted({d for d, c, _ in cc if c == 'consumidores'} | {d for d, _ in A})
    for d in dists:
        for y in range(2022, 2026):
            r = cc.get((d, 'consumidores', y)); u = ua.get((d, y)) or {}
            a = A.get((d, y)); b = float(r['valor']) if r and r['valor'] else None
            ok2, why2, cav = elegibilidade.estoque(r)
            expl = (u.get('ucmt', 0) + u.get('ucat', 0)) if u else None
            overlap = (u['ucbt'] + u['ucmt'] + u['ucat'] - u['uniao']) if u and u.get('uniao') is not None else None
            rows.append(dict(DIST=d, empresa=r and r['empresa'], ano=y, A_ucbt_ativas_v3=a, B_consumidores_contrato=b,
                             auditoria_ucbt=u.get('ucbt'), auditoria_ucmt=u.get('ucmt'), auditoria_ucat=u.get('ucat'), auditoria_uniao=u.get('uniao'),
                             sobreposicao_entre_tabelas=overlap, B_menos_A=(b - a) if a is not None and b is not None else None,
                             explicado_ucmt_ucat_menos_sobreposicao=(expl - overlap) if expl is not None and overlap is not None else None,
                             A_menos_auditoria_ucbt=(a - u['ucbt']) if a is not None and u else None,
                             B_menos_auditoria_uniao=(b - u['uniao']) if b is not None and u and u.get('uniao') is not None else None,
                             fechamento_exato=(a is not None and b is not None and u and u.get('uniao') is not None and a == u['ucbt'] and b == u['uniao']),
                             A_sobre_B=(a / b) if a and b else None, estado_contrato=r and r['estado'], intervalo_base=r and r['intervalo_base'],
                             estoque_elegivel_v1_B=elegibilidade.legado_b(r), estoque_elegivel_v2=ok2, motivo_inelegivel=why2, ressalvas=';'.join(cav)))
        ra, rb = da.get(d), db.get(d)
        ca, cb = complete(ra, pa.get(d, {})), complete(rb, pb.get(d, {}))
        g = lambda p, s: p.get((2030, s))
        per_dist.append(dict(DIST=d, empresa=(cc.get((d, 'consumidores', 2025)) or cc.get((d, 'consumidores', 2022)) or {}).get('empresa'),
                             A_ancora=ra and ra.get('ano_ancora'), B_ancora=rb and rb.get('ano_ancora'), B_ancora_v1=db1.get(d, {}).get('ano_ancora'),
                             A_completa_nos_totais=ca, B_completa_nos_totais=cb, coorte_comum=ca and cb,
                             A_2025=A.get((d, 2025)), B_2025=float(cc[d, 'consumidores', 2025]['valor']) if (d, 'consumidores', 2025) in cc and cc[d, 'consumidores', 2025]['valor'] else None,
                             A_moderado_2030=g(pa.get(d, {}), 'Moderado'), B_moderado_2030=g(pb.get(d, {}), 'Moderado'),
                             A_cagr_moderado=_cagr(A.get((d, 2025)), g(pa.get(d, {}), 'Moderado')),
                             B_cagr_moderado=_cagr(_f(rb and rb.get('valor_ancora')), g(pb.get(d, {}), 'Moderado'), _i(rb and rb.get('ano_ancora'))),
                             A_modelo=ra and ra.get('modelo_usado_na_projecao'), B_modelo=rb and rb.get('modelo_usado_na_projecao'),
                             motivo_fora_A=None if ca else _why(ra, pa.get(d, {})), motivo_fora_B=None if cb else _why(rb, pb.get(d, {}))))
    write_csv(OUT / 'RECONCILIACAO_AB_CONSUMIDORES_DIST_ANO.csv', rows)
    write_csv(OUT / 'RECONCILIACAO_AB_CONSUMIDORES_POR_DIST.csv', per_dist)
    # cohort comparison (DIST complete in both levels)
    coh = [x for x in per_dist if x['coorte_comum']]
    tot = {}
    for s in ('Conservador', 'Moderado', 'Agressivo'):
        for y in (2026, 2030):
            tot[f'{s}_{y}'] = dict(A=sum(pa[x['DIST']][y, s] for x in coh), B=sum(pb[x['DIST']][y, s] for x in coh))
    y25 = [r for r in rows if r['ano'] == 2025 and r['DIST'] in {x['DIST'] for x in coh}]
    summary = dict(
        dist_coorte_comum=len(coh), dist_so_A=sum(1 for x in per_dist if x['A_completa_nos_totais'] and not x['B_completa_nos_totais']),
        dist_so_B=sum(1 for x in per_dist if x['B_completa_nos_totais'] and not x['A_completa_nos_totais']),
        coorte_2025=dict(A_ucbt=sum(r['A_ucbt_ativas_v3'] or 0 for r in y25), B_consumidores=sum(r['B_consumidores_contrato'] or 0 for r in y25),
                         ucmt=sum(r['auditoria_ucmt'] or 0 for r in y25), ucat=sum(r['auditoria_ucat'] or 0 for r in y25),
                         sobreposicao=sum(r['sobreposicao_entre_tabelas'] or 0 for r in y25)),
        coorte_totais=tot,
        fechamento_dist_ano=dict(com_auditoria=sum(1 for r in rows if r['auditoria_uniao'] is not None and r['A_ucbt_ativas_v3'] is not None and r['B_consumidores_contrato'] is not None),
                                 exatos=sum(1 for r in rows if r['fechamento_exato']),
                                 nao_exatos=[dict(DIST=r['DIST'], ano=r['ano'], A_menos_auditoria_ucbt=r['A_menos_auditoria_ucbt'], B_menos_auditoria_uniao=r['B_menos_auditoria_uniao'])
                                             for r in rows if r['auditoria_uniao'] is not None and r['A_ucbt_ativas_v3'] is not None and r['B_consumidores_contrato'] is not None and not r['fechamento_exato']]),
        enel_sp_390=[dict((k, r[k]) for k in ('ano', 'A_ucbt_ativas_v3', 'B_consumidores_contrato', 'auditoria_ucmt', 'auditoria_ucat', 'intervalo_base', 'estoque_elegivel_v1_B', 'estoque_elegivel_v2')) for r in rows if r['DIST'] == 390],
        enel_sp_390_projecao=next((x for x in per_dist if x['DIST'] == 390), None),
        celulas_que_mudaram_de_elegibilidade=[dict(DIST=r['DIST'], ano=r['ano'], v1=r['estoque_elegivel_v1_B'], v2=r['estoque_elegivel_v2'], motivo=r['motivo_inelegivel'], ressalvas=r['ressalvas'])
                                              for r in rows if r['estoque_elegivel_v1_B'] != r['estoque_elegivel_v2'] and r['estado_contrato'] in ('observado', 'zero_verificado')])
    summary['evidencia_intervalo_nao_anual'] = auditoria_intervalo()
    atomic(OUT / 'RECONCILIACAO_AB_RESUMO.json', summary)
    return summary


def auditoria_intervalo():
    """Empirical check behind the policy: growth of every eligible transition touching an INTERVALO_NAO_ANUAL cell against the
    national cross-section of the same concept and year (median +- 5 MAD, MAD floor 0.02 as in the scenario screen), compared
    with all other transitions."""
    import math
    import statistics as st
    cc = elegibilidade.cells()
    nao = {(d, y) for (d, c, y), r in cc.items() if r['intervalo_base'] == 'INTERVALO_NAO_ANUAL'}
    g = defaultdict(dict)
    for (d, c, y), r in cc.items():
        p = cc.get((d, c, y - 1))
        if p is not None and elegibilidade.transicao(p, r)[0]:
            g[c, y][d] = math.log1p(max(float(r['valor']), 0)) - math.log1p(max(float(p['valor']), 0))
    rows = []
    for (c, y), gs in g.items():
        if len(gs) < 5:
            continue
        med = st.median(gs.values()); mad = max(st.median([abs(x - med) for x in gs.values()]), 0.02)
        for d, v in gs.items():
            touch = (d, y) in nao or (d, y - 1) in nao
            rows.append(dict(DIST=d, conceito=c, ano=y, toca_intervalo_nao_anual=touch, crescimento_log1p=v, mediana_nacional=med, mad=mad,
                             desvio_em_mad=(v - med) / mad, atipica_5mad=abs(v - med) > 5 * mad))
    write_csv(OUT / 'AUDITORIA_INTERVALO_NAO_ANUAL.csv', [r for r in rows if r['toca_intervalo_nao_anual']])
    share = lambda f: (sum(r['atipica_5mad'] for r in rows if f(r)) / max(1, sum(1 for r in rows if f(r))), sum(1 for r in rows if f(r)))
    a, b = share(lambda r: r['toca_intervalo_nao_anual']), share(lambda r: not r['toca_intervalo_nao_anual'])
    return dict(publicacoes_nao_anuais=sorted(nao), transicoes_com_ressalva=a[1], share_atipica_com_ressalva=a[0], transicoes_demais=b[1], share_atipica_demais=b[0])


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _i(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return 2025


def _cagr(v0, v1, y0=2025):
    return (v1 / v0) ** (1 / (2030 - y0)) - 1 if v0 and v1 and v0 > 0 and y0 < 2030 else None


def _why(dec, proj):
    if not dec:
        return 'sem serie'
    if dec.get('status_projecao') != 'gerada':
        return dec.get('motivo_projecao') or dec.get('status_projecao')
    if str(dec.get('ancora_2025')) not in ('True', 'true'):
        return f"ancora {dec.get('ano_ancora')} != 2025"
    return f'{len(proj)} de 15 valores'


if __name__ == '__main__':
    s = run()
    print(json.dumps({k: v for k, v in s.items() if k not in ('enel_sp_390',)}, ensure_ascii=False, indent=1, default=str)[:5000])
