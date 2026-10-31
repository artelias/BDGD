"""Hierarchical reconciliation of consumers: UCBT (Level A) is contained in Consumidores (Level B) for every DIST, year and scenario.

    python -m motor_v2.nacional.hierarquia

CONTRACT (CONTRATO_HIERARQUIA_CONSUMIDORES.json): for the same DIST, competence and scenario
    Consumidores = UCBT + complemento,   complemento = UCMT + UCAT - (units present in more than one table) >= 0,
both counts under the UC-v3 identity (COD_ID + PN_CON, active). Observed: closes exactly in every audited DIST x year (385 pairs).

Adopted strategy `hierarquica_complemento`:
  1. the UCBT projection of Level A (moderate path and scenarios) is kept unchanged;
  2. the observed complement series C_t = B_t - A_t is built only from compatible pairs: same publication, both stocks eligible
     under the common policy, exact closure with the ETL UC-v3 audit; a transition of C is comparable when the Level B transition
     is eligible (elegibilidade.transicao) and Level A records no rupture;
  3. C is modelled with the baselines that its 4-point history supports (persistence, drift, CAGR), chosen per DIST with the same
     backtest and choice rule as the rest of the motor (origins 2023/2024, selecao.choose: a trend only if >= 5% better than
     persistence and not worse in any origin); its scenarios follow cenarios.scenarios with the v2 envelope screen computed on the
     national cross-section of complements; C >= 0 by construction (baseline fallbacks and zero floor);
  4. Consumidores_reconciliado = A + C for every year and scenario; integers: A integer (as published) + half-up rounding of C, so
     the reconciled value is an integer >= UCBT and the scenario order holds (both terms are ordered).
The independent Level B projection is preserved in its own column, with the model that produced it. Only DIST whose A and B series
share the anchor competence and whose complement is observed at that anchor are reconciled; the rest is reported as `sem_coorte`.

Strategies compared (ESTRATEGIAS_RECONCILIACAO_CONSUMIDORES.csv), none of them touches other asset families:
  hierarquica_complemento (adopted) | hierarquica_participacao (complement share of the anchor held constant: C = A x C0/A0) |
  ajuste_minimo (B kept where B >= A + C0, otherwise raised to A + C0: keeps the independent B growth, mixes two models) |
  b_prevalece (reference only, not admissible: A = B - C changes the UCBT projection)."""
import csv
import json
import math
from collections import Counter, defaultdict

import pyarrow.parquet as pq

from . import ROOT_OUT, elegibilidade
from .cenarios import YEARS, baseline_path, lg, scenarios, screen_table_v2, screened_growth_v2
from .relatorio import write_csv, write_parquet
from .selecao import BASELINES, choose, metrics
from ..metric_contract import round_count
from ..runner import atomic, digest, read

OUT = ROOT_OUT / 'hierarquia_consumidores'
SCEN = ('Conservador', 'Moderado', 'Agressivo')
ORIGINS = (2023, 2024)


# ----------------------------------------------------------------------------------------------------------- pure functions
def one_step(kind, seg):
    """One-step baseline forecast of origin+1 from the comparable segment ending at the origin (same formulas as Level B)."""
    t1, y1 = seg[-1]
    if kind == 'persistencia' or len(seg) < 2:
        return y1, (None if kind == 'persistencia' else 'short_series')
    t0, y0 = seg[0]
    if kind == 'deriva':
        v = y1 + (y1 - y0) / (t1 - t0)
        return (v, None) if v >= 0 else (y1, 'negative_forecast')
    if y0 <= 0 or y1 <= 0:
        return y1, 'nonpositive_endpoint'
    return y1 * (y1 / y0) ** (1 / (t1 - t0)), None


def segment(points, breaks, end):
    """Contiguous comparable segment of {year: value} ending at `end`."""
    if end not in points:
        return []
    seg, t = [(end, points[end])], end
    while t - 1 in points and t not in breaks:
        t -= 1; seg.insert(0, (t, points[t]))
    return seg


