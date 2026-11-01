"""Feature audit: ARE_LOC domain, independent consumption, municipal coverage, external gating, no leakage."""
import json
import tempfile
import unittest
from pathlib import Path

import duckdb
import numpy as np

from motor_v2.comparison import choose_options, eligible_features, feature_subsets, load_panel, options
from motor_v2.externals import feature_allowed
from motor_v2.features import snapshots, urban_share
from motor_v2.runner import atomic, digest


def row(year=2024, **kw):
    r = dict(dist=26, year=year, group='1', feature_year=year-1, feature_available=f'{year-1}-12-31',
             feature_revision_available=f'{year-1}-12-31', target_available=f'{year}-12-31',
             x=[3., .5, 1.], stock=20., y=21., rupture=False, key=f'26:{year}:1')
    r.update(kw)
    return r


def panel():
    return [row(y, dist=d, group=str(m), key=f'{d}:{y}:{m}', y=20.+m % 7+(y-2023), x=[3.+m % 5, .4+(m % 3)/10, 1.+(m % 4)/10])
            for d in (26, 6585, 6600) for y in (2023, 2024, 2025) for m in range(60)]


class AreaDomain(unittest.TestCase):
    def test_ub_nu_known_and_share_is_over_known(self):
        u = urban_share({'UB': 70, 'NU': 30})
        self.assertEqual((u['share'], u['coverage'], u['unknown']), (.7, 1., 0))

    def test_zero_code_is_unknown_not_nonurban(self):
        # 0 = "Nao informado" in the TARE domain: coverage drops, share is over known customers only.
        u = urban_share({'UB': 700, 'NU': 299, '0': 1})
        self.assertEqual(u['unknown'], 1)
        self.assertAlmostEqual(u['coverage'], .999)
        self.assertAlmostEqual(u['share'], 700/999)
        self.assertEqual(u['reason'], 'available_over_known_customers')

    def test_undeclared_ru_and_missing_are_unknown_and_block_above_tolerance(self):
        u = urban_share({'UB': 50, 'RU': 40, 'MISSING': 10})
        self.assertIsNone(u['share'])
        self.assertEqual((u['known'], u['unknown']), (50, 50))
        self.assertEqual(u['reason'], 'unknown_area_codes_above_tolerance')

    def test_empty_has_no_share(self):
        self.assertIsNone(urban_share({})['share'])


class IndependentConsumption(unittest.TestCase):
    def test_stock_plus_consumption_is_tested_without_urbanization(self):
        self.assertIn([0, 2], feature_subsets([0, 2]))
        self.assertNotIn(1, [i for f in feature_subsets([0, 2]) for i in f])
        for model in ('ols', 'ridge', 'elastic_net', 'poisson', 'random_forest', 'hist_gradient_boosting'):
            self.assertIn([0, 2], [o['features'] for o in options(model, 2, 42, eligible=[0, 2])])

    def test_full_search_space_when_everything_is_eligible(self):
        self.assertEqual(feature_subsets([0, 1, 2]), [[0], [0, 2], [0, 1], [0, 1, 2]])

    def test_missing_covariate_is_never_imputed_as_zero(self):
        rows = [row(group=str(i), x=[3., None, 1.]) for i in range(10)]
        self.assertEqual(eligible_features(rows, [], 'point_in_time', 3), [0, 2])
        self.assertTrue(all(r['x'][1] is None for r in rows))

    def test_eligible_search_runs_consumption_without_urbanization(self):
        rows = panel()
        for r in rows:
            r['x'][1] = None
        cfg = dict(max_trials=3, seed=42)
        selected, trials, _ = choose_options(rows, 26, 2024, 'reconciled_retrospective', 'shared_pilot', set(), 'ridge', cfg)
        tried = [t['features'] for t in trials]
        self.assertIn([0, 2], tried)
        self.assertNotIn([0, 1], tried)
        self.assertTrue(any(t['status'] == 'inner_validation' for t in trials if t['features'] == [0, 2]))


