"""Per-territory trend baselines evaluated on exactly the same test rows and origins as every other candidate.

drift  : y(T+1) = y(T) + (y(T) - y(T0)) / (T - T0)
cagr   : y(T+1) = y(T) * (y(T) / y(T0)) ** (1 / (T - T0))
T is the forecast origin and T0 the first year of the contiguous, comparable segment that ends at T. Only rows usable at
the origin (release/revision gates of the validation mode) enter the segment. A rupture cuts the segment.
Whenever a trend cannot be computed (short or truncated segment, invalid or non-positive endpoint, negative forecast) the
baseline falls back to persistence AND records the reason: fallbacks are counted, never hidden."""
import math
from .temporal import usable

BASELINES = ('persistencia', 'deriva', 'cagr')
DEFAULT_MIN_POINTS = 2   # one observed growth interval; configurable via cfg['baseline_min_points']


def segment(rows, dist, group, origin, mode):
    """Contiguous (year, value) points ending at `origin`, using only information usable at that origin."""
    pts, ruptured = {}, set()
    for r in rows:
        if r['dist'] != dist or r['group'] != group or r['year'] > origin or not usable(r, origin, mode, True):
            continue
        for year, value in ((r['year'] - 1, r['stock']), (r['year'], r['y'])):
            if value is not None and isinstance(value, (int, float)) and math.isfinite(value):
                pts[year] = float(value)
        if r['rupture']:
            ruptured.add(r['year'])     # the step (year-1 -> year) is not comparable
    if origin not in pts:
        return [], 'no_value_at_origin'
    seg, year = [], origin
    while year in pts:
        seg.append((year, pts[year]))
        if year in ruptured:
            break
        year -= 1
    seg.reverse()
    reason = 'rupture_truncated' if (seg and seg[0][0] in ruptured) else None
    return seg, reason


def forecast(kind, seg, last, min_points):
    """-> (value, fallback_reason or None). `last` is the stock at the origin carried on the test row."""
    if len(seg) < min_points:
        return last, 'short_series'
    (t0, y0), (t1, y1) = seg[0], seg[-1]
    if kind == 'deriva':
        value = y1 + (y1 - y0) / (t1 - t0)
    else:
        if y0 <= 0 or y1 <= 0:
            return last, 'nonpositive_endpoint'
        value = y1 * (y1 / y0) ** (1 / (t1 - t0))
    if not math.isfinite(value) or value < 0:
        return last, 'negative_or_nonfinite_forecast'
    return value, None


def predict(kind, rows, test, origin, mode, min_points=DEFAULT_MIN_POINTS):
    """Predictions for the test rows of a fold plus fallback bookkeeping."""
    values, reasons = [], {}
    for r in test:
        if kind == 'persistencia':
            values.append(r['stock']); continue
        seg, cut = segment(rows, r['dist'], r['group'], origin, mode)
        value, why = forecast(kind, seg, r['stock'], min_points)
        why = why or None
        if why == 'short_series' and cut:
            why = cut                  # the short segment is the consequence of a rupture: say so
        values.append(value)
        if why:
            reasons[why] = reasons.get(why, 0) + 1
    return values, dict(baseline=kind, min_points=min_points, fallbacks=reasons, fallback_rows=sum(reasons.values()), rows=len(test))
