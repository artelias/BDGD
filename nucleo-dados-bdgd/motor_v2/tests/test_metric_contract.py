"""Physical nature contract: rounding, bounds, negatives, sums, scenario stability and unit consistency."""
import itertools
import json
import math
import random
import tempfile
import unittest
from pathlib import Path

from motor_v2 import metric_contract as mc
from motor_v2.assets import ASSETS
from motor_v2.comparison import physical_block, physical_columns, summarise
from motor_v2.runner import scenario_values


class Rounding(unittest.TestCase):
    def test_ties_follow_the_declared_policy_not_python_round(self):
        self.assertEqual([mc.round_count(x) for x in (0.5, 1.5, 2.5, 3.5)], [1, 2, 3, 4])               # half_up
        self.assertEqual([mc.round_count(x, 'half_even') for x in (0.5, 1.5, 2.5, 3.5)], [0, 2, 2, 4])
        self.assertEqual(round(2.5), 2)                                                                  # the implicit Python behaviour we avoid
        self.assertEqual((mc.round_count(2.4, 'ceil'), mc.round_count(2.6, 'floor')), (3, 2))

    def test_exact_binary_value_decides_near_ties(self):
        self.assertEqual(mc.round_count(0.49999999999999994), 0)                                         # naive floor(x+0.5) gives 1
        self.assertEqual(mc.round_count(2.4999999999999996), 2)
        self.assertEqual(mc.round_count(1e15 + 0.5), 10 ** 15 + 1)
        self.assertEqual(mc.round_count(0.0), 0); self.assertEqual(mc.round_count(7), 7)

    def test_result_is_a_python_int_and_non_negative(self):
        for x in (0, 0.2, 3.7, 12345.678):
            r = mc.round_count(x)
            self.assertIs(type(r), int); self.assertGreaterEqual(r, 0)

    def test_negative_nonfinite_and_non_numeric_are_rejected_never_clipped(self):
        for bad in (-0.1, -5, float('nan'), float('inf'), float('-inf'), None, '3', True):
            with self.assertRaises(ValueError):
                mc.round_count(bad)
        with self.assertRaises(ValueError):
            mc.physical_prediction(-1., 'continuous_length')
        with self.assertRaises(ValueError):
            mc.round_count(1., 'bankers')

    def test_minus_zero_is_zero(self):
        self.assertEqual(mc.round_count(-0.0), 0)


class Natures(unittest.TestCase):
    def test_units_map_to_natures_and_unknown_units_fail(self):
        cases = {'clientes': 'discrete_count', 'itens': 'discrete_count', 'km': 'continuous_length', 'm': 'continuous_length', 'kVA': 'continuous_capacity',
                 'MVA': 'continuous_capacity', 'MW': 'continuous_capacity', 'kWh': 'continuous_energy', 'MWh': 'continuous_energy', '%': 'ratio'}
        for unit, nature in cases.items():
            self.assertEqual(mc.nature_of(unit), nature)
        with self.assertRaises(ValueError):
            mc.nature_of('furlongs')

    def test_every_asset_has_a_nature_consistent_with_its_unit(self):
        self.assertEqual({a: s['nature'] for a, s in ASSETS.items()},
                         {'ucbt_quantidade': 'discrete_count', 'trafo_dist_quantidade': 'discrete_count',
                          'trafo_dist_potencia_kva': 'continuous_capacity', 'rede_mt_extensao_km': 'continuous_length',
                          'rede_bt_extensao_km': 'continuous_length'})
        for a, s in ASSETS.items():
            self.assertEqual(s['count'], s['nature'] == 'discrete_count')                               # count flag and nature never disagree

    def test_continuous_natures_keep_their_decimals(self):
        for nature, v in (('continuous_length', 20705.206181), ('continuous_capacity', 745664.5), ('continuous_energy', 12.345678), ('ratio', 0.123456)):
            self.assertEqual(mc.physical_prediction(v, nature), v)
            self.assertIsNone(mc.prediction_pair(v, nature)['rounding'])
        p = mc.prediction_pair(2.5, 'discrete_count')
        self.assertEqual((p['raw_prediction'], p['physical_prediction'], p['rounding']), (2.5, 3, 'half_up'))

    def test_valid_conversions_inside_one_kind_need_no_hypothesis(self):
        self.assertEqual(mc.convert(1.5, 'MVA', 'kVA'), 1500.)
        self.assertEqual(mc.convert(2500., 'kW', 'MW'), 2.5)
        self.assertEqual(mc.convert(3.2, 'MWh', 'kWh'), 3200.)
        self.assertEqual(mc.convert(2500., 'm', 'km'), 2.5)
        self.assertEqual(mc.convert(1000., 'W', 'kW'), 1.)
        self.assertEqual(mc.convert(7., 'kVA', 'kVA'), 7.)

    def test_apparent_and_active_power_are_not_interchangeable_without_an_explicit_power_factor(self):
        for a, b in (('kVA', 'kW'), ('MVA', 'MW'), ('kW', 'kVA'), ('MW', 'MVA'), ('kVA', 'MW'), ('W', 'kVA')):
            with self.assertRaisesRegex(ValueError, 'power factor'):
                mc.convert(100., a, b)
        self.assertEqual((mc.power_kind('kVA'), mc.power_kind('MVA'), mc.power_kind('kW'), mc.power_kind('MW'), mc.power_kind('km')),
                         ('apparent', 'apparent', 'active', 'active', None))

    def test_explicit_power_factor_converts_across_kinds_and_round_trips(self):
        self.assertAlmostEqual(mc.convert(1000., 'kVA', 'kW', power_factor=.92), 920.)
        self.assertAlmostEqual(mc.convert(1., 'MVA', 'kW', power_factor=.9), 900.)
        self.assertAlmostEqual(mc.convert(920., 'kW', 'kVA', power_factor=.92), 1000.)
        self.assertAlmostEqual(mc.convert(mc.convert(750., 'kVA', 'MW', power_factor=.85), 'MW', 'kVA', power_factor=.85), 750.)

    def test_invalid_power_factors_and_misplaced_hypotheses_are_refused(self):
        for pf in (0, -.5, 1.01, float('nan'), float('inf'), True, '0.9'):
            with self.assertRaises(ValueError):
                mc.convert(100., 'kVA', 'kW', power_factor=pf)
        with self.assertRaises(ValueError):
            mc.convert(100., 'kVA', 'MVA', power_factor=.9)            # same kind: a hypothesis would be applied silently
        with self.assertRaises(ValueError):
            mc.convert(100., 'km', 'm', power_factor=.9)
        for bad in (float('nan'), True, None, '5'):
            with self.assertRaises(ValueError):
                mc.convert(bad, 'kVA', 'MVA')

    def test_unit_conversion_stays_inside_one_nature_and_refuses_counts(self):
        self.assertEqual(mc.convert(1.5, 'MVA', 'kVA'), 1500.)
        self.assertEqual(mc.convert(2500., 'm', 'km'), 2.5)
        for a, b in (('km', 'kVA'), ('clientes', 'itens'), ('%', '%')):
            with self.assertRaises(ValueError):
                mc.convert(1., a, b)
        with self.assertRaises(ValueError):
            mc.physical_prediction(1., 'weight')