def choose_complement(points, breaks):
    """Backtest of the baselines on the complement series and the motor's choice rule -> (decision, candidates)."""
    preds, detail = defaultdict(list), defaultdict(list)
    for o in ORIGINS:
        if o + 1 not in points or o + 1 in breaks or o not in points:
            continue
        seg = segment(points, breaks, o)
        for b in BASELINES:
            v, why = one_step(b, seg)
            preds[b].append((o, points[o + 1], v)); detail[b].append(why)
    cands = {b: dict(kind='baseline', keys={o for o, _, _ in pr}, m=metrics(pr), fallback_share=sum(1 for w in detail[b] if w) / len(pr))
             for b, pr in preds.items()}
    return choose(cands) if cands else choose({}), cands


def complement_paths(anchor, points, breaks, table, kind):
    """Complement paths of the three scenarios (moderate = chosen baseline; envelope = v2 screen on the complement cross-section)."""
    seg = segment(points, breaks, anchor)
    mod, why = baseline_path(kind, seg, anchor)
    mod = {y: max(v, 0.0) for y, v in mod.items()}
    kept, cls = screened_growth_v2({y: v for y, v in points.items() if y <= anchor}, breaks, table)
    sc, meta = scenarios(anchor, points[anchor], mod, kept)
    meta['fallback_modelo'] = why
    meta['classes_transicoes'] = dict(Counter(x['classe'] for x in cls))
    return sc, meta


def reconcile(a_int, c_raw):
    """Integer reconciled consumers: UCBT integer (as published) + half-up rounding of a non-negative complement."""
    if c_raw < 0:
        raise ValueError('complemento negativo')
    return int(a_int) + round_count(c_raw)


def violations(rows, a_key='ucbt_A', b_key='consumidores_reconciliado'):
    """Rows where Consumidores < UCBT or an integer / sign / order rule fails (the reconciled series must return [])."""
    bad = [r for r in rows if r[b_key] is None or r[b_key] < r[a_key] or r[b_key] < 0 or float(r[b_key]) != int(r[b_key])]
    by = defaultdict(dict)
    for r in rows:
        by[r['DIST'], r['ano']][r['cenario']] = r[b_key]
    bad += [dict(DIST=d, ano=y, regra='ordem dos cenarios') for (d, y), v in by.items() if len(v) == 3 and not (v['Conservador'] <= v['Moderado'] <= v['Agressivo'])]
    return bad


def incompletude(rows, years=YEARS, scenarios=SCEN):
    """Completeness of the reconciled series: every DIST must hold exactly len(years) x len(scenarios) unique (ano, cenario) pairs
    (15 for 2026-2030 x 3 scenarios): no duplicate pair, no missing pair, no pair outside the horizon. [] when complete."""
    want = {(y, s) for y in years for s in scenarios}
    seen = defaultdict(list)
    for r in rows:
        seen[r['DIST']].append((r['ano'], r['cenario']))
    bad = []
    for d, pairs in sorted(seen.items()):
        c = Counter(pairs)
        dup, miss, extra = sorted(k for k, n in c.items() if n > 1), sorted(want - set(c)), sorted(set(c) - want)
        if dup or miss or extra:
            bad.append(dict(DIST=d, regra='15 pares (ano, cenario) unicos por DIST', pares=len(pairs), unicos=len(c), duplicados=dup, ausentes=miss, fora_do_horizonte=extra))
    return bad


