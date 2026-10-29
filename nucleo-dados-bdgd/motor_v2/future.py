"""Future covariates 2026-2030 with explicit provenance. Nothing is invented:

  official_projection : value from an ingested official source flagged `projected` (none is integrated today)
  scenario_assumption : value from an assumption supplied in configuration (id, scenario, rate or path)
  engine_estimate     : value derived by the engine itself (recursive own stock path, or an explicit static carry-forward)

A (feature, geo, year, scenario) cell has exactly one provenance; conflicting sources raise. A feature that no
source can supply is returned as `unavailable` with a reason, never filled. Observed years (<= base) are rejected."""
from .runner import fingerprint

KINDS = ('official_projection', 'scenario_assumption', 'engine_estimate')
BASE_YEAR = 2025
HORIZON = tuple(range(2026, 2031))


def _cell(feature, geo, year, scenario, value, kind, method, source_id, **extra):
    if kind not in KINDS:
        raise ValueError('unknown provenance kind')
    return dict(feature=feature, geo=geo, year=year, scenario=scenario, value=value, kind=kind, method=method,
                source_id=source_id, status='available', **extra)


def _gap(feature, geo, year, scenario, reason):
    return dict(feature=feature, geo=geo, year=year, scenario=scenario, value=None, kind=None, method=None, source_id=None,
                status='unavailable', reason=reason)


def generate(features, geos, last_observed, *, scenarios=('Moderado',), official=None, assumptions=None, engine_paths=None,
             static_carry=(), years=HORIZON):
    """features: names to cover. last_observed: {(feature, geo): (value, year)}.
    official: [{feature, geo, year, value, source_id, projected: True}] (only projected rows are accepted).
    assumptions: {feature: {id, scenarios: {name: {'rate': r} | {'path': {year: v}}}}} - explicit, never defaulted.
    engine_paths: {(feature, geo, scenario): {year: value}} derived by the engine (e.g. its own recursive stock path).
    static_carry: features for which carrying the last observed value forward is an explicit engine choice."""
    if any(y <= BASE_YEAR or y > 2100 for y in years):
        raise ValueError('observed years cannot be generated as future covariates')
    official = official or []
    assumptions = assumptions or {}
    engine_paths = engine_paths or {}
    off = {}
    for r in official:
        if not r.get('projected'):
            raise ValueError('only officially projected values may be used as official future covariates')
        off.setdefault((r['feature'], r['geo'], int(r['year'])), r)
    out = []
    for feature in features:
        for geo in geos:
            for scenario in scenarios:
                for year in years:
                    sources = []
                    if (feature, geo, year) in off:
                        r = off[feature, geo, year]
                        sources.append(_cell(feature, geo, year, scenario, float(r['value']), 'official_projection', 'official', r['source_id']))
                    a = assumptions.get(feature, {}).get('scenarios', {}).get(scenario)
                    last = last_observed.get((feature, geo))
                    if a and 'path' in a and year in a['path']:
                        sources.append(_cell(feature, geo, year, scenario, float(a['path'][year]), 'scenario_assumption', 'explicit_path',
                                             assumptions[feature]['id']))
                    elif a and 'rate' in a and last:
                        v, y0 = last
                        sources.append(_cell(feature, geo, year, scenario, float(v) * (1 + a['rate']) ** (year - y0), 'scenario_assumption',
                                             'explicit_rate_from_last_observed', assumptions[feature]['id'], rate=a['rate'], base_year=y0))
                    p = engine_paths.get((feature, geo, scenario))
                    if p and year in p:
                        sources.append(_cell(feature, geo, year, scenario, float(p[year]), 'engine_estimate', 'engine_recursive_path', 'engine'))
                    elif feature in static_carry and last and not sources:
                        sources.append(_cell(feature, geo, year, scenario, float(last[0]), 'engine_estimate', 'static_carry_forward', 'engine',
                                             age_years=year - last[1]))
                    if len(sources) > 1:
                        raise ValueError(f'conflicting future sources for {feature}/{geo}/{year}/{scenario}: '
                                         + ','.join(s['kind'] for s in sources))
                    out.append(sources[0] if sources else _gap(feature, geo, year, scenario, 'no official projection, scenario assumption or engine estimate'))
    return out


def summarize(cells):
    by = {}
    for c in cells:
        k = (c['feature'], c['kind'] or 'unavailable')
        by[k] = by.get(k, 0) + 1
    return dict(version=fingerprint(cells)[:16], counts={f'{f}|{k}': n for (f, k), n in sorted(by.items())})