class Allocation(unittest.TestCase):
    def test_parts_always_sum_to_the_integer_total_property(self):
        rng = random.Random(11)
        for _ in range(300):
            raw = {f'u{i}': rng.random() * 50 for i in range(rng.randint(1, 40))}
            a = mc.allocate(raw)
            self.assertEqual(sum(a.values()), mc.round_count(sum(raw.values())))
            self.assertTrue(all(isinstance(v, int) and v >= 0 for v in a.values()))
            self.assertTrue(all(abs(v - raw[k]) <= 1.0001 + abs(sum(raw.values()) - sum(a.values())) for k, v in a.items()))

    def test_explicit_totals_far_from_the_sum_are_reachable_and_exact(self):
        a = mc.allocate({'a': 10., 'b': 30., 'c': 60.}, 1000)
        self.assertEqual((sum(a.values()), a), (1000, {'a': 100, 'b': 300, 'c': 600}))
        self.assertEqual(sum(mc.allocate({'a': 1.1, 'b': 2.2}, 0).values()), 0)
        with self.assertRaises(ValueError):
            mc.allocate({'a': 0., 'b': 0.}, 5)
        self.assertEqual(mc.allocate({'a': 0., 'b': 0.}, 0), {'a': 0, 'b': 0})
        with self.assertRaises(ValueError):
            mc.allocate({'a': 1.}, -1)

    def test_ties_break_by_unit_key_and_input_order_does_not_matter(self):
        raw = {'b': 1.5, 'a': 1.5, 'c': 1.0}                                                             # total 4: the extra unit goes to 'a'
        base = mc.allocate(raw)
        self.assertEqual((base, sum(base.values())), ({'a': 2, 'b': 1, 'c': 1}, 4))
        for perm in itertools.permutations(raw.items()):
            self.assertEqual(mc.allocate(dict(perm)), base)

    def test_reconcile_reports_the_move_against_independent_rounding(self):
        r = mc.reconcile({'a': 1.4, 'b': 1.4, 'c': 1.4, 'd': 1.4, 'e': 1.4})                              # independent rounding gives 5; sum 7.0 -> 7
        self.assertEqual(r['total'], 7); self.assertEqual(sum(r['by_unit'].values()), 7); self.assertEqual(sum(r['independent'].values()), 5)
        top = mc.reconcile({'a': 3.2, 'b': 4.1}, total_raw=7.6)                                           # model of the distributor itself
        self.assertEqual((top['total'], sum(top['by_unit'].values())), (8, 8))

    def test_negative_raw_blocks_allocation(self):
        with self.assertRaises(ValueError):
            mc.allocate({'a': -1., 'b': 3.})


