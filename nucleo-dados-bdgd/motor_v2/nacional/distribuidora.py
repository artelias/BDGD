"""Level B: distributor-level series of EVERY national-contract concept (25 objectives), 2022-2025, experimental.

    python -m motor_v2.nacional.distribuidora

Source: output-historico/contrato-integracao/serie_fisica_nacional.csv, i.e. the values the existing ETL computed under the MCPSE/TUC
rules of each concept from the ordinary publication of each competence (no new extraction, no extraordinary base).
A cell is usable when estado is `observado` or `zero_verificado`, the base interval is annual and compatible and the cell may be
summed (`nao_somar_em_agregados` false). A transition t-1 -> t is comparable when both cells are usable and the contract records
no rupture at t.

Panel row = (DIST, concept, t) with a comparable transition. Features at t-1 only: log1p stock, log1p consumers, log1p MV network
km of the same DIST, and the previous comparable log1p growth (t-2 -> t-1, when it exists). Target: log1p growth t-1 -> t.
Backtest origins 2023 and 2024 (one test row per series per origin). ML scopes draw on the national panel of the same concept:
`grupo_economico` (controller at 2025-12-31, grupos_2025.json; unconfirmed control gives no pool) and `comparaveis` (the DIST and
its 9 nearest DIST by log stock and log consumers measured at t-1). Individual ML is impossible (<= 2 rows per series) and is
recorded as such. Feature subset and hyper-parameters are chosen on an inner origin (train <= o-1, validate on o) inside the pool;
without an inner origin the default subset is used and recorded."""
import csv
import json
import math
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

from . import CONTRACT, GROUPS, ROOT_OUT
from .cenarios import YEARS, baseline_path, lg, ml_path, scenarios, screen_table, screened_growth
from .selecao import BASELINES, choose, metrics
from ..metric_contract import round_count
from ..runner import atomic, digest, fingerprint

OUT = ROOT_OUT / 'distribuidora'
ORIGINS = (2023, 2024)
MODELS = ('ols', 'ridge', 'elastic_net', 'poisson', 'random_forest', 'hist_gradient_boosting')
SCOPES = ('grupo_economico', 'comparaveis')
K = 9
FEATURES = ('log_estoque', 'log_consumidores', 'log_rede_mt_km', 'crescimento_anterior')
SUBSETS = ([0], [0, 1], [0, 1, 2], [0, 3])
GRID = {'ols': [{}], 'ridge': [{'alpha': 1.}, {'alpha': 10.}], 'elastic_net': [{'alpha': .01, 'l1_ratio': .5}, {'alpha': .1, 'l1_ratio': .5}],
        'poisson': [{'alpha': .1}, {'alpha': 1.}], 'random_forest': [{'max_depth': 3, 'min_samples_leaf': 2}],
        'hist_gradient_boosting': [{'max_leaf_nodes': 7, 'learning_rate': .1, 'min_samples_leaf': 3}]}
SEED = 42


