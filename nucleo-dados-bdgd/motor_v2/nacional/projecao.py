"""Level A projections 2026-2030 per DIST x asset x territorial unit, three scenarios, reconciled to the company total.

    python -m motor_v2.nacional.projecao

Decision per DIST x asset (selecao.choose) from the comparison summaries (mode reconciled_retrospective; point-in-time has no
eligible origin). Anchor = the latest competence with a valid physical total (2025 when it exists); a company without 2025
keeps its last reliable competence and the real horizon is recorded.

Cohort = territorial units of the anchor that pass the panel rules (official code, coverage gate, quarantine, bridges). The rest
of the company total (codes outside the IBGE list, units without CONJ, unlinked transformers...) is the explicit residual
`NAO_TERRITORIALIZADO`, projected with the cohort's aggregate path. Company total = cohort + residual, exactly; for counts the
integer total is the half-up rounding of the raw total and units are allocated by largest remainder (Hamilton), so territorial
integers always add up to the company integer. Lengths and capacities keep their unit and decimals."""
import json
import math
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from . import LEVEL_A, ROOT_OUT
from .cenarios import YEARS, baseline_path, ml_path, scenarios, screen_table, screened_growth
from .comparativos import ALIAS, EXTERNAL, OUT as CMP, grupos
from .painel import PANEL
from .relatorio import write_csv, write_parquet
from .selecao import BASELINES, choose
from ..runner import ROOT, atomic, digest, fingerprint, read

OUT = ROOT_OUT / 'projecao'
MODE = 'reconciled_retrospective'


def summaries(asset):
    out = {}
    st = read(CMP / 'STATUS.json')
    for bid, r in st['lotes'].items():
        if r['ativo'] != asset or r.get('estado') != 'completed':
            continue
        for s in read(Path(r['output']) / 'summaries.json'):
            if s['mode'] == MODE:
                out[s['dist']] = dict(s, _batch=bid, _output=r['output'])
    return out


def candidates(summary):
    """selecao.choose input from a comparison summary (same test keys = common_test_set flag of the comparison)."""
    out = {}
    for c in summary['candidates']:
        model, scope = c['candidate'].split(':', 1)
        name = model if model in BASELINES and scope == 'individual' else c['candidate']
        per = {str(x['origin']): x['mae'] for x in c.get('by_origin', [])}
        m = None
        if c.get('n_predictions') and c.get('robust_score') is not None:
            mt = c['metrics']
            m = dict(n=c['n_predictions'], origens=c['independent_origins'], mae=mt.get('mae'), rmse=mt.get('rmse'), vies=mt.get('bias'),
                     wape=mt.get('wape'), mae_por_origem=per, robusto=c['robust_score'])
        fb = sum(f['explanation'].get('fallback_rows', 0) for f in c.get('folds', [])) if model in BASELINES else 0
        out[name] = dict(kind='baseline' if name in BASELINES else 'ml', keys={'comum'} if c.get('common_test_set') else {'outro'},
                         m=m, fallback_share=(fb / c['n_predictions']) if model in BASELINES and c.get('n_predictions') else None,
                         _raw=c)
    if 'persistencia' in out and out['persistencia']['m']:
        out['persistencia']['keys'] = {'comum'}
    return out


def chosen_option(raw):
    """(params, feature indices) used at the LAST origin, most frequent across its territorial folds."""
    from ..features import FEATURES
    folds = raw.get('folds', [])
    if not folds:
        return None
    last = max(f['origin'] for f in folds)
    c = Counter(json.dumps([f['params'], f['selected_features']], sort_keys=True) for f in folds if f['origin'] == last)
    params, feats = json.loads(c.most_common(1)[0][0])
    return params, [FEATURES.index(f) for f in feats]


def panel_rows(asset, quarantine, vm, pool):
    from ..comparison import load_panel
    from ..bridges import load as load_bridges
    from ..assets import ASSETS
    from ..features import attach_snapshot_features
    from ..externals import attach
    from .. import shared
    spec = ASSETS[asset]
    rows, quality, prov = load_panel(str(PANEL), asset, load_bridges(ROOT / 'motor_v2/bridges'), 0.98,
                                     0.95 if asset.startswith('rede_') else None, future_year=2026, valid_municipalities=vm, quarantine=quarantine)
    rows = attach(rows, EXTERNAL)
    if asset != 'ucbt_quantidade':
        matrix = shared.build(str(PANEL), str(PANEL), pool, spec['unit_kind']); rows = shared.attach(rows, matrix, asset)
    rows = attach_snapshot_features([dict(r, recent_connection_share=None) for r in rows])
    gr = grupos()
    rows = [dict(r, grupo=gr.get(str(r['dist']), 'nao_confirmado')) for r in rows]
    return rows, quality, spec


