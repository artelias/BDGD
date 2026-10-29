"""Future covariates 2026-2030 with explicit provenance. Nothing is invented.

Projection happens in ORIGINAL units (persons, kWh, thousand BRL, km...). Only afterwards is the model transform
(log1p, identity) applied, as declared in the feature registry. Every cell has exactly one provenance:

  official_projection : value from an ingested official source flagged `projected`, in the feature's original unit,
                        published (`available_at`) no later than the forecast origin `as_of`
  scenario_assumption : value from an assumption in configuration that is APPROVED (approved=True with approver/date),
                        in the feature's original unit, scenario-specific (explicit rate or explicit path)
  engine_estimate     : derived by the engine itself (own recursive path) or an explicit static carry-forward

A cell no source can supply is `unavailable` with a reason; it is never filled. Rejected loudly (ValueError): observed
years, a unit that differs from the registry's original unit, an unprojected 'official' value, conflicting sources.
Territorial compatibility: a feature defined for a different territorial unit (e.g. municipal GDP for a conjunto)
is `unavailable` ('territorial_incompatible'), never mapped."""
import math
from .feature_registry import SPECS
from .runner import fingerprint

KINDS = ('official_projection', 'scenario_assumption', 'engine_estimate')
BASE_YEAR = 2025
HORIZON = tuple(range(2026, 2031))
_SPEC = {s.name: s for s in SPECS}


def transform(spec, value):
    """Model-space value from an original-unit value. Applied last."""
    if not math.isfinite(value):
        raise ValueError('non-finite covariate')
    if spec.transform == 'log1p':
        if value <= -1:
            raise ValueError('log1p undefined for values <= -1')
        return math.log1p(value)
    return value


def _check_value(spec, value):
    if not math.isfinite(value) or (spec.nonnegative and value < 0):
        raise ValueError(f'invalid projected value for {spec.name}: {value}')
    return float(value)


def _cell(spec, geo, year, scenario, original, kind, method, source_id, available_at, **extra):
    original = _check_value(spec, original)
    return dict(feature=spec.name, geo=geo, year=year, scenario=scenario, value_original=original, value=transform(spec, original),
                unit=spec.original_unit, transform=spec.transform, kind=kind, method=method, source_id=source_id,
                available_at=available_at, status='available', **extra)


def _gap(spec, geo, year, scenario, reason):
    return dict(feature=spec.name, geo=geo, year=year, scenario=scenario, value_original=None, value=None, unit=spec.original_unit,
                transform=spec.transform, kind=None, method=None, source_id=None, available_at=None, status='unavailable', reason=reason)


def generate(features, geos, last_observed, *, unit_kind='municipality', scenarios=('Moderado',), official=None, assumptions=None,
             engine_paths=None, static_carry=(), years=HORIZON, as_of=None):
    """features: registry names. last_observed: {(feature, geo): (value in ORIGINAL units, year)}.
    official: [{feature, geo, year, value, unit, source_id, projected: True, available_at}].
    assumptions: {feature: {id, unit, approved, approved_by, approved_at, scenarios: {name: {'rate': r} | {'path': {year: v}}}}}.
    engine_paths: {(feature, geo, scenario): {year: value in original units}}.
    static_carry: features whose last observed value may be carried forward as an explicit engine choice.
    as_of: forecast origin date (YYYY-MM-DD); sources made available after it are not usable."""
    if any(y <= BASE_YEAR or y > 2100 for y in years):
        raise ValueError('observed years cannot be generated as future covariates')
    official, assumptions, engine_paths = official or [], assumptions or {}, engine_paths or {}
    off = {}
    for r in official:
        spec = _SPEC[r['feature']]
        if not r.get('projected'):
            raise ValueError('only officially projected values may be used as official future covariates')
        if r.get('unit') != spec.original_unit:
            raise ValueError(f"unit mismatch for {spec.name}: {r.get('unit')!r} != {spec.original_unit!r}")
        off.setdefault((r['feature'], r['geo'], int(r['year'])), r)
    for name, a in assumptions.items():
        if a.get('unit') != _SPEC[name].original_unit:
            raise ValueError(f"assumption unit mismatch for {name}: {a.get('unit')!r} != {_SPEC[name].original_unit!r}")
    out = []
    for feature in features:
        spec = _SPEC[feature]
        for geo in geos:
            for scenario in scenarios:
                for year in years:
                    if unit_kind not in spec.unit_kind:
                        out.append(_gap(spec, geo, year, scenario, 'territorial_incompatible')); continue
                    if spec.status != 'implemented':
                        out.append(_gap(spec, geo, year, scenario, spec.status)); continue
                    sources, blocked = [], []
                    r = off.get((feature, geo, year))
                    if r:
                        if as_of and r.get('available_at') and r['available_at'] > as_of:
                            blocked.append('official_projection_not_available_at_origin')
                        else:
                            sources.append(_cell(spec, geo, year, scenario, float(r['value']), 'official_projection', 'official', r['source_id'], r.get('available_at')))
                    a = assumptions.get(feature, {}).get('scenarios', {}).get(scenario)
                    last = last_observed.get((feature, geo))
                    if a:
                        meta = assumptions[feature]
                        if not meta.get('approved') or not meta.get('approved_by') or not meta.get('approved_at'):
                            blocked.append('assumption_not_approved')
                        elif as_of and meta['approved_at'] > as_of:
                            blocked.append('assumption_approved_after_origin')
                        elif 'path' in a and year in a['path']:
                            sources.append(_cell(spec, geo, year, scenario, a['path'][year], 'scenario_assumption', 'explicit_path', meta['id'], meta['approved_at']))
                        elif 'rate' in a and last:
                            v, y0 = last       # growth acts on the original-unit value; the transform comes afterwards
                            sources.append(_cell(spec, geo, year, scenario, v * (1 + a['rate']) ** (year - y0), 'scenario_assumption',
                                                 'explicit_rate_from_last_observed', meta['id'], meta['approved_at'], rate=a['rate'], base_year=y0))
                    p = engine_paths.get((feature, geo, scenario))
                    if p and year in p:
                        sources.append(_cell(spec, geo, year, scenario, p[year], 'engine_estimate', 'engine_recursive_path', 'engine', as_of))
                    elif feature in static_carry and last and not sources:
                        sources.append(_cell(spec, geo, year, scenario, last[0], 'engine_estimate', 'static_carry_forward', 'engine', as_of, age_years=year - last[1]))
                    if len(sources) > 1:
                        raise ValueError(f'conflicting future sources for {feature}/{geo}/{year}/{scenario}: ' + ','.join(s['kind'] for s in sources))
                    out.append(sources[0] if sources else
                               _gap(spec, geo, year, scenario, blocked[0] if blocked else 'no official projection, approved scenario assumption or engine estimate'))
    return out


def summarize(cells):
    by = {}
    for c in cells:
        k = (c['feature'], c['kind'] or 'unavailable:' + c['reason'])
        by[k] = by.get(k, 0) + 1
    return dict(version=fingerprint(cells)[:16], counts={f'{f}|{k}': n for (f, k), n in sorted(by.items())})