def load():
    cells, meta = {}, {}
    with open(CONTRACT, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            d, y, c = int(r['dist']), int(r['ano']), r['conceitoId']
            ok = r['estado'] in ('observado', 'zero_verificado') and r['valor'] != '' and r['intervalo_base'] == 'INTERVALO_ANUAL_COMPATIVEL' \
                and r['nao_somar_em_agregados'] != 'true'
            cells[d, c, y] = dict(value=float(r['valor']) if r['valor'] != '' else None, usable=ok, rupture=r['ruptura_desde_ano_anterior'] == 'true',
                                  estado=r['estado'], status=r['status_homologacao'], item=r['publicacao_id'], lacuna=r['tipo_lacuna'],
                                  intervalo=r['intervalo_base'], nao_somar=r['nao_somar_em_agregados'] == 'true')
            meta[c] = dict(metrica=r['metrica'], unidade=r['unidade'], natureza='discrete_count' if r['unidade'] == 'itens' else 'continuous_length')
            meta.setdefault(('empresa', d), r['empresa'])
    return cells, meta


def groups():
    g = json.loads(Path(GROUPS).read_text(encoding='utf-8'))
    out = {}
    for x in g['grupos']:
        for d in x['dists']:
            out[int(d)] = x['grupo_id']
    return out, digest(GROUPS)


def comparable(cells, d, c, t):
    a, b = cells.get((d, c, t - 1)), cells.get((d, c, t))
    return bool(a and b and a['usable'] and b['usable'] and not b['rupture'])


def row(cells, d, c, t):
    """Features at t-1 (and t-2 for the previous growth) for the step t-1 -> t; y is None for a projection row."""
    prev = cells[d, c, t - 1]['value']
    cons = cells.get((d, 'consumidores', t - 1)); mt = cells.get((d, 'rede_mt', t - 1))
    g_prev = lg(prev) - lg(cells[d, c, t - 2]['value']) if comparable(cells, d, c, t - 1) else None
    y = cells[d, c, t]['value'] if (d, c, t) in cells and t <= 2025 else None
    return dict(dist=d, concept=c, year=t, stock=prev, y=y,
                x=[lg(prev), lg(cons['value']) if cons and cons['usable'] else None, lg(mt['value']) if mt and mt['usable'] else None, g_prev])


def panel(cells, concepts, dists):
    return [row(cells, d, c, t) for c in concepts for d in dists for t in (2023, 2024, 2025) if comparable(cells, d, c, t)]


def build(model, params):
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LinearRegression, Ridge, ElasticNet, PoissonRegressor
    from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
    f = {'ols': LinearRegression, 'ridge': Ridge, 'elastic_net': ElasticNet, 'poisson': PoissonRegressor,
         'random_forest': RandomForestRegressor, 'hist_gradient_boosting': HistGradientBoostingRegressor}[model]
    kw = dict(params)
    if model == 'random_forest':
        kw.update(n_estimators=64, random_state=SEED, n_jobs=1)
    if model == 'hist_gradient_boosting':
        kw.update(max_iter=80, random_state=SEED)
    if model == 'elastic_net':
        kw.update(max_iter=5000, random_state=SEED)
    if model == 'poisson':
        kw.update(max_iter=1000)
    return Pipeline([('scale', StandardScaler()), ('model', f(**kw))])


def fit_predict(model, params, feats, train, test):
    """-> predicted log1p growth for each test row, or raises. Rows lacking a selected feature are left out (no imputation)."""
    tr = [r for r in train if all(r['x'][i] is not None for i in feats)]
    if len(tr) < 4 or len({r['dist'] for r in tr}) < 2:
        raise ValueError('pool insuficiente (<4 linhas completas ou <2 DIST)')
    if any(r['x'][i] is None for r in test for i in feats):
        raise ValueError('feature ausente na linha de teste')
    X = np.array([[r['x'][i] for i in feats] for r in tr]); Xt = np.array([[r['x'][i] for i in feats] for r in test])
    g = np.array([lg(r['y']) - lg(r['stock']) for r in tr])
    m = build(model, params)
    if model == 'poisson':
        m.fit(X, np.exp(g)); out = np.log(np.maximum(m.predict(Xt), 1e-12))
    else:
        m.fit(X, g); out = m.predict(Xt)
    if not np.isfinite(out).all():
        raise ValueError('previsao nao finita')
    return out.tolist()


def level(stock, g):
    return max(math.expm1(lg(stock) + g), 0.0)


def pool(rows, concept, d, origin, scope, grp, test_row):
    tr = [r for r in rows if r['concept'] == concept and r['year'] <= origin]
    if scope == 'grupo_economico':
        gid = grp.get(d)
        if not gid:
            return [], 'controle nao confirmado'
        members = {r['dist'] for r in tr if grp.get(r['dist']) == gid} | {d}
        if len(members) < 2:
            return [], 'grupo com uma DIST'
        return [r for r in tr if r['dist'] in members], None
    last = {}
    for r in tr:
        if r['x'][1] is not None and (r['dist'] not in last or r['year'] > last[r['dist']]['year']):
            last[r['dist']] = r
    if test_row['x'][1] is None:
        return [], 'consumidores ausentes em t-1'
    prof = {k: (v['x'][0], v['x'][1]) for k, v in last.items() if k != d}
    prof[d] = (test_row['x'][0], test_row['x'][1])
    keys = sorted(prof); m = np.array([prof[k] for k in keys]); sd = m.std(axis=0); sd[sd == 0] = 1
    z = (m - m.mean(axis=0)) / sd; me = z[keys.index(d)]
    near = [k for _, k in sorted((float(np.linalg.norm(z[i] - me)), k) for i, k in enumerate(keys) if k != d)[:K]]
    return [r for r in tr if r['dist'] in set(near) | {d}], None


def select(rows, concept, d, origin, scope, model, grp, test_row):
    """Inner selection: train <= origin-1, validate on rows with year == origin (same pool rule)."""
    inner, _ = pool(rows, concept, d, origin - 1, scope, grp, test_row)
    val = [r for r in pool(rows, concept, d, origin, scope, grp, test_row)[0] if r['year'] == origin]
    trials = []
    for feats in SUBSETS:
        for p in GRID[model]:
            try:
                pr = fit_predict(model, p, feats, inner, [v for v in val if all(v['x'][i] is not None for i in feats)])
                vv = [v for v in val if all(v['x'][i] is not None for i in feats)]
                if not vv:
                    raise ValueError('sem validacao interna')
                trials.append((float(np.mean([abs(a - (lg(v['y']) - lg(v['stock']))) for a, v in zip(pr, vv)])), len(feats), feats, p))
            except ValueError:
                continue
    if trials:
        mae, _, feats, p = min(trials, key=lambda t: (t[0], t[1]))
        return feats, p, 'selecao_interna', len(trials)
    feats = [0, 1] if test_row['x'][1] is not None else [0]
    return feats, GRID[model][0], 'padrao_sem_origem_interna', 0


def segment(cells, d, c, origin):
    if not (cells.get((d, c, origin)) or {}).get('usable'):
        return []
    seg, t = [(origin, cells[d, c, origin]['value'])], origin
    while comparable(cells, d, c, t):
        t -= 1; seg.insert(0, (t, cells[d, c, t]['value']))
    return seg


def run():
    t0 = time.monotonic()
    OUT.mkdir(parents=True, exist_ok=True)
    cells, meta = load()
    grp, gsha = groups()
    concepts = sorted(k for k in meta if isinstance(k, str))
    dists = sorted({d for d, _, _ in cells})
    rows = panel(cells, concepts, dists)
    results, decisions, projections, unavailable = [], [], [], []
    cache = {}
    tables = {c: concept_table(cells, c, dists) for c in concepts}
    for c in concepts:
        nature = meta[c]['natureza']
        for d in dists:
            cands = {}
            preds = defaultdict(list); detail = defaultdict(list)
            for o in ORIGINS:
                if not comparable(cells, d, c, o + 1):
                    continue
                test = row(cells, d, c, o + 1)
                seg = segment(cells, d, c, o)
                for b in BASELINES:
                    value, why = one_step(b, seg)
                    preds[b].append((o, test['y'], value))
                    detail[b].append(dict(origem=o, fallback=why))
                for model in MODELS:
                    if model == 'poisson' and nature != 'discrete_count':
                        continue
                    for scope in SCOPES:
                        name = f'{model}:{scope}'
                        tr, why = pool(rows, c, d, o, scope, grp, test)
                        if why:
                            detail[name].append(dict(origem=o, falha=why)); continue
                        key = (c, scope, grp.get(d) if scope == 'grupo_economico' else d, o, model)
                        try:
                            if key not in cache:
                                cache[key] = select(rows, c, d, o, scope, model, grp, test)
                            feats, p, how, ntr = cache[key]
                            g = fit_predict(model, p, feats, tr, [test])[0]
                            preds[name].append((o, test['y'], level(test['stock'], g)))
                            detail[name].append(dict(origem=o, features=[FEATURES[i] for i in feats], params=p, selecao=how, tentativas=ntr,
                                                     dist_no_pool=len({r['dist'] for r in tr}), linhas_treino=len(tr)))
                        except ValueError as e:
                            detail[name].append(dict(origem=o, falha=str(e)))
            for name, pr in preds.items():
                kind = 'baseline' if name in BASELINES else 'ml'
                fb = [x for x in detail[name] if x.get('fallback')]
                cands[name] = dict(kind=kind, keys={o for o, _, _ in pr}, m=metrics(pr),
                                   fallback_share=len(fb) / len(pr) if kind == 'baseline' and pr else None)
                m = cands[name]['m']
                results.append(dict(DIST=d, conceito=c, metrica=meta[c]['metrica'], unidade=meta[c]['unidade'], natureza=nature, candidato=name,
                                    modelo=name.split(':')[0], escopo=name.split(':')[1] if ':' in name else 'individual',
                                    origens=m['origens'], previsoes=m['n'], mae=m['mae'], rmse=m['rmse'], wape=m['wape'], vies=m['vies'], score_robusto=m['robusto'],
                                    mae_por_origem=json.dumps(m['mae_por_origem']),
                                    erro_fisico_mae=float(np.mean([abs(round_count(p) - a) for _, a, p in pr])) if nature == 'discrete_count' else None,
                                    detalhe=json.dumps(detail[name], ensure_ascii=False)))
            for name in [f'{m}:{s}' for m in MODELS for s in SCOPES]:
                if name not in preds and detail.get(name):
                    results.append(dict(DIST=d, conceito=c, metrica=meta[c]['metrica'], unidade=meta[c]['unidade'], natureza=nature, candidato=name,
                                        modelo=name.split(':')[0], escopo=name.split(':')[1], origens=0, previsoes=0,
                                        detalhe=json.dumps(detail[name], ensure_ascii=False)))
            dec = choose(cands) if cands else choose({})
            # projection
            anchor = max((y for y in range(2022, 2026) if (cells.get((d, c, y)) or {}).get('usable')), default=None)
            rec = dict(DIST=d, empresa=meta.get(('empresa', d)), conceito=c, metrica=meta[c]['metrica'], unidade=meta[c]['unidade'], natureza=nature,
                       grupo=grp.get(d), ano_ancora=anchor, **{k: v for k, v in dec.items()})
            if anchor is None:
                why = sorted({(cells.get((d, c, y)) or {}).get('estado', 'sem_celula') + ':' + ((cells.get((d, c, y)) or {}).get('lacuna') or '') for y in range(2022, 2026)})
                unavailable.append(dict(nivel='B', DIST=d, conceito=c, motivo='nenhuma competencia utilizavel no contrato (' + '; '.join(why) + ')'))
                rec.update(status_projecao='bloqueada', motivo_projecao='sem competencia utilizavel'); decisions.append(rec); continue
            seg = segment(cells, d, c, anchor)
            chosen = dec['modelo_projecao']; note = None
            if chosen in BASELINES:
                path, fb = baseline_path(chosen, seg, anchor); note = fb
            else:
                model, scope = chosen.split(':')
                try:
                    prow = dict(row(cells, d, c, anchor + 1), y=None)
                    tr, why = pool(rows, c, d, anchor, scope, grp, prow)
                    if why:
                        raise ValueError(why)
                    feats, p, how, _ = select(rows, c, d, anchor, scope, model, grp, prow)
                    g = fit_predict(model, p, feats, tr, [prow])[0]
                    path = ml_path(seg[-1][1], level(seg[-1][1], g), anchor)
                    note = f'ML {model}/{scope} features={[FEATURES[i] for i in feats]} params={p} ({how})'
                except ValueError as e:
                    path, fb = baseline_path(dec['modelo_fallback'], seg, anchor)
                    note = f'ML escolhido nao projetavel ({e}); usado o fallback {dec["modelo_fallback"]}'; chosen = dec['modelo_fallback']
            pts, breaks = series_points(cells, d, c, anchor)
            kept, atypical = screened_growth(pts, breaks, tables[c])
            sc, smeta = scenarios(anchor, seg[-1][1], path, kept)
            smeta['transicoes_atipicas_excluidas'] = atypical
            rec.update(status_projecao='gerada', modelo_usado_na_projecao=chosen, nota_projecao=note, horizonte_real=f'{2026 - anchor}..{2030 - anchor} anos a partir de {anchor}',
                       ancora_2025=anchor == 2025, valor_ancora=seg[-1][1], **{'cenario_' + k: v for k, v in smeta.items() if k != 'regra'})
            decisions.append(rec)
            for s, vals in sc.items():
                for y in YEARS:
                    v = vals[y]
                    projections.append(dict(nivel='B_distribuidora', DIST=d, conceito=c, metrica=meta[c]['metrica'], unidade=meta[c]['unidade'], natureza=nature,
                                            ano_ancora=anchor, horizonte=y - anchor, ano=y, cenario=s,
                                            valor=round_count(v) if nature == 'discrete_count' else round(v, 6), valor_bruto=v,
                                            modelo=chosen, base=dec['base_da_projecao'] if chosen == dec['modelo_projecao'] else 'modelo_fallback',
                                            status='experimental_interno_nao_publicavel'))
    prov = dict(contrato=str(CONTRACT), contrato_sha256=digest(CONTRACT), grupos_sha256=gsha, codigo=fingerprint({p.name: digest(p) for p in Path(__file__).parent.glob('*.py')}),
                origens=ORIGINS, modelos=MODELS, escopos=SCOPES, k_comparaveis=K, features=FEATURES, subsets=SUBSETS, grade=GRID, semente=SEED,
                linhas_painel=len(rows), segundos=round(time.monotonic() - t0, 1))
    return dict(results=results, decisions=decisions, projections=projections, unavailable=unavailable, provenance=prov)


def series_points(cells, d, c, last=2025):
    pts = {y: cells[d, c, y]['value'] for y in range(2022, last + 1) if (cells.get((d, c, y)) or {}).get('usable')}
    return pts, {y for y in pts if not comparable(cells, d, c, y)}


def concept_table(cells, c, dists):
    ser, br = {}, {}
    for d in dists:
        ser[d], br[d] = series_points(cells, d, c)
    return screen_table(ser, br)


def reenvelope():
    """Recompute the conservative/aggressive envelopes of an existing Level B run from its saved moderate paths (same decisions,
    same moderate values), applying the cross-sectional atypical-transition screen; rewrites projections and decisions."""
    import pyarrow.parquet as pq
    from .relatorio import write_csv, write_parquet
    cells, meta = load()
    dists = sorted({d for d, _, _ in cells}); concepts = sorted(k for k in meta if isinstance(k, str))
    tables = {c: concept_table(cells, c, dists) for c in concepts}
    old = pq.read_table(OUT / 'PROJECOES_B_INTERNO.parquet').to_pylist()
    mod = defaultdict(dict); info = {}
    for r in old:
        if r['cenario'] == 'Moderado':
            mod[r['DIST'], r['conceito']][r['ano']] = r['valor_bruto']; info[r['DIST'], r['conceito']] = r
    decisions = list(csv.DictReader(open(OUT / 'DECISOES_B.csv', encoding='utf-8')))
    projections = []
    for dec in decisions:
        if dec['status_projecao'] != 'gerada':
            continue
        d, c = int(dec['DIST']), dec['conceito']; anchor = int(dec['ano_ancora']); r0 = info[d, c]
        pts, breaks = series_points(cells, d, c, anchor)
        kept, atypical = screened_growth(pts, breaks, tables[c])
        sc, smeta = scenarios(anchor, float(dec['valor_ancora']), mod[d, c], kept)
        smeta['transicoes_atipicas_excluidas'] = atypical
        dec.update({'cenario_' + k: (json.dumps(v) if isinstance(v, list) else v) for k, v in smeta.items() if k != 'regra'})
        for s_, vals in sc.items():
            for y in YEARS:
                v = vals[y]
                projections.append(dict(r0, horizonte=y - anchor, ano=y, cenario=s_, valor=round_count(v) if r0['natureza'] == 'discrete_count' else round(v, 6), valor_bruto=v))
    write_csv(OUT / 'DECISOES_B.csv', decisions)
    write_csv(OUT / 'PROJECOES_B.csv', [{k: v for k, v in r.items() if k != 'valor_bruto'} for r in projections])
    write_parquet(OUT / 'PROJECOES_B_INTERNO.parquet', projections)
    m = json.loads((OUT / 'MANIFESTO_B.json').read_text(encoding='utf-8'))
    m['reenvelope'] = dict(regra='transicoes atipicas (mediana +- 5 MAD no corte nacional do conceito) fora do envelope dos cenarios; trajetoria moderada inalterada',
                           series=len({(r['DIST'], r['conceito']) for r in projections}), transicoes_excluidas=sum(len(json.loads(x['cenario_transicoes_atipicas_excluidas'] or '[]')) for x in decisions if x['status_projecao'] == 'gerada'))
    atomic(OUT / 'MANIFESTO_B.json', m)
    return m['reenvelope']


def one_step(kind, seg):
    """One-step forecast for origin+1 with the formulas of motor_v2.baselines; persistence (with the reason) when undefined."""
    t1, y1 = seg[-1]
    if kind == 'persistencia':
        return y1, None
    if len(seg) < 2:
        return y1, 'short_series'
    t0, y0 = seg[0]
    if kind == 'deriva':
        v = y1 + (y1 - y0) / (t1 - t0)
        return (v, None) if v >= 0 else (y1, 'negative_forecast')
    if y0 <= 0 or y1 <= 0:
        return y1, 'nonpositive_endpoint'
    return y1 * (y1 / y0) ** (1 / (t1 - t0)), None


def write(res):
    from .relatorio import write_csv, write_parquet
    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / 'RESULTADOS_CANDIDATOS_B.csv', res['results'])
    write_csv(OUT / 'DECISOES_B.csv', res['decisions'])
    write_csv(OUT / 'PROJECOES_B.csv', [{k: v for k, v in r.items() if k != 'valor_bruto'} for r in res['projections']])
    write_parquet(OUT / 'PROJECOES_B_INTERNO.parquet', res['projections'])
    write_csv(OUT / 'INDISPONIVEIS_B.csv', res['unavailable'])
    atomic(OUT / 'MANIFESTO_B.json', res['provenance'])


if __name__ == '__main__':
    r = run(); write(r)
    print(json.dumps(dict(candidatos=len(r['results']), series=len(r['decisions']), projecoes=len(r['projections']), indisponiveis=len(r['unavailable']),
                          segundos=r['provenance']['segundos'])))