# ----------------------------------------------------------------------------------------------------------- data
def history():
    """{dist: dict(A={y: v}, B={y: v}, C={y: v}, breaks=set, motivo_fora={y: reason})}, compatible pairs only."""
    from .reconciliacao_ab import level_a, uc_audit
    cc = elegibilidade.cells(); ua = uc_audit(); A = level_a()
    rupA = {}
    for p in sorted((ROOT_OUT / 'painel').glob('*/ucbt_quantidade/result.json')):
        for h in read(p)['history']:
            rupA[int(p.parent.parent.name), h['year']] = bool(h.get('rupture'))
    out = {}
    for d in sorted({d for d, c, _ in cc if c == 'consumidores'}):
        rec = dict(A={}, B={}, C={}, breaks=set(), motivo_fora={})
        for y in range(2022, 2026):
            r = cc.get((d, 'consumidores', y)); a = A.get((d, y)); u = ua.get((d, y)) or {}
            ok, why, _ = elegibilidade.estoque(r)
            if a is None:
                rec['motivo_fora'][y] = 'sem UCBT extraido (nivel A)'; continue
            if not ok:
                rec['motivo_fora'][y] = 'estoque B inelegivel: ' + str(why); continue
            b = float(r['valor'])
            if not u or u.get('uniao') is None or a != u['ucbt'] or b != u['uniao']:
                rec['motivo_fora'][y] = 'sem fechamento exato com a auditoria UC-v3'; continue
            rec['A'][y], rec['B'][y], rec['C'][y] = float(a), b, b - a
        for y in rec['C']:
            if y - 1 in rec['C']:
                t_ok = elegibilidade.transicao(cc[d, 'consumidores', y - 1], cc[d, 'consumidores', y])[0]
                if not t_ok or rupA.get((d, y)):
                    rec['breaks'].add(y)
        out[d] = rec
    return out


def projections():
    A, B = defaultdict(dict), defaultdict(dict)
    meta = {}
    for r in pq.read_table(ROOT_OUT / 'projecao' / 'PROJECOES_A_DISTRIBUIDORA_INTERNO.parquet').to_pylist():
        if r['ativo'] == 'ucbt':
            A[r['DIST']][r['ano'], r['cenario']] = (r['valor'], r['valor_bruto']); meta['A', r['DIST']] = dict(ancora=r['ano_ancora'], modelo=r['modelo'])
    for r in pq.read_table(ROOT_OUT / 'distribuidora' / 'PROJECOES_B_INTERNO.parquet').to_pylist():
        if r['conceito'] == 'consumidores':
            B[r['DIST']][r['ano'], r['cenario']] = (r['valor'], r['valor_bruto']); meta['B', r['DIST']] = dict(ancora=r['ano_ancora'], modelo=r['modelo'])
    return A, B, meta


