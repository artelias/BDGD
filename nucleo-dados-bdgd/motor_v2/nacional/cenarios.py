"""Projection paths and the three documented scenarios (no future covariate, no confidence interval, no official premise).

Moderate  = the path of the model chosen for projection (experimental when stable, otherwise the fallback baseline):
            persistence  y(T+h) = y(T)
            drift        y(T+h) = y(T) + h * slope of the comparable segment ending at T
            CAGR         y(T+h) = y(T) * g ** h
            ML           y(T+h) = expm1(log1p y(T) + h * d), d = the model's one-step change in log1p, held constant
                         (no future covariates exist, so later steps repeat the first one: a mathematical hypothesis, documented)
Conservative / aggressive = the moderate path with its mean annual log1p growth shifted to the LOWEST / HIGHEST annual log1p
            growth observed in the series' own comparable transitions 2022-2025 whenever that is more extreme than the moderate
            growth (otherwise they coincide with the moderate path). Transitions that are atypical for the object in the national
            cross-section (beyond median +- 5 MAD of all companies' growth in the same year: cadastral jumps, unit changes) are
            left out of this envelope and reported; they never change the moderate path. Ordering cons <= mod <= agr holds by construction. Values are
            floored at zero (physical stock), and a floor is reported."""
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
                regra='cenario = trajetoria moderada com crescimento anual medio (log1p) deslocado para o menor/maior crescimento anual observado nas transicoes comparaveis 2022-2025 da propria serie, sem transicoes atipicas no corte nacional (mediana +- 5 MAD)')
    return out, meta
