"""Projection paths and the three documented scenarios (no future covariate, no confidence interval, no official premise).

Moderate  = the path of the model chosen for projection (experimental when stable, otherwise the fallback baseline):
            persistence  y(T+h) = y(T)
            drift        y(T+h) = y(T) + h * slope of the comparable segment ending at T
            CAGR         y(T+h) = y(T) * g ** h
            ML           y(T+h) = expm1(log1p y(T) + h * d), d = the model's one-step change in log1p, held constant
                         (no future covariates exist, so later steps repeat the first one: a mathematical hypothesis, documented)
Conservative / aggressive = the moderate path with its mean annual log1p growth shifted to the LOWEST / HIGHEST annual log1p
            growth observed in the series' own comparable transitions 2022-2025 whenever that is more extreme than the moderate
            growth (otherwise they coincide with the moderate path). Which transitions enter this envelope is decided by the
            screen v2 below (documented evidence, then same object x year x size class, then the temporal pattern of the jump);
            excluded transitions are reported with their class and never change the moderate path. The v1 screen (national
            median +- 5 MAD only) is kept for the sensitivity audit. Ordering cons <= mod <= agr holds by construction. Values
            are floored at zero (physical stock), and a floor is reported."""
import math

YEARS = (2026, 2027, 2028, 2029, 2030)


def lg(v):
    return math.log1p(max(v, 0.0))


def hist_growth(points, breaks=()):
    """points {year: value} of comparable observations; `breaks` years whose step from year-1 is not comparable."""
    out = []
    for y in sorted(points):
        if y - 1 in points and y not in breaks and points[y] is not None and points[y - 1] is not None:
            out.append(lg(points[y]) - lg(points[y - 1]))
    return out


MAD_K = 5.0          # a transition is atypical when its growth is beyond median +- 5 MAD of all companies, same object and year
MAD_FLOOR = 0.02     # log1p units: with K=5 a jump must be >= ~10 p.p. away from the national median growth of the year


def screen_table(series, breaks):
    """series {dist: {year: value}}, breaks {dist: set(years)} -> {year: (median, mad)} of the comparable log1p growths
    year-1 -> year across companies (the cross-section of one object)."""
    import statistics
    by = {}
    for d, pts in series.items():
        for y in sorted(pts):
            if y - 1 in pts and y not in breaks.get(d, ()) and pts[y] is not None and pts[y - 1] is not None:
                by.setdefault(y, []).append(lg(pts[y]) - lg(pts[y - 1]))
    out = {}
    for y, g in by.items():
        med = statistics.median(g)
        out[y] = (med, max(statistics.median([abs(x - med) for x in g]), MAD_FLOOR), len(g))
    return out


def screened_growth(points, breaks, table):
    """Comparable growths of one series, without the atypical ones (cadastral jumps, unit changes): -> (kept, excluded)."""
    kept, excl = [], []
    for y in sorted(points):
        if y - 1 in points and y not in breaks and points[y] is not None and points[y - 1] is not None:
            g = lg(points[y]) - lg(points[y - 1])
            med, mad, n = table.get(y, (None, None, 0))
            if med is not None and n >= 5 and abs(g - med) > MAD_K * mad:
                excl.append(dict(ano=y, crescimento_log1p=g, mediana=med, mad=mad))
            else:
                kept.append(g)
    return kept, excl


# ---------------------------------------------------------------- envelope screen v2 (evidence, family x size, temporal pattern)
# Rule v1 above dropped every transition beyond median +- 5 MAD of ALL companies' growth of the same object and year. v2 never
# treats an extreme growth as an error only because it departs from the national cross-section:
#   1. documented record-level evidence first (auditoria/fase4/RANKING_ANOMALIAS_TEMPORAIS.csv, COD_ID persistence between the two
#      publications): `alteracao_cadastral`, `alteracao_classificacao`, `anomalia_fonte` -> not physical, out of the envelope;
#      `variacao_real_plausivel` (records persist and new ones are added) -> kept, whatever its size (e.g. distributed generation);
#   2. otherwise the reference is the SAME object, SAME year and SAME size class (tercile of the stock at t-1 among the companies
#      with that transition; the whole object when a class has < 5 companies), median +- K MAD (MAD floor in log1p units);
#   3. an atypical transition is classified by what happens next: `persistente` (next step atypical in the same direction: a
#      structural change, kept), `reversao` (next step atypical in the opposite direction: cadastral oscillation, excluded),
#      `degrau_isolado` (next step typical: a one-off level shift; the level is kept in the anchor, the pace is not sustained for
#      five years, excluded from the envelope) and `sem_ano_seguinte` (last observed step: unverifiable; excluded from the central
#      envelope and included in the sensitivity variant `v2_com_nao_verificaveis`).
# Nothing here changes the moderate path. Small bases (< 50 units, fase4 `base_pequena`) are flagged, not excluded.
import csv as _csv
from pathlib import Path as _Path