# ----------------------------------------------------------------------------------------------------------- core (pure)
def reconcile_dist(d, h, a_proj, b_proj, ma, mb, table):
    """One DIST, no disk access. h: dict(A, B, C {year: value}, breaks, motivo_fora); a_proj/b_proj {(year, scenario): (int, raw)};
    ma/mb: dict(ancora, modelo). -> (decision, rows, strategy rows for the anchor-2025 comparison)."""
    anchor = ma.get('ancora')
    why = None
    if not a_proj or not b_proj:
        why = 'projecao ausente em ' + ('A' if not a_proj else 'B')
    elif ma['ancora'] != mb['ancora']:
        why = f"ancoras diferentes (A {ma['ancora']}, B {mb['ancora']})"
    elif anchor not in h['C']:
        why = f"complemento nao observado na ancora {anchor}: {h['motivo_fora'].get(anchor, 'par incompativel')}"
    elif h['C'][anchor] < 0:
        why = 'complemento observado negativo na ancora (par semanticamente incompativel)'
    rows, strat = [], defaultdict(list)
    if why:
        for (y, s), (bv, _) in sorted(b_proj.items()):
            av = a_proj.get((y, s), (None,))[0]
            rows.append(dict(DIST=d, ancora=mb.get('ancora'), ano=y, cenario=s, ucbt_A=av, consumidores_B_original=bv, complemento=None,
                             consumidores_reconciliado=None, ajuste=None, violacao_original=av is not None and bv < av, status='sem_coorte', motivo=why))
        return dict(DIST=d, status='sem_coorte', motivo=why, ancora_A=ma.get('ancora'), ancora_B=mb.get('ancora')), rows, strat
    dec, cands = choose_complement(h['C'], h['breaks'])
    kind = dec['modelo_projecao'] if dec['modelo_projecao'] in BASELINES else dec['modelo_fallback']
    csc, cmeta = complement_paths(anchor, h['C'], h['breaks'], table, kind)
    c0, a0 = h['C'][anchor], h['A'][anchor]
    decision = dict(DIST=d, status='reconciliada', ancora=anchor, ucbt_ancora=a0, consumidores_ancora=h['B'][anchor], complemento_ancora=c0,
                    complemento_historico=json.dumps({str(k): v for k, v in sorted(h['C'].items())}), quebras=json.dumps(sorted(h['breaks'])),
                    metodo_complemento=kind, escolha=dec.get('melhor_modelo_experimental') or 'persistencia por politica/medida',
                    motivo_escolha=dec.get('motivo_experimental'), origens_medidas=dec.get('origens'),
                    mae_persistencia=(cands.get('persistencia') or {}).get('m', {}).get('mae') if cands else None,
                    modelo_A=ma['modelo'], modelo_B_original=mb['modelo'], **{'complemento_' + k: v for k, v in cmeta.items() if k != 'regra'})
    for s in SCEN:
        for y in YEARS:
            a_int, a_raw = a_proj[y, s]; b_int, b_raw = b_proj[y, s]; c = csc[s][y]
            rec = reconcile(a_int, c)
            rows.append(dict(DIST=d, ancora=anchor, ano=y, cenario=s, ucbt_A=int(a_int), consumidores_B_original=int(b_int), complemento=round_count(c),
                             complemento_bruto=c, consumidores_reconciliado=rec, ajuste=rec - int(b_int), violacao_original=b_int < a_int,
                             diferenca_conceito_ancora=c0, diferenca_modelo=int(b_int) - int(a_int) - c0, metodo_complemento=kind,
                             modelo_A=ma['modelo'], modelo_B_original=mb['modelo'], status='reconciliada', motivo=None))
            if anchor != 2025:
                continue
            # strategies compared (comparable cohort: anchor 2025)
            share = c0 / a0 if a0 else 0.
            strat['hierarquica_complemento'].append((d, y, s, int(a_int), rec, int(b_int)))
            strat['hierarquica_participacao'].append((d, y, s, int(a_int), int(a_int) + round_count(a_raw * share), int(b_int)))
            strat['ajuste_minimo'].append((d, y, s, int(a_int), max(int(b_int), int(a_int) + round_count(c0)), int(b_int)))
            strat['b_prevalece'].append((d, y, s, int(b_int) - round_count(c), int(b_int), int(b_int)))
    return decision, rows, strat


def complement_table(H):
    return screen_table_v2({d: h['C'] for d, h in H.items()}, {d: h['breaks'] for d, h in H.items()})


