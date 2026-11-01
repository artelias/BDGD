"""Physical nature contract applied to Motor V2 internals: asset natures, scenario rounding and the physical error block of the comparison.

The generic contract tests live in test_metric_contract.py, kept byte-identical to PR #19 (the public-product contract) so both PRs share
one implementation and one test file without a merge conflict; this file holds only the Motor V2 side."""
import random
import unittest

from motor_v2 import metric_contract as mc
from motor_v2.assets import ASSETS
from motor_v2.comparison import physical_block, physical_columns, summarise
from motor_v2.runner import scenario_values


def mc_round(x):
    return mc.round_count(x)


def experiment(rows):
    """rows: (key, origin, municipality, actual, pred)"""
    return dict(predictions=[dict(key=k, origin=o, horizon=1, municipality=m, actual=a, pred=p) for k, o, m, a, p in rows], folds=[], failures=[])


class AssetNatures(unittest.TestCase):
    def test_every_asset_has_a_nature_consistent_with_its_unit(self):
        self.assertEqual({a: s['nature'] for a, s in ASSETS.items()},
                         {'ucbt_quantidade': 'discrete_count', 'trafo_dist_quantidade': 'discrete_count',
                          'trafo_dist_potencia_kva': 'continuous_capacity', 'rede_mt_extensao_km': 'continuous_length',
                          'rede_bt_extensao_km': 'continuous_length'})
        for a, s in ASSETS.items():
            self.assertEqual(s['count'], s['nature'] == 'discrete_count')                               # count flag and nature never disagree


class ScenarioRounding(unittest.TestCase):
    def test_rounding_is_monotone_so_scenario_order_survives_single_unit_forecasts(self):
        rng = random.Random(3)
        for _ in range(500):
            base = [rng.random() * 1e5 for _ in range(5)]
            values = scenario_values(base, [-.01, 0., .02])
            for h in range(5):
                phys = [mc.round_count(values[i][h]) for i in range(3)]
                self.assertEqual(phys, sorted(phys))


class ComparisonPhysical(unittest.TestCase):
    ROWS = [('k1', 2023, 'm1', 100., 101.4), ('k2', 2023, 'm2', 200., 198.6), ('k3', 2023, 'm3', 50., 50.5), ('k4', 2024, 'm1', 105., 104.2), ('k5', 2024, 'm2', 205., 206.4)]

    def test_discrete_candidates_get_physical_errors_on_the_same_rows(self):
        ex = {n: experiment(self.ROWS) for n in ('persistencia:individual', 'deriva:individual', 'cagr:individual', 'ridge:individual')}
        s = summarise(ex, 2, 'discrete_count')
        for c in s['candidates']:
            ph = c['physical']
            self.assertEqual(ph['rounding_policy'], 'half_up'); self.assertEqual(ph['independent']['n'], 5)
            self.assertIsNotNone(ph['independent']['continuous']['mae']); self.assertIsNotNone(ph['independent']['physical']['mae'])
            for t in ph['totals']:
                self.assertIs(type(t['physical_total']), int); self.assertIs(type(t['actual_total']), int)
            self.assertEqual(ph['totals'][0]['physical_total'], mc_round(101.4 + 198.6 + 50.5))
        self.assertEqual(s['best_baseline'], 'persistencia:individual')

    def test_selection_uses_the_continuous_error_not_the_rounded_one(self):
        base = [('k1', 2023, 'm1', 10., 10.4), ('k2', 2023, 'm2', 10., 10.4), ('k3', 2024, 'm1', 10., 10.4), ('k4', 2024, 'm2', 10., 10.4)]
        a = [(k, o, m, ac, 10.45) for k, o, m, ac, _ in base]             # worse continuously, identical once rounded
        ex = {'persistencia:individual': experiment(base), 'deriva:individual': experiment(base), 'cagr:individual': experiment(base), 'ridge:individual': experiment(a)}
        s = summarise(ex, 2, 'discrete_count')
        cands = {c['candidate']: c for c in s['candidates']}
        self.assertLess(cands['persistencia:individual']['robust_score'], cands['ridge:individual']['robust_score'])
        self.assertEqual(cands['ridge:individual']['physical']['independent']['physical']['mae'], cands['persistencia:individual']['physical']['independent']['physical']['mae'])

    def test_continuous_assets_have_no_physical_block_and_keep_decimals(self):
        ex = {n: experiment(self.ROWS) for n in ('persistencia:individual', 'deriva:individual', 'cagr:individual', 'ridge:individual')}
        for nature in (None, 'continuous_length', 'continuous_capacity'):
            s = summarise(ex, 2, nature)
            self.assertTrue(all(c['physical'] is None for c in s['candidates']))
            self.assertEqual(physical_columns(s['candidates'][0]), {})

    def test_physical_columns_for_the_matrix(self):
        s = summarise({n: experiment(self.ROWS) for n in ('persistencia:individual', 'deriva:individual', 'cagr:individual')}, 2, 'discrete_count')
        cols = physical_columns(s['candidates'][0])
        self.assertEqual(set(cols), {'physical_mae', 'physical_rmse', 'physical_bias', 'physical_wape', 'reconciled_physical_mae', 'reconciled_physical_wape', 'rounding_policy'})

    def test_reconciled_allocation_sums_to_the_integer_total_per_origin(self):
        ph = physical_block(experiment(self.ROWS)['predictions'], 'discrete_count', 'half_up')
        for t in ph['totals']:
            self.assertEqual(t['physical_total'], mc_round(t['raw_total']))
        self.assertGreaterEqual(min(t['moved_by_reconciliation'] for t in ph['totals']), 0)


if __name__ == '__main__':
    unittest.main()
