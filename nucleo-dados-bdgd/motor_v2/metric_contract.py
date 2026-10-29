"""Physical nature contract for forecast metrics (standard library only, shared by every producer of public numbers).

Natures
  discrete_count      customers, UCs, transformers, poles, devices and any indivisible quantity
  continuous_length   km, m
  continuous_capacity kVA, MVA, MW, kW
  continuous_energy   kWh, MWh
  ratio               indices, percentages, rates, fractions

For `discrete_count` a forecast has two representations:
  raw_prediction       the model output, a real number, kept INTERNALLY for diagnostics only
  physical_prediction  a non-negative INTEGER under a declared rounding policy; the only form a public CSV, JSON or chart may show
Continuous natures keep their decimal value in both fields.

Rounding policy (never Python's round(), which is half-to-even and hides the choice): default `half_up`, computed on the exact
binary value of the float (decimal.Decimal), so 2.5 -> 3, 0.49999999999999994 -> 0, 1e15 + 0.5 is exact. Other declared
policies: `half_even`, `floor`, `ceil`. A negative or non-finite raw prediction is REJECTED (ValueError), never clipped silently.

Territorial reconciliation: integer shares of a distributor total use the largest-remainder (Hamilton) method with a
deterministic tie-break (larger fractional part first, then unit key ascending), so the integer parts always sum to the integer
total. Scenario families are allocated 'nested' (lowest scenario first, each later scenario never below the previous one for any
unit), which preserves the physical ordering Conservador <= Moderado <= Agressivo unit by unit."""
import math
from fractions import Fraction
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN, ROUND_HALF_UP

NATURES = ('discrete_count', 'continuous_length', 'continuous_capacity', 'continuous_energy', 'ratio')
POLICIES = {'half_up': ROUND_HALF_UP, 'half_even': ROUND_HALF_EVEN, 'floor': ROUND_FLOOR, 'ceil': ROUND_CEILING}
DEFAULT_POLICY = 'half_up'
SCENARIO_ORDER = ('Conservador', 'Moderado', 'Agressivo')

# Unit -> nature. An unknown unit is an error: a new unit must be classified explicitly (consistency of units).
_UNIT_NATURE = {}
for _nature, _units in {
    'discrete_count': ('clientes', 'customers', 'uc', 'ucs', 'itens', 'items', 'unidades', 'units', 'quantidade'),
    'continuous_length': ('km', 'm', 'metros'),
    'continuous_capacity': ('kva', 'mva', 'mw', 'kw', 'w'),
    'continuous_energy': ('kwh', 'mwh', 'gwh', 'twh'),
    'ratio': ('%', 'percent', 'pct', 'fraction', 'ratio', 'indice', 'taxa'),
}.items():
    for _u in _units:
        _UNIT_NATURE[_u] = _nature
# Unit prefix scale to the base unit (for consistency checks between a unit and a declared conversion).
_SCALE = {'km': 1000., 'm': 1., 'kva': 1e3, 'mva': 1e6, 'kw': 1e3, 'mw': 1e6, 'w': 1., 'kwh': 1e3, 'mwh': 1e6, 'gwh': 1e9, 'twh': 1e12}


def nature_of(unit):
    """Nature from a unit string; case-insensitive. Raises on an unclassified unit."""
    key = str(unit).strip().lower()
    if key not in _UNIT_NATURE:
        raise ValueError(f'unit {unit!r} has no declared physical nature')
    return _UNIT_NATURE[key]


def check_nature(nature):
    if nature not in NATURES:
        raise ValueError(f'unknown physical nature {nature!r}')
    return nature


# Apparent (kVA, MVA) and active (kW, MW) power are different physical quantities: S = P / pf. They are NEVER interchangeable by
# the prefix scale alone; a conversion across them needs an explicit power-factor hypothesis supplied by the caller.
_POWER_KIND = {'kva': 'apparent', 'mva': 'apparent', 'kw': 'active', 'mw': 'active', 'w': 'active'}


def power_kind(unit):
    """'apparent' (kVA, MVA), 'active' (W, kW, MW) or None for non-power units."""
    return _POWER_KIND.get(str(unit).strip().lower())