# ----------------------------------------------------------------------------------------------------------- run
def run():
    OUT.mkdir(parents=True, exist_ok=True)
    H = history(); A, B, meta = projections()
    table = complement_table(H)
    rows, decisions, strat = [], [], defaultdict(list)
    empty = dict(A={}, B={}, C={}, breaks=set(), motivo_fora={})
    for d in sorted(set(A) | set(B)):
        dec, rr, st = reconcile_dist(d, H.get(d) or empty, A.get(d, {}), B.get(d, {}), meta.get(('A', d), {}), meta.get(('B', d), {}), table)
        decisions.append(dec); rows += rr
        for k, v in st.items():
            strat[k] += v
    rec_rows = [r for r in rows if r['status'] == 'reconciliada']
    bad = violations(rec_rows) + incompletude(rec_rows)
    comp = compare(strat, decisions)
    nat = national(rows)
    write_csv(OUT / 'PROJECOES_CONSUMIDORES_RECONCILIADAS.csv', rows)
    write_parquet(OUT / 'PROJECOES_CONSUMIDORES_RECONCILIADAS.parquet', rows)
    write_csv(OUT / 'COMPLEMENTO_POR_DIST.csv', decisions)
    write_csv(OUT / 'ESTRATEGIAS_RECONCILIACAO_CONSUMIDORES.csv', comp)
    write_csv(OUT / 'VIOLACOES_E_AJUSTES.csv', audit(rows))
    write_csv(OUT / 'TOTAIS_CONSUMIDORES_RECONCILIADOS.csv', nat)
    contract = dict(
        contrato='hierarquia-consumidores-1', relacao='Consumidores = UCBT + complemento; complemento = UCMT + UCAT - sobreposicao >= 0 (identidade UC-v3)',
        regra='para a mesma DIST, competencia e cenario: consumidores_reconciliado >= ucbt_A; inteiros >= 0; Conservador <= Moderado <= Agressivo; 15 pares (ano, cenario) unicos por DIST reconciliada, sem duplicidade nem ausencia',
        ucbt='projecao do nivel A preservada (modelo e cenarios), sem alteracao', complemento=__doc__.split('Adopted strategy')[1].split('Strategies compared')[0].strip(),
        pares_compativeis='mesma publicacao, estoques elegiveis (politica comum), fechamento exato com a auditoria UC-v3 do ETL',
        fechamento_historico=dict(pares=sum(len(h['C']) for h in H.values()), complemento_negativo=sum(1 for h in H.values() for v in h['C'].values() if v < 0)),
        previsao_original='consumidores_B_original (modelo independente do nivel B) mantida em coluna propria para auditoria',
        violacoes_remanescentes=len(bad), pares_por_dist_exigidos=len(YEARS) * len(SCEN), dist_reconciliadas=sum(1 for x in decisions if x['status'] == 'reconciliada'),
        dist_sem_coorte=[dict(DIST=x['DIST'], motivo=x['motivo']) for x in decisions if x['status'] == 'sem_coorte'],
        status='experimental_interno_nao_publicavel; nao homologado',
        hashes=dict(projecoes_A=digest(ROOT_OUT / 'projecao' / 'PROJECOES_A_DISTRIBUIDORA_INTERNO.parquet'),
                    projecoes_B=digest(ROOT_OUT / 'distribuidora' / 'PROJECOES_B_INTERNO.parquet')))
    atomic(OUT / 'CONTRATO_HIERARQUIA_CONSUMIDORES.json', contract)
    if bad:
        raise AssertionError(f'{len(bad)} violacoes remanescentes nas series reconciliadas')
    return dict(contrato=contract, estrategias=comp, totais=[t for t in nat if t['ano'] == 2030])


def compare(strat, decisions):
    out = []
    for name, rr in strat.items():
        tot = defaultdict(float); base = defaultdict(float); a = defaultdict(float)
        for d, y, s, av, bv, b0 in rr:
            tot[y, s] += bv; base[y, s] += b0; a[y, s] += av
        viol = sum(1 for d, y, s, av, bv, b0 in rr if bv < av)
        changed = sum(1 for d, y, s, av, bv, b0 in rr if bv != b0)
        anc = sum(x['consumidores_ancora'] for x in decisions if x['status'] == 'reconciliada' and x['ancora'] == 2025)
        g = lambda s: (tot[2030, s] / anc) ** (1 / 5) - 1 if anc else None
        out.append(dict(estrategia=name, admissivel=name != 'b_prevalece', preserva_ucbt_A=name != 'b_prevalece', violacoes_consumidores_menor_ucbt=viol,
                        celulas_alteradas_vs_B_original=changed, celulas=len(rr),
                        total_2030_conservador=tot[2030, 'Conservador'], total_2030_moderado=tot[2030, 'Moderado'], total_2030_agressivo=tot[2030, 'Agressivo'],
                        ucbt_2030_moderado=a[2030, 'Moderado'], b_original_2030_moderado=base[2030, 'Moderado'],
                        cagr_moderado_2025_2030=g('Moderado'), cagr_conservador=g('Conservador'), cagr_agressivo=g('Agressivo'),
                        amplitude_relativa_2030=(tot[2030, 'Agressivo'] - tot[2030, 'Conservador']) / tot[2030, 'Moderado'] if tot[2030, 'Moderado'] else None,
                        complemento_2030_moderado=tot[2030, 'Moderado'] - a[2030, 'Moderado'],
                        nota={'hierarquica_complemento': 'adotada: UCBT de A + complemento modelado pelo proprio historico',
                              'hierarquica_participacao': 'complemento proporcional a UCBT (participacao da ancora constante)',
                              'ajuste_minimo': 'mantem B onde nao viola; mistura o crescimento de dois modelos independentes',
                              'b_prevalece': 'referencia: altera a projecao UCBT do nivel A; nao admissivel'}[name]))
    return out