def project_dist(d, asset, spec, rows, quality, summary, table=None):
    from ..comparison import fit_predict, scope_pool
    from ..baselines import segment
    from ..metric_contract import allocate, round_count
    from ..policy import FeaturePolicy
    nature = spec['nature']; count = nature == 'discrete_count'
    q = {r['year']: r for r in quality if r['dist'] == d}
    years = sorted(y for y, r in q.items() if r.get('physical_total') is not None)
    base = dict(DIST=d, ativo=spec['ativo'], metrica=spec['metrica'], unidade=spec['unit'], natureza=nature, unidade_territorial=spec['unit_kind'])
    if not years:
        return dict(base, status_projecao='bloqueada', motivo_projecao='nenhuma competencia com total fisico valido (extracao/regra de qualidade)'), [], []
    anchor = years[-1]; total0 = float(q[anchor]['physical_total'])
    cands = candidates(summary) if summary else {}
    dec = choose(cands) if cands else choose({})
    if not summary:
        dec['motivo_experimental'] = 'DIST sem transicao comparavel no painel (menos de 2 competencias): nada medido'
    fut = [r for r in rows if r.get('future') and r['dist'] == d and r['feature_year'] == anchor and not r['rupture']] if anchor == 2025 else []
    units = {r['group']: r['stock'] for r in fut}
    chosen, note = dec['modelo_projecao'], None
    paths = {}
    if chosen not in BASELINES and units:
        model, scope = chosen.split(':', 1)
        raw = cands[chosen]['_raw']; opt = chosen_option(raw)
        try:
            if opt is None:
                raise ValueError('sem fold registrado para reconstruir a escolha')
            params, feats = opt
            train, peers = scope_pool([r for r in rows if not r.get('future')], d, anchor, MODE, scope, set())
            pred, _ = fit_predict(model, dict(params=params, features=feats, mode=MODE, policy=FeaturePolicy().as_dict()), train, fut, 42)
            paths = {r['group']: ml_path(r['stock'], p, anchor) for r, p in zip(fut, pred)}
            from ..features import FEATURES
            note = f'{model}/{scope}: params={params} features={[FEATURES[i] for i in feats]} pool={len(peers) or 1} DIST, {len(train)} linhas de treino ate {anchor}'
        except Exception as e:
            note = f'ML escolhido nao projetavel ({e}); usado o fallback {dec["modelo_fallback"]}'
            chosen = dec['modelo_fallback']; paths = {}
    if chosen in BASELINES:
        hist = [r for r in rows if r['dist'] == d and not r.get('future')]
        by = defaultdict(list)
        for r in hist:
            by[r['group']].append(r)
        fb = Counter()
        for u, s in units.items():
            seg, _ = segment(by.get(u, []), d, u, anchor, MODE)
            p, why = baseline_path(chosen, seg if seg else [(anchor, s)], anchor)
            paths[u] = p
            if why:
                fb[why] += 1
        if fb:
            note = (note + '; ' if note else '') + f'fallback para persistencia em {sum(fb.values())} unidades: {dict(fb)}'
    cohort0 = sum(units.values())
    residual0 = total0 - cohort0
    agg = {y: (sum(p[y] for p in paths.values()) / cohort0) if cohort0 > 0 else 1.0 for y in YEARS}
    if not units:
        # no territorial cohort at the anchor: the company total follows the chosen baseline on its own physical totals
        seg = [(y, float(q[y]['physical_total'])) for y in years]
        cut = [i for i, (y, _) in enumerate(seg) if i and (seg[i - 1][0] != y - 1 or q[y].get('rupture'))]
        seg = seg[cut[-1]:] if cut else seg
        k = chosen if chosen in BASELINES else dec['modelo_fallback']
        tp, why = baseline_path(k, seg, anchor)
        agg = {y: tp[y] / total0 if total0 else 1.0 for y in YEARS}
        note = (note + '; ' if note else '') + f'sem coorte territorial em {anchor}: total projetado por {k} sobre os totais fisicos' + (f' ({why})' if why else '')
        chosen = k
    mod_total = {y: sum(p[y] for p in paths.values()) + residual0 * agg[y] for y in YEARS}
    pts = {y: float(q[y]['physical_total']) for y in years}
    breaks = _breaks(q, years)
    kept, atypical = screened_growth(pts, breaks, table or {})
    sc, smeta = scenarios(anchor, total0, mod_total, kept)
    smeta['transicoes_atipicas_excluidas'] = atypical
    terr, tot = [], []
    for s, tpath in sc.items():
        for y in YEARS:
            f = tpath[y] / mod_total[y] if mod_total[y] > 0 else 0.0
            raw = {u: p[y] * f for u, p in paths.items()}
            raw['NAO_TERRITORIALIZADO'] = residual0 * agg[y] * f
            if count:
                t_int = round_count(tpath[y])
                alloc = allocate({k: max(v, 0.0) for k, v in raw.items()}, t_int)
                assert sum(alloc.values()) == t_int
            for u, v in raw.items():
                terr.append(dict(base, ano_ancora=anchor, horizonte=y - anchor, ano=y, cenario=s, unidade_codigo=u,
                                 valor=alloc[u] if count else round(v, 6), valor_bruto=v, status='experimental_interno_nao_publicavel'))
            tot.append(dict(base, ano_ancora=anchor, horizonte=y - anchor, ano=y, cenario=s, valor=t_int if count else round(tpath[y], 6),
                            valor_bruto=tpath[y], unidades_territoriais=len(paths), residuo_ancora=residual0, modelo=chosen,
                            status='experimental_interno_nao_publicavel'))
    dec_out = dict(base, ano_ancora=anchor, ancora_2025=anchor == 2025, horizonte_real=f'{2026 - anchor}..{2030 - anchor} anos a partir de {anchor}',
                   total_ancora=total0, coorte_ancora=cohort0, residuo_ancora=residual0, unidades=len(paths), **{k: v for k, v in dec.items()},
                   modelo_usado_na_projecao=chosen, nota_projecao=note, status_projecao='gerada',
                   **{'cenario_' + k: v for k, v in smeta.items() if k != 'regra'})
    return dec_out, terr, tot