class NoLeakage(unittest.TestCase):
    def test_selection_does_not_see_labels_after_the_inner_origin(self):
        cfg = dict(max_trials=4, seed=42)
        base = choose_options(panel(), 26, 2024, 'reconciled_retrospective', 'shared_pilot', set(), 'ridge', cfg)
        rows = panel()
        for r in rows:
            if r['year'] > 2024:        # outer-test labels and features are perturbed wildly
                r['y'] *= 50; r['x'] = [v * 9 if v is not None else None for v in r['x']]
        changed = choose_options(rows, 26, 2024, 'reconciled_retrospective', 'shared_pilot', set(), 'ridge', cfg)
        self.assertEqual(base[0]['features'], changed[0]['features'])
        self.assertEqual(base[0]['params'], changed[0]['params'])
        self.assertEqual([t['mae'] for t in base[1]], [t['mae'] for t in changed[1]])


class ExternalGating(unittest.TestCase):
    def meta(self, **kw):
        m = dict(reference_year=2022, available='2026-10-28', released='2023-08-31')
        m.update(kw)
        return m

    def test_point_in_time_requires_verified_availability_before_origin(self):
        r = row(2024, feature_meta={'log_population': self.meta()})
        self.assertFalse(feature_allowed(r, 3, 'point_in_time'))                 # downloaded in 2026: vintage not proven
        r['feature_meta']['log_population'] = self.meta(available='2023-12-31')
        self.assertTrue(feature_allowed(r, 3, 'point_in_time'))

    def test_retrospective_allows_later_vintages_but_never_same_or_future_reference(self):
        r = row(2024, feature_meta={'log_population': self.meta()})
        self.assertTrue(feature_allowed(r, 3, 'reconciled_retrospective'))
        r['feature_meta']['log_population'] = self.meta(reference_year=2024)
        self.assertFalse(feature_allowed(r, 3, 'reconciled_retrospective'))

    def test_feature_without_provenance_is_not_allowed(self):
        self.assertFalse(feature_allowed(row(2024), 3, 'reconciled_retrospective'))


class MunicipalCoverageAndCheckpoints(unittest.TestCase):
    def build(self, root, years, municipalities):
        db = duckdb.connect()
        history = []
        for y in years:
            d = Path(root) / '26' / 'ucbt_quantidade' / str(y); d.mkdir(parents=True)
            f = d / 'territorial.parquet'
            vals = ','.join(f"('{m}','UB',{n},{n},CAST({n*100.} AS DOUBLE))" for m, n in municipalities[y].items())
            db.execute(f"COPY (SELECT * FROM (VALUES {vals}) t(MUN,ARE_LOC,clientes_ativos,energia_denominador,energia_kwh)) TO '{f.as_posix()}' (FORMAT parquet)")
            atomic(d / 'checkpoint.json', dict(output_sha256=digest(f)))
            history.append(dict(year=y, available=f'{y}-10-01', rupture=False, qa={}))
        atomic(Path(root) / '26' / 'ucbt_quantidade' / 'result.json', dict(dist=26, history=history))
        db.close()

    def test_entering_municipality_is_missing_not_zero_and_partial_coverage_is_reported(self):
        with tempfile.TemporaryDirectory() as t:
            self.build(t, (2022, 2023), {2022: {'2500001': 100, '2500002': 50}, 2023: {'2500001': 110, '2500002': 55, '2500003': 400}})
            rows, quality, _ = load_panel(t)
            self.assertEqual({r['group'] for r in rows}, {'2500001', '2500002'})   # 2500003 has no prior snapshot: no target, no zero
            q = next(x for x in quality if x['year'] == 2023)
            self.assertEqual((q['municipal_total'], q['matched_cohort']), (565, 165))
            self.assertAlmostEqual(q['coverage'], 165/565)

    def test_tampered_aggregate_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            self.build(t, (2022,), {2022: {'2500001': 100}})
            f = Path(t) / '26' / 'ucbt_quantidade' / '2022' / 'territorial.parquet'
            f.write_bytes(f.read_bytes() + b'x')
            with self.assertRaises(ValueError):
                snapshots(t)


if __name__ == '__main__':
    unittest.main()
