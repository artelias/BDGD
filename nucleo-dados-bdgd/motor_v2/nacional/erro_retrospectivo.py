"""End-to-end retrospective error of the reconciled consumers (Consumidores = UCBT + complemento) against the independent Level B model.

    python -m motor_v2.nacional.erro_retrospectivo

Nothing is retrained or re-run: the stored one-step backtest predictions of the Level A candidates (distributor totals per origin, from the
comparison summaries in force) are combined with the one-step baselines of the complement computed from the compatible-pair history, and
compared with the independent Level B backtest (stored per-origin errors of its candidates) on the SAME (DIST, origin) cells.

Cell = one DIST at one origin o in {2023, 2024}, predicting o+1 (horizon 1 year). A cell is comparable when
  * the complement is observed at o and o+1 (compatible pairs), and the o -> o+1 transition is not a break (B ineligible/succession, A rupture);
  * the Level A stored actual equals the audit UCBT of o+1 (the same closure used to build the pairs);
  * the independent Level B backtest has a stored error for that origin.
Variants (all use the same actual: Consumidores of o+1):
  E2E_reconciliado_escolhido   A candidate chosen by Level A + complement baseline chosen by the complement backtest;
  E2E_persistencia             A persistence + complement persistence (no model selection at all);
  E2E_A_escolhido_C_persist.   A chosen + complement persistence;
  B_escolhido / B_persistencia / B_deriva / B_cagr   independent Level B (stored errors).
LIMITS (carried into the report): 2 origins, horizon 1 only (the 2026-2030 horizon is not validated), the chosen variants were selected on
these same origins (in-sample selection, optimistic), no point-in-time vintage; nothing here is scientific validation."""
import csv
import json
import math
import statistics
from collections import defaultdict

from . import ROOT_OUT
from .hierarquia import BASELINES, ORIGINS, OUT, choose_complement, history, one_step, segment
from .relatorio import write_csv
from ..runner import atomic

A_PERSIST = 'persistencia:individual'
VARIANTS = ('E2E_reconciliado_escolhido', 'E2E_persistencia', 'E2E_A_escolhido_C_persistencia',
            'B_escolhido', 'B_persistencia', 'B_deriva', 'B_cagr')


def a_candidate_name(model):
    """Candidate key of the comparison summaries for a model name used by Level A (baselines are individual-scope)."""
    return f'{model}:individual' if model in BASELINES else model


def cells_for_dist(d, h, a_tot, a_model, c_kind, b_err, b_chosen):
    """One DIST -> (rows, excluded). h: hierarquia.history entry; a_tot: {candidate: {origin: (actual, pred)}} (Level A distributor totals);
    a_model: A model used in the projection; c_kind: complement baseline chosen; b_err: {candidate: {origin: abs error}} of the independent
    Level B backtest; b_chosen: B model used in the projection (None when B has no projection).
    Pure: no disk access. Every origin that cannot be compared is returned in `excluded` with its reason."""
    rows, excl = [], []
    a_name = a_candidate_name(a_model)
    for o in ORIGINS:
        why = None
        if o not in h['C'] or o + 1 not in h['C']:
            why = 'complemento nao observado em o e o+1 (par incompativel)'
        elif o + 1 in h['breaks']:
            why = 'transicao com ruptura/sucessao'
        elif a_name not in a_tot or o not in a_tot[a_name] or A_PERSIST not in a_tot or o not in a_tot[A_PERSIST]:
            why = 'previsao do nivel A ausente na origem'
        elif a_tot[a_name][o][0] != h['A'][o + 1]:
            why = 'real do nivel A difere da UCBT auditada'
        elif b_chosen is None or b_chosen not in b_err or o not in b_err[b_chosen] or any(k not in b_err or o not in b_err[k] for k in BASELINES):
            why = 'backtest do nivel B ausente na origem'
        if why:
            excl.append(dict(DIST=d, origem=o, motivo=why)); continue
        seg = segment(h['C'], h['breaks'], o)
        c = {k: one_step(k, seg)[0] for k in BASELINES}
        actual = h['B'][o + 1]
        a_ch, a_pe = a_tot[a_name][o][1], a_tot[A_PERSIST][o][1]
        pred = {'E2E_reconciliado_escolhido': a_ch + c[c_kind], 'E2E_persistencia': a_pe + c['persistencia'],
                'E2E_A_escolhido_C_persistencia': a_ch + c['persistencia']}
        r = dict(DIST=d, origem=o, alvo=o + 1, real_consumidores=actual, modelo_A=a_model, complemento_metodo=c_kind, modelo_B=b_chosen)
        for k, p in pred.items():
            r[k + '_pred'] = p; r[k + '_erro'] = p - actual; r[k + '_erro_abs'] = abs(p - actual)
        # independent Level B: signed error is exact only for persistence (history of the compatible pairs); the rest keeps the stored absolute error
        for k, n in (('B_escolhido', b_chosen), ('B_persistencia', 'persistencia'), ('B_deriva', 'deriva'), ('B_cagr', 'cagr')):
            r[k + '_erro_abs'] = b_err[n][o]
        r['B_persistencia_erro'] = h['B'][o] - actual
        rows.append(r)
    return rows, excl