def audit(rows):
    out = []
    by = defaultdict(list)
    for r in rows:
        by[r['ano'], r['cenario']].append(r)
    for r in rows:
        if r['status'] != 'reconciliada':
            cls = 'sem_coorte'
        elif r['violacao_original']:
            cls = 'violacao_mesma_dist (diferenca de modelo supera o complemento)'
        elif r['diferenca_modelo'] != 0:
            cls = 'sem_violacao; diferenca de modelo'
        else:
            cls = 'sem_violacao; diferenca so de conceito'
        out.append(dict(r, classe=cls, efeito_na_trajetoria=None if r['ajuste'] is None else ('elevada' if r['ajuste'] > 0 else 'reduzida' if r['ajuste'] < 0 else 'inalterada')))
    for (y, s), rr in sorted(by.items()):
        rec = [r for r in rr if r['status'] == 'reconciliada']
        a = sum(r['ucbt_A'] for r in rec); b0 = sum(r['consumidores_B_original'] for r in rec); b1 = sum(r['consumidores_reconciliado'] for r in rec)
        out.append(dict(DIST='NACIONAL_COORTE', ano=y, cenario=s, ucbt_A=a, consumidores_B_original=b0, consumidores_reconciliado=b1, ajuste=b1 - b0,
                        violacao_original=b0 < a, classe='violacao_agregada_nacional' if b0 < a else 'agregado sem violacao',
                        diferenca_modelo=sum(r['diferenca_modelo'] for r in rec), diferenca_conceito_ancora=sum(r['diferenca_conceito_ancora'] for r in rec),
                        status='agregado', motivo=f"{sum(r['violacao_original'] for r in rec)} DIST com violacao local; deficit local {sum(min(0, r['consumidores_B_original'] - r['ucbt_A']) for r in rec)}"))
    return out


def national(rows):
    """Totals of the reconciled consumers on the comparable cohort only (anchor 2025, reconciled), with the original B and A."""
    t = defaultdict(lambda: defaultdict(float)); n = defaultdict(set)
    for r in rows:
        if r['status'] != 'reconciliada' or r['ancora'] != 2025:
            continue
        k = (r['ano'], r['cenario'])
        for f in ('ucbt_A', 'consumidores_B_original', 'consumidores_reconciliado', 'complemento'):
            t[k][f] += r[f]
        n[k].add(r['DIST'])
    sem = sorted({r['DIST'] for r in rows if r['status'] == 'sem_coorte'})
    other = sorted({r['DIST'] for r in rows if r['status'] == 'reconciliada' and r['ancora'] != 2025})
    return [dict(ano=k[0], cenario=k[1], dist_coorte=len(n[k]), **{f: int(v) for f, v in t[k].items()},
                 status_total='PARCIAL', motivo_parcial='coorte comparavel de DIST com ancora comum e complemento observado; DIST sem coorte: ' + ';'.join(map(str, sem))
                 + '; reconciliadas com ancora anterior a 2025 (fora dos totais): ' + ';'.join(map(str, other))
                 + '; as cooperativas sem estoque 2025 utilizavel ficam fora (ver TOTAIS_NACIONAIS_SERIES_COMPLETAS.csv)')
            for k in sorted(t)]


if __name__ == '__main__':
    r = run()
    print(json.dumps(dict(violacoes=r['contrato']['violacoes_remanescentes'], dist_reconciliadas=r['contrato']['dist_reconciliadas'],
                          sem_coorte=r['contrato']['dist_sem_coorte'], estrategias=[{k: x[k] for k in ('estrategia', 'violacoes_consumidores_menor_ucbt', 'total_2030_moderado', 'amplitude_relativa_2030', 'cagr_moderado_2025_2030')} for x in r['estrategias']],
                          totais_2030=r['totais']), ensure_ascii=False, indent=1, default=str))