def _breaks(q, years):
    return {y for y in years if q[y].get('rupture') or (y - 1) in q and not q[y].get('gate_ok', True)}


def physical_series(quality):
    pts, br = {}, {}
    for d in {r['dist'] for r in quality}:
        q = {r['year']: r for r in quality if r['dist'] == d}
        ys = sorted(y for y, r in q.items() if r.get('physical_total') is not None)
        pts[d] = {y: float(q[y]['physical_total']) for y in ys}; br[d] = _breaks(q, ys)
    return pts, br


def run():
    t0 = time.monotonic()
    qz = read(ROOT_OUT / 'quarentena.json')
    vm = set(json.loads(Path(qz['municipios_validos']).read_text(encoding='utf-8')))
    decisions, terr, tot, blocked = [], [], [], []
    for asset in LEVEL_A:
        from .painel import dists_with
        pool = dists_with(asset, 1)
        rows, quality, spec = panel_rows(asset, qz['quarentena'], vm, pool)
        summ = summaries(asset)
        table = screen_table(*physical_series(quality))
        for d in pool:
            try:
                dec, t, s = project_dist(d, asset, spec, rows, quality, summ.get(d), table)
            except Exception as e:
                dec, t, s = dict(DIST=d, ativo=spec['ativo'], metrica=spec['metrica'], status_projecao='falha', motivo_projecao=str(e)), [], []
            decisions.append(dec); terr += t; tot += s
            if dec.get('status_projecao') != 'gerada':
                blocked.append(dict(nivel='A', DIST=d, ativo=asset, motivo=dec.get('motivo_projecao')))
        print(asset, len(pool), round(time.monotonic() - t0), flush=True)
    # reconciliation proof: territorial (incl. residual) == company total, per DIST x asset x scenario x year
    sums = defaultdict(float)
    for r in terr:
        sums[r['DIST'], r['ativo'], r['metrica'], r['cenario'], r['ano']] += r['valor']
    bad = [r for r in tot if abs(sums[r['DIST'], r['ativo'], r['metrica'], r['cenario'], r['ano']] - r['valor']) > (0 if r['natureza'] == 'discrete_count' else 1e-3)]
    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / 'DECISOES_A.csv', decisions)
    write_csv(OUT / 'PROJECOES_A_DISTRIBUIDORA.csv', [{k: v for k, v in r.items() if k != 'valor_bruto'} for r in tot])
    write_parquet(OUT / 'PROJECOES_A_TERRITORIAL_INTERNO.parquet', terr)
    write_parquet(OUT / 'PROJECOES_A_DISTRIBUIDORA_INTERNO.parquet', tot)
    write_csv(OUT / 'INDISPONIVEIS_A.csv', blocked)
    atomic(OUT / 'MANIFESTO_A.json', dict(painel=str(PANEL), quarentena=qz['quarentena'], comparativos=str(CMP / 'STATUS.json'),
                                          codigo=fingerprint({p.name: digest(p) for p in Path(__file__).parent.glob('*.py')}),
                                          reconciliacao_falhas=len(bad), linhas_territoriais=len(terr), linhas_distribuidora=len(tot),
                                          segundos=round(time.monotonic() - t0, 1)))
    return decisions, terr, tot, blocked, bad


if __name__ == '__main__':
    d, t, s, b, bad = run()
    print(json.dumps(dict(decisoes=len(d), territoriais=len(t), totais=len(s), bloqueadas=len(b), falhas_reconciliacao=len(bad))))