class ScenarioStability(unittest.TestCase):
    def test_nested_allocation_orders_every_unit_and_sums_every_scenario(self):
        rng = random.Random(5)
        for _ in range(200):
            units = [f'u{i}' for i in range(rng.randint(1, 30))]
            base = {u: rng.random() * 100 for u in units}
            raw = {'Conservador': base, 'Moderado': {u: v * (1 + rng.random() * .1) for u, v in base.items()}}
            raw['Agressivo'] = {u: v * (1 + rng.random() * .2) for u, v in raw['Moderado'].items()}
            out = mc.allocate_nested(raw)
            for s, parts in out.items():
                self.assertEqual(sum(parts.values()), mc.round_count(sum(raw[s].values())))
            for u in units:
                self.assertLessEqual(out['Conservador'][u], out['Moderado'][u]); self.assertLessEqual(out['Moderado'][u], out['Agressivo'][u])

    def test_unit_whose_raw_order_is_reversed_never_breaks_the_physical_order(self):
        raw = {'Conservador': {'a': 10., 'b': 10.}, 'Moderado': {'a': 9.6, 'b': 12.4}, 'Agressivo': {'a': 9.6, 'b': 14.4}}   # a is lower in later scenarios
        out = mc.allocate_nested(raw)
        for u in 'ab':
            self.assertTrue(out['Conservador'][u] <= out['Moderado'][u] <= out['Agressivo'][u])
        self.assertEqual([sum(v.values()) for v in out.values()], [20, 22, 24])

    def test_totals_must_be_ordered_and_scenarios_must_share_units(self):
        with self.assertRaises(ValueError):
            mc.allocate_nested({'Conservador': {'a': 5.}, 'Moderado': {'a': 3.}})
        with self.assertRaises(ValueError):
            mc.allocate_nested({'Conservador': {'a': 5.}, 'Moderado': {'b': 6.}})
        with self.assertRaises(ValueError):
            mc.allocate_nested({'Pessimista': {'a': 5.}})

    def test_rounding_is_monotone_so_scenario_order_survives_single_unit_forecasts(self):
        rng = random.Random(3)
        for _ in range(500):
            base = [rng.random() * 1e5 for _ in range(5)]
            values = scenario_values(base, [-.01, 0., .02])
            for h in range(5):
                phys = [mc.round_count(values[i][h]) for i in range(3)]
                self.assertEqual(phys, sorted(phys))


class ErrorsAndPublication(unittest.TestCase):
    def test_continuous_and_physical_errors_are_both_reported(self):
        actual = [10, 20, 30]; raw = [10.4, 19.6, 30.5]; phys = [10, 20, 31]
        e = mc.error_pair(actual, raw, phys)
        self.assertAlmostEqual(e['continuous']['mae'], (.4 + .4 + .5) / 3); self.assertAlmostEqual(e['physical']['mae'], 1 / 3)
        self.assertEqual(e['n'], 3)
        with self.assertRaises(ValueError):
            mc.error_pair([], [], [])

    def test_assert_publishable_rejects_fractional_counts_only(self):
        mc.assert_publishable(5, 'discrete_count'); mc.assert_publishable(5.0, 'discrete_count'); mc.assert_publishable(None, 'discrete_count')
        mc.assert_publishable(5.25, 'continuous_length'); mc.assert_publishable(-3, 'discrete_count', signed=True)
        for bad in (5.5, -1, float('nan'), True, '7'):
            with self.assertRaises(ValueError):
                mc.assert_publishable(bad, 'discrete_count')
        with self.assertRaises(ValueError):
            mc.assert_publishable(-2.5, 'continuous_length')

    def test_public_csv_writer_blocks_a_fractional_count_before_writing(self):
        with tempfile.TemporaryDirectory() as t:
            f = Path(t) / 'p.csv'
            with self.assertRaises(ValueError):
                mc.write_public_csv(f, [dict(ano=2026, valor=100), dict(ano=2027, valor=100.4)], {'valor': 'discrete_count'})
            self.assertFalse(f.exists())
            mc.write_public_csv(f, [dict(ano=2026, valor=100, km=12.345)], {'valor': 'discrete_count', 'km': 'continuous_length'})
            self.assertIn('12.345', f.read_text(encoding='utf-8-sig')); self.assertNotIn('100.0', f.read_text(encoding='utf-8-sig'))

    def test_empty_csv_cells_are_nd_and_pass_the_gate_but_text_does_not(self):
        mc.assert_public_table([dict(v=''), dict(v=None), dict(v=3)], {'v': 'discrete_count'})
        with self.assertRaises(ValueError):
            mc.assert_public_table([dict(v='3')], {'v': 'discrete_count'})

    def test_json_dump_of_physical_predictions_contains_no_fraction(self):
        rows = [dict(valor=mc.physical_prediction(v, 'discrete_count')) for v in (1.2, 99.5, 1e6 + .49)]
        self.assertEqual(json.dumps(rows), '[{"valor": 1}, {"valor": 100}, {"valor": 1000000}]')


def experiment(rows):
    """rows: (key, origin, municipality, actual, pred)"""
    return dict(predictions=[dict(key=k, origin=o, horizon=1, municipality=m, actual=a, pred=p) for k, o, m, a, p in rows], folds=[], failures=[])


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


def mc_round(x):
    return mc.round_count(x)


if __name__ == '__main__':
    unittest.main()
