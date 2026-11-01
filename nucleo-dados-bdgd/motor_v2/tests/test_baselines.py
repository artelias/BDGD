"""Drift and CAGR baselines: same test rows, short series, ruptures, invalid values, fallbacks and gain accounting."""
import unittest

from motor_v2.baselines import forecast, predict, segment
from motor_v2.comparison import summarise


def series(group, values, start=2022, dist=26, rupture_years=()):
    """Panel rows for one territory from consecutive yearly values: row(year) has stock=value(year-1), y=value(year)."""
    rows = []
    for i in range(1, len(values)):
        y = start + i
        rows.append(dict(dist=dist, year=y, group=group, feature_year=y-1, feature_available=f'{y-1}-12-31',
                         feature_revision_available=f'{y-1}-12-31', target_available=f'{y}-12-31',
                         x=[1.], stock=values[i-1], y=values[i], rupture=y in rupture_years, key=f'{dist}:{y}:{group}'))
    return rows


def test_row(group, stock, year=2024, dist=26):
    return dict(dist=dist, year=year, group=group, stock=stock, rupture=False)


class Segments(unittest.TestCase):
    def test_segment_is_contiguous_and_ends_at_the_origin(self):
        rows = series('a', [10., 12., 14.])                    # years 2022..2024
        seg, why = segment(rows, 26, 'a', 2024, 'reconciled_retrospective')
        self.assertEqual(seg, [(2022, 10.), (2023, 12.), (2024, 14.)]); self.assertIsNone(why)

    def test_origin_excludes_later_years(self):
        rows = series('a', [10., 12., 14., 99.])
        seg, _ = segment(rows, 26, 'a', 2024, 'reconciled_retrospective')
        self.assertEqual(seg[-1], (2024, 14.))

    def test_rupture_cuts_the_segment(self):
        rows = series('a', [10., 12., 40., 42.], rupture_years=(2024,))   # step 2023->2024 is not comparable
        seg, why = segment(rows, 26, 'a', 2025, 'reconciled_retrospective')
        self.assertEqual(seg, [(2024, 40.), (2025, 42.)]); self.assertEqual(why, 'rupture_truncated')

    def test_point_in_time_uses_only_rows_released_before_the_origin(self):
        rows = series('a', [10., 12., 14.])
        rows[-1]['target_available'] = '2025-06-01'                # the 2024 value was published after the 2024 origin
        seg, why = segment(rows, 26, 'a', 2024, 'point_in_time')
        self.assertEqual(seg, []); self.assertEqual(why, 'no_value_at_origin')
        seg, _ = segment(rows, 26, 'a', 2024, 'reconciled_retrospective')   # the reconciled mode may use the later revision
        self.assertEqual(seg[-1], (2024, 14.))


class Formulas(unittest.TestCase):
    def test_drift_and_cagr_values(self):
        seg = [(2022, 100.), (2023, 110.), (2024, 121.)]
        self.assertAlmostEqual(forecast('deriva', seg, 121., 2)[0], 121 + 10.5)
        self.assertAlmostEqual(forecast('cagr', seg, 121., 2)[0], 121 * 1.1)

    def test_short_series_falls_back_to_persistence_with_a_reason(self):
        self.assertEqual(forecast('deriva', [(2024, 5.)], 5., 2), (5., 'short_series'))
        self.assertEqual(forecast('cagr', [(2023, 4.), (2024, 5.)], 5., 3), (5., 'short_series'))

    def test_cagr_needs_positive_endpoints_and_drift_never_goes_negative(self):
        self.assertEqual(forecast('cagr', [(2023, 0.), (2024, 5.)], 5., 2), (5., 'nonpositive_endpoint'))
        self.assertEqual(forecast('deriva', [(2023, 10.), (2024, 2.)], 2., 2), (2., 'negative_or_nonfinite_forecast'))

    def test_predict_counts_fallbacks_and_leaves_persistence_untouched(self):
        rows = series('a', [10., 12., 14.]) + series('b', [5., 5., 5.])[:0]
        vals, info = predict('deriva', rows, [test_row('a', 14.), test_row('zzz', 7.)], 2024, 'reconciled_retrospective')
        self.assertEqual(vals, [16., 7.]); self.assertEqual(info['fallbacks'], {'no_value_at_origin': 1})
        self.assertEqual(predict('persistencia', rows, [test_row('a', 14.)], 2024, 'reconciled_retrospective')[0], [14.])


def exp(pairs, origin_by=None):
    """Experiment dict from (key, actual, pred) tuples over origins 2023 and 2024."""
    return dict(predictions=[dict(key=k, origin=2023 if i % 2 == 0 else 2024, horizon=1, municipality=k, actual=a, pred=p)
                             for i, (k, a, p) in enumerate(pairs)], folds=[], failures=[])


class Accounting(unittest.TestCase):
    def test_ml_must_beat_the_best_baseline_not_only_persistence(self):
        actual = [100., 200., 300., 400.]
        mk = lambda preds: exp([(f'k{i}', a, p) for i, (a, p) in enumerate(zip(actual, preds))])
        ex = {'persistencia:individual': mk([90., 180., 270., 360.]),         # biased low
              'deriva:individual': mk([99., 199., 299., 399.]),               # excellent trend baseline
              'cagr:individual': mk([97., 190., 290., 390.]),
              'ridge:individual': mk([98., 198., 298., 398.])}                # beats persistence, loses to drift
        s = summarise(ex, minimum_origins=2)
        self.assertEqual(s['best_baseline'], 'deriva:individual'); self.assertEqual(s['best_ml'], 'ridge:individual')
        self.assertFalse(s['ml_beats_best_baseline']); self.assertGreater(s['ml_gain_vs_persistence'], .5)
        self.assertLess(s['ml_gain_vs_best_baseline'], 0)
        self.assertNotEqual(s['winner'], 'ridge:individual')
        self.assertEqual(s['selection_reason'], '>=5% robust gain of a trend baseline over persistence')

    def test_ml_gain_over_all_baselines_is_reported_but_needs_enough_origins(self):
        actual = [100., 200., 300., 400.]
        mk = lambda preds: exp([(f'k{i}', a, p) for i, (a, p) in enumerate(zip(actual, preds))])
        ex = {'persistencia:individual': mk([90., 180., 270., 360.]), 'deriva:individual': mk([95., 190., 285., 380.]),
              'cagr:individual': mk([95., 190., 285., 380.]), 'ridge:individual': mk([100., 200., 300., 400.])}
        few = summarise(ex, minimum_origins=3)                                  # only 2 origins
        self.assertTrue(few['ml_beats_best_baseline']); self.assertFalse(few['validated_winner']); self.assertEqual(few['winner'], 'persistencia:individual')
        enough = summarise(ex, minimum_origins=2)
        self.assertEqual(enough['winner'], 'ridge:individual'); self.assertTrue(enough['validated_winner'])

    def test_candidates_on_other_test_rows_are_not_comparable(self):
        base = exp([('k0', 100., 90.), ('k1', 200., 190.)])
        other = exp([('k0', 100., 100.)])
        s = summarise({'persistencia:individual': base, 'deriva:individual': base, 'cagr:individual': base, 'ridge:individual': other}, 2)
        self.assertFalse(next(c for c in s['candidates'] if c['candidate'] == 'ridge:individual')['common_test_set'])
        self.assertIsNone(s['best_ml'])


if __name__ == '__main__':
    unittest.main()