def convert(value, from_unit, to_unit, power_factor=None):
    """Unit conversion inside one nature (e.g. MVA -> kVA, m -> km, MWh -> kWh). Refused: different natures, counts and ratios,
    and apparent <-> active power without an explicit `power_factor` in (0, 1] (kW = kVA * pf; kVA = kW / pf). A power factor given
    for a conversion that does not cross apparent/active power is also refused, so a hypothesis is never applied silently."""
    a, b = nature_of(from_unit), nature_of(to_unit)
    if a != b or a in ('discrete_count', 'ratio'):
        raise ValueError(f'cannot convert {from_unit!r} to {to_unit!r}')
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('value to convert must be a finite number')
    f, t = str(from_unit).strip().lower(), str(to_unit).strip().lower()
    scaled = value * _SCALE[f] / _SCALE[t]
    kf, kt = power_kind(f), power_kind(t)
    if a != 'continuous_capacity':
        if power_factor is not None:
            raise ValueError('a power factor only applies to apparent <-> active power conversions')
        return scaled
    if kf is None or kt is None:
        raise ValueError(f'unclassified power unit in {from_unit!r} -> {to_unit!r}')
    if kf == kt:
        if power_factor is not None:
            raise ValueError('a power factor only applies to apparent <-> active power conversions')
        return scaled
    if power_factor is None:
        raise ValueError(f'{from_unit} ({kf} power) and {to_unit} ({kt} power) are not interchangeable without an explicit power factor')
    if isinstance(power_factor, bool) or not isinstance(power_factor, (int, float)) or not math.isfinite(power_factor) or not 0 < power_factor <= 1:
        raise ValueError('power factor must be a finite number in (0, 1]')
    return scaled * power_factor if kf == 'apparent' else scaled / power_factor


def round_count(raw, policy=DEFAULT_POLICY):
    """Non-negative integer from a raw real prediction under a declared policy. Ties follow the policy, not Python's round()."""
    if policy not in POLICIES:
        raise ValueError(f'unknown rounding policy {policy!r}')
    if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not math.isfinite(raw):
        raise ValueError('raw prediction must be a finite number')
    if raw < 0:
        raise ValueError('negative raw prediction rejected (not clipped)')
    return int(Decimal(raw).to_integral_value(rounding=POLICIES[policy]))


def physical_prediction(raw, nature, policy=DEFAULT_POLICY):
    """int for discrete_count, the unchanged non-negative float otherwise."""
    check_nature(nature)
    if nature == 'discrete_count':
        return round_count(raw, policy)
    if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not math.isfinite(raw) or raw < 0:
        raise ValueError('continuous prediction must be finite and non-negative')
    return float(raw)


def prediction_pair(raw, nature, policy=DEFAULT_POLICY):
    return dict(raw_prediction=float(raw), physical_prediction=physical_prediction(raw, nature, policy), rounding=policy if nature == 'discrete_count' else None)