def sign_test(wins, losses):
    """Two-sided exact sign test (ties dropped): p-value of `wins` vs `losses` under a fair coin."""
    n = wins + losses
    if n == 0:
        return 1.0
    k = min(wins, losses)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def summarize(rows, variants=VARIANTS):
    """Pooled and per-origin metrics of each variant on the common cells: MAE, WAPE (sum |e| / sum actual), bias (only where the signed error is
    stored), median absolute percentage error, share of cells where the variant beats the independent chosen B (paired wins/losses/ties and exact sign test
    against it) and the signed relative bias where the signed error is stored."""
    def block(rr):
        out = {}
        tot = sum(r['real_consumidores'] for r in rr)
        for v in variants:
            ae = [r[v + '_erro_abs'] for r in rr]
            m = dict(celulas=len(rr), mae=sum(ae) / len(ae) if ae else None, wape=sum(ae) / tot if tot else None,
                     mediana_ape=statistics.median(a / r['real_consumidores'] for a, r in zip(ae, rr)) if rr else None,
                     vence_B_escolhido=(sum(1 for r in rr if r[v + '_erro_abs'] < r['B_escolhido_erro_abs']) / len(rr)) if rr else None)
            if all((v + '_erro') in r for r in rr) and rr:
                m['vies_relativo'] = sum(r[v + '_erro'] for r in rr) / tot
            if v != 'B_escolhido' and rr:
                w = sum(1 for r in rr if r[v + '_erro_abs'] < r['B_escolhido_erro_abs']); l = sum(1 for r in rr if r[v + '_erro_abs'] > r['B_escolhido_erro_abs'])
                m.update(pareado_vitorias=w, pareado_derrotas=l, pareado_empates=len(rr) - w - l, pareado_p_teste_dos_sinais=sign_test(w, l))
            out[v] = m
        return out
    res = dict(todas=block(rows))
    for o in ORIGINS:
        res[f'origem_{o}'] = block([r for r in rows if r['origem'] == o])
    # sensitivity: the three largest companies carry a large share of the weighted metrics
    big = {d for d, _ in sorted(((r['DIST'], r['real_consumidores']) for r in rows), key=lambda x: -x[1])[:3]}
    res['sem_3_maiores'] = block([r for r in rows if r['DIST'] not in big])
    res['_maiores_excluidos'] = sorted(big)
    return res


# ----------------------------------------------------------------------------------------------------------- data
def _csv(p):
    return list(csv.DictReader(open(p, encoding='utf-8')))