EVIDENCIA = _Path(__file__).resolve().parents[2] / 'auditoria/fase4/RANKING_ANOMALIAS_TEMPORAIS.csv'
NAO_FISICO = ('alteracao_cadastral', 'alteracao_classificacao', 'anomalia_fonte')


def evidence(path=EVIDENCIA):
    """{(dist, concept, year_to): dict(categoria, grau, causa)} from the fase4 ranking (record-level evidence, read only)."""
    out = {}
    with open(path, encoding='utf-8') as f:
        for r in _csv.DictReader(f):
            out[int(r['dist']), r['ativo'], int(r['ano_para'])] = dict(categoria=r['categoria'], grau=r['grau_confianca'], causa=r['possivel_causa'])
    return out


def _mad(g):
    import statistics
    med = statistics.median(g)
    return med, max(statistics.median([abs(x - med) for x in g]), MAD_FLOOR), len(g)


def screen_table_v2(series, breaks):
    """-> {year: dict(cortes=(t1, t2), classes={0|1|2: (median, mad, n)}, todos=(median, mad, n))} by size tercile of the stock at t-1."""
    by = {}
    for d, pts in series.items():
        for y in sorted(pts):
            if y - 1 in pts and y not in breaks.get(d, ()) and pts[y] is not None and pts[y - 1] is not None:
                by.setdefault(y, []).append((lg(pts[y]) - lg(pts[y - 1]), pts[y - 1]))
    out = {}
    for y, v in by.items():
        s = sorted(x[1] for x in v)
        cuts = (s[len(s) // 3], s[2 * len(s) // 3]) if len(s) >= 3 else (float('inf'), float('inf'))
        cls = {}
        for k in range(3):
            g = [x[0] for x in v if _cls(x[1], cuts) == k]
            if g:
                cls[k] = _mad(g)
        out[y] = dict(cortes=cuts, classes=cls, todos=_mad([x[0] for x in v]))
    return out


def _cls(stock, cuts):
    return 0 if stock < cuts[0] else 1 if stock < cuts[1] else 2


def _ref(table, year, stock, k=MAD_K):
    t = table.get(year)
    if not t:
        return None
    c = _cls(stock, t['cortes']); med, mad, n = t['classes'].get(c, (None, None, 0))
    scope = 'porte_%d' % c
    if n < 5:
        (med, mad, n), scope = t['todos'], 'objeto_inteiro'
    return dict(mediana=med, mad=mad, n=n, referencia=scope, atipica=n >= 5 and med is not None, k=k)


def classify(points, breaks, table, evid=None, k=MAD_K):
    """Every comparable transition of one series with its class and whether it enters the central envelope."""
    tr = [(y, lg(points[y]) - lg(points[y - 1]), points[y - 1]) for y in sorted(points)
          if y - 1 in points and y not in breaks and points[y] is not None and points[y - 1] is not None]
    out = []
    for i, (y, g, s) in enumerate(tr):
        e = (evid or {}).get(y)
        rec = dict(ano=y, crescimento_log1p=g, estoque_anterior=s, evidencia=e['categoria'] if e else None, base_pequena=bool(e and e['categoria'] == 'base_pequena'))
        if e and e['categoria'] in NAO_FISICO:
            rec.update(classe='evidencia_nao_fisica', no_envelope=False, nao_verificavel=False); out.append(rec); continue
        if e and e['categoria'] == 'variacao_real_plausivel':
            rec.update(classe='evidencia_variacao_real', no_envelope=True, nao_verificavel=False); out.append(rec); continue
        r = _ref(table, y, s, k)
        atyp = bool(r and r['atipica'] and abs(g - r['mediana']) > k * r['mad'])
        rec.update(referencia=r and r['referencia'], mediana=r and r['mediana'], mad=r and r['mad'])
        if not atyp:
            rec.update(classe='tipica', no_envelope=True, nao_verificavel=False); out.append(rec); continue
        nxt = tr[i + 1] if i + 1 < len(tr) and tr[i + 1][0] == y + 1 else None
        if nxt is None:
            rec.update(classe='sem_ano_seguinte', no_envelope=False, nao_verificavel=True); out.append(rec); continue
        r2 = _ref(table, nxt[0], nxt[2], k)
        dev, dev2 = g - r['mediana'], (nxt[1] - r2['mediana']) if r2 else 0.0
        atyp2 = bool(r2 and r2['atipica'] and abs(dev2) > k * r2['mad'])
        cls = 'persistente' if atyp2 and dev * dev2 > 0 else 'reversao' if atyp2 else 'degrau_isolado'
        rec.update(classe=cls, no_envelope=cls == 'persistente', nao_verificavel=False); out.append(rec)
    return out


def screened_growth_v2(points, breaks, table, evid=None, incluir_nao_verificaveis=False, k=MAD_K):
    """-> (growths kept in the envelope, every transition with its class)."""
    c = classify(points, breaks, table, evid, k)
    return [x['crescimento_log1p'] for x in c if x['no_envelope'] or (incluir_nao_verificaveis and x['nao_verificavel'])], c


def baseline_path(kind, seg, anchor_year):
    """seg: [(year, value)] contiguous comparable segment ending at the anchor. -> ({year: value}, fallback reason or None)."""
    t1, y1 = seg[-1]
    if kind == 'persistencia' or len(seg) < 2:
        return {y: y1 for y in YEARS}, (None if kind == 'persistencia' else 'short_series')
    t0, y0 = seg[0]
    if kind == 'deriva':
        slope = (y1 - y0) / (t1 - t0)
        path = {y: y1 + (y - anchor_year) * slope for y in YEARS}
        if any(v < 0 for v in path.values()):
            return {y: y1 for y in YEARS}, 'negative_forecast'
        return path, None
    if y0 <= 0 or y1 <= 0:
        return {y: y1 for y in YEARS}, 'nonpositive_endpoint'
    g = (y1 / y0) ** (1 / (t1 - t0))
    return {y: y1 * g ** (y - anchor_year) for y in YEARS}, None


def ml_path(anchor_value, one_step, anchor_year):
    d = lg(one_step) - lg(anchor_value)
    return {y: math.expm1(lg(anchor_value) + (y - anchor_year) * d) for y in YEARS}


def scenarios(anchor_year, anchor_value, moderate, growths):
    """-> ({'Conservador': {year: v}, 'Moderado': ..., 'Agressivo': ...}, meta)."""
    last = max(YEARS)
    g_mod = (lg(moderate[last]) - lg(anchor_value)) / (last - anchor_year)
    lo = min([g_mod] + growths); hi = max([g_mod] + growths)
    out, floored = {}, False
    for name, g in (('Conservador', lo), ('Moderado', g_mod), ('Agressivo', hi)):
        path = {}
        for y in YEARS:
            z = lg(moderate[y]) + (y - anchor_year) * (g - g_mod)
            v = math.expm1(z) if z > 0 else 0.0
            floored |= z <= 0 and moderate[y] > 0
            path[y] = v
        out[name] = path
    for y in YEARS:
        assert out['Conservador'][y] <= out['Moderado'][y] + 1e-9 <= out['Agressivo'][y] + 2e-9, 'scenario order violated'
    meta = dict(crescimento_log1p_moderado=g_mod, crescimento_log1p_conservador=lo, crescimento_log1p_agressivo=hi,
                transicoes_historicas=len(growths), cenarios_degenerados=not growths or (lo == g_mod == hi), piso_zero_aplicado=floored,
                regra='cenario = trajetoria moderada com crescimento anual medio (log1p) deslocado para o menor/maior crescimento anual observado nas transicoes comparaveis 2022-2025 da propria serie que entram no envelope (triagem v2: evidencia fase4, objeto x ano x porte, padrao temporal)')
    return out, meta