def _hamilton(exact, total):
    """Largest remainder on exact Fractions that sum to `total`: floors, then +1 for the largest fractional parts (key ascending on ties)."""
    base = {k: v.numerator // v.denominator for k, v in exact.items()}
    rem = total - sum(base.values())
    if not 0 <= rem <= len(exact):
        raise ValueError('inconsistent allocation total')
    for k in sorted(exact, key=lambda k: (-(exact[k] - base[k]), str(k)))[:rem]:
        base[k] += 1
    return base


def allocate(raw, total=None, policy=DEFAULT_POLICY):
    """Integer parts of `raw` ({unit: real >= 0}) that sum to `total` (default: round_count(sum(raw))), by largest remainder.
    Shares are proportional to the raw values (exact rational arithmetic), so any integer total is reachable, not only totals
    within one unit per territory. Deterministic: ties on the fractional part are broken by unit key ascending."""
    for k, v in raw.items():
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
            raise ValueError(f'invalid raw prediction for {k!r}')
    total = round_count(sum(raw.values()), policy) if total is None else total
    if not isinstance(total, int) or isinstance(total, bool) or total < 0:
        raise ValueError('total must be a non-negative integer')
    s = sum(Fraction(v) for v in raw.values())
    if s == 0:
        if total:
            raise ValueError('cannot allocate a positive total over zero raw predictions')
        return {k: 0 for k in raw}
    return _hamilton({k: Fraction(v) * total / s for k, v in raw.items()}, total)


def allocate_nested(raw_by_scenario, total_by_scenario=None, order=SCENARIO_ORDER, policy=DEFAULT_POLICY):
    """Allocate a family of scenarios so that, unit by unit, each later scenario is >= the previous one and every scenario's
    integer parts sum to its own integer total (default: rounding of its raw sum). The totals must be non-decreasing along `order`.
    The increment between two scenarios is shared out in proportion to how far each unit's raw value is above the previous
    allocation (units already above their raw value get nothing, except through the remainder), by largest remainder."""
    names = [s for s in order if s in raw_by_scenario]
    if set(names) != set(raw_by_scenario):
        raise ValueError('scenario names must belong to the declared order')
    units, out, previous, prev_total = None, {}, None, -1
    for s in names:
        raw = raw_by_scenario[s]
        if units is None:
            units = set(raw)
        elif set(raw) != units:
            raise ValueError('scenarios must cover the same units')
        total = (total_by_scenario or {}).get(s)
        total = round_count(sum(raw.values()), policy) if total is None else total
        if total < prev_total:
            raise ValueError(f'scenario totals are not ordered: {s}')
        if previous is None:
            alloc = allocate(raw, total, policy)
        else:
            extra = total - sum(previous.values())
            weights = {k: max(Fraction(raw[k]) - previous[k], Fraction(0)) for k in raw}
            sw = sum(weights.values())
            if sw == 0:                                   # nothing is above its previous value: fall back to the raw shape
                weights = {k: Fraction(raw[k]) for k in raw}; sw = sum(weights.values())
            if extra and sw == 0:
                raise ValueError('cannot allocate an increment over zero weights')
            inc = _hamilton({k: (weights[k] * extra / sw if sw else Fraction(0)) for k in raw}, extra)
            alloc = {k: previous[k] + inc[k] for k in raw}
        out[s] = alloc
        previous, prev_total = alloc, total
    return out


def reconcile(raw_by_unit, total_raw=None, policy=DEFAULT_POLICY):
    """Territorial physical predictions + distributor total. With `total_raw` (a model of the distributor itself) the integer total is
    its rounding; otherwise the bottom-up sum. -> dict(total, by_unit, independent) where `independent` is plain per-unit rounding
    (kept to measure how much the reconciliation moves things)."""
    total = round_count(sum(raw_by_unit.values()) if total_raw is None else total_raw, policy)
    return dict(total=total, by_unit=allocate(raw_by_unit, total, policy), independent={k: round_count(v, policy) for k, v in raw_by_unit.items()})


def error_pair(actual, raw, physical):
    """MAE/RMSE/bias/WAPE of the continuous (raw) and the physical (publishable) predictions against the same actuals.
    The continuous error is reported next to, never instead of, the publishable one."""
    n = len(actual)
    if n == 0 or n != len(raw) or n != len(physical):
        raise ValueError('actual, raw and physical must be non-empty and of equal length')

    def score(pred):
        e = [p - a for p, a in zip(pred, actual)]
        den = sum(abs(a) for a in actual)
        return dict(mae=sum(abs(x) for x in e) / n, rmse=math.sqrt(sum(x * x for x in e) / n), bias=sum(e) / n,
                    wape=sum(abs(x) for x in e) / den if den else None)
    return dict(continuous=score(raw), physical=score(physical), n=n)


def is_integral(value):
    return isinstance(value, int) and not isinstance(value, bool) or (isinstance(value, float) and math.isfinite(value) and value == int(value))


def assert_publishable(value, nature, where='', signed=False):
    """Raise unless `value` may appear in a public artifact: a discrete count must be an integer >= 0 (an integer of any sign when
    `signed`, e.g. a residual); continuous values must be finite and >= 0 unless signed."""
    check_nature(nature)
    if value is None:
        return value
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or (value < 0 and not signed):
        raise ValueError(f'non-publishable value {value!r} {where}')
    if nature == 'discrete_count' and not is_integral(value):
        raise ValueError(f'fractional count {value!r} in a public artifact {where}')
    return value


def assert_public_table(rows, nature_by_column):
    """Gate for a public CSV/JSON table: every cell of a discrete column must be an integer (None allowed = N/D)."""
    for i, row in enumerate(rows):
        for col, nature in nature_by_column.items():
            if col in row and row[col] != '':          # '' is an N/D cell of a CSV: never a number, never zero
                signed = nature.endswith(':signed')
                assert_publishable(row[col], nature.split(':')[0], f'(row {i}, column {col})', signed)
    return rows


def write_public_csv(path, rows, nature_by_column, fields=None):
    """The only writer for public CSVs: validates every discrete column first (a fractional count aborts before any byte is written)."""
    import csv
    import os
    assert_public_table(rows, nature_by_column)
    fields = fields or list(dict.fromkeys(k for r in rows for k in r))
    tmp = str(path) + '.tmp'
    with open(tmp, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fields)
        w.writeheader(); w.writerows(rows)
    os.replace(tmp, path)