def load_a_totals():
    """{DIST: {candidate: {origin: (actual, pred)}}} from the Level A comparison summaries in force (the revision batch supersedes)."""
    from .projecao import summaries
    out = {}
    for d, s in summaries('ucbt_quantidade').items():
        out[d] = {c['candidate']: {int(t['origin']): (float(t['actual']), float(t['pred'])) for t in c.get('distributor_totals', [])} for c in s['candidates']}
    return out


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    H = history(); A = load_a_totals()
    ma = {int(r['DIST']): r for r in _csv(ROOT_OUT / 'projecao' / 'DECISOES_A.csv') if r['ativo'] == 'ucbt'}
    mb = {int(r['DIST']): r for r in _csv(ROOT_OUT / 'distribuidora' / 'DECISOES_B.csv') if r['conceito'] == 'consumidores'}
    be = defaultdict(lambda: defaultdict(dict))
    for r in _csv(ROOT_OUT / 'distribuidora' / 'RESULTADOS_CANDIDATOS_B.csv'):
        if r['conceito'] == 'consumidores' and r['mae_por_origem']:
            be[int(r['DIST'])][r['candidato']] = {int(k): float(v) for k, v in json.loads(r['mae_por_origem']).items()}
    comp = {int(r['DIST']): r['metodo_complemento'] for r in _csv(OUT / 'COMPLEMENTO_POR_DIST.csv') if r['status'] == 'reconciliada'}
    rows, excl = [], []
    for d in sorted(comp):
        a_model = (ma.get(d) or {}).get('modelo_usado_na_projecao') or 'persistencia'
        b_model = (mb.get(d) or {}).get('modelo_usado_na_projecao') or None
        rr, ee = cells_for_dist(d, H[d], A.get(d, {}), a_model, comp[d], be.get(d, {}), b_model)
        rows += rr; excl += ee
    res = summarize(rows)
    write_csv(OUT / 'ERRO_RETROSPECTIVO_CONSUMIDORES_CELULAS.csv', rows)
    write_csv(OUT / 'ERRO_RETROSPECTIVO_CONSUMIDORES_EXCLUIDAS.csv', excl)
    flat = [dict(recorte=k, variante=v, **m) for k, blk in res.items() if not k.startswith('_') for v, m in blk.items()]
    write_csv(OUT / 'ERRO_RETROSPECTIVO_CONSUMIDORES.csv', flat)
    atomic(OUT / 'ERRO_RETROSPECTIVO_CONSUMIDORES_RESUMO.json', dict(
        celulas=len(rows), dist=len({r['DIST'] for r in rows}), excluidas=len(excl), motivos_exclusao=dict(sorted(
            ((m, sum(1 for e in excl if e['motivo'] == m)) for m in {e['motivo'] for e in excl}))),
        resultados=res, status='diagnostico_retrospectivo_NAO_e_validacao_cientifica',
        limites=['2 origens (2023, 2024), horizonte de 1 ano: o horizonte 2026-2030 nao foi validado',
                 'os modelos escolhidos (A, complemento e B) foram selecionados nas mesmas origens: comparacao otimista para as variantes escolhidas',
                 'sem vintage point-in-time', 'erro assinado do B disponivel so para a persistencia; os demais usam o erro absoluto armazenado']))
    return res, len(rows), len(excl)


if __name__ == '__main__':
    res, n, e = run()
    print(n, 'celulas;', e, 'excluidas')
    for k in ('todas', 'origem_2023', 'origem_2024', 'sem_3_maiores'):
        print('==', k)
        for v, m in res[k].items():
            print(f"  {v:34s} cel={m['celulas']:3d} MAE={m['mae'] or 0:10.1f} WAPE={m['wape'] or 0:.4%} medAPE={m['mediana_ape'] or 0:.4%} vence_B={m['vence_B_escolhido'] or 0:.2f}", f"vies={m['vies_relativo']:+.4%}" if 'vies_relativo' in m else '')
