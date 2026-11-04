"""Policy, registry, future covariates, perimeter bridges and the generalized asset extractors."""
import json
import tempfile
import unittest
from pathlib import Path

import duckdb
import numpy as np

from motor_v2 import bridges, feature_registry
from motor_v2.assets import ASSETS, extract_network, extract_transformers
from motor_v2.comparison import eligible_features, feature_report, fit_predict, load_panel
from motor_v2.externals import feature_allowed
from motor_v2.features import FEATURES
from motor_v2.policy import FeaturePolicy, design, feature_status, fit_imputer
from motor_v2.runner import atomic, digest

ROOT = Path(__file__).resolve().parents[2]


def row(i, year=2024, **kw):
    r = dict(dist=26, year=year, group=str(i), feature_year=year-1, feature_available=f'{year-1}-12-31',
             feature_revision_available=f'{year-1}-12-31', target_available=f'{year}-12-31',
             x=[3.+i % 5, .5, 1.+i % 3, 10., .01, 12.], stock=20., y=21.+i % 4, rupture=False, key=f'26:{year}:{i}',
             feature_meta={n: dict(reference_year=year-2, available='2020-01-01', released='2020-01-01') for n in FEATURES[3:]})
    r.update(kw)
    return r


def with_gap(n, missing, feature=3, year=2024):
    rows = [row(i, year) for i in range(n)]
    for i in missing:
        rows[i]['x'][feature] = None
    return rows


class Policy(unittest.TestCase):
    def test_strict_is_default_and_drops_a_feature_missing_in_a_few_rows(self):
        rows = with_gap(40, [0, 1])
        st = feature_status(3, rows, [], 'reconciled_retrospective', FeaturePolicy(), feature_allowed)
        self.assertFalse(st['eligible']); self.assertEqual(st['reason'], 'missing_values_strict')
        self.assertNotIn(3, eligible_features(rows, [], 'reconciled_retrospective', 6))

    def test_coverage_policy_keeps_the_feature_when_training_coverage_is_enough(self):
        rows = with_gap(40, [0, 1]); policy = FeaturePolicy('coverage', .9, 'median')
        self.assertIn(3, eligible_features(rows, [], 'reconciled_retrospective', 6, policy))
        rep = feature_report(rows, [], 'reconciled_retrospective', 6, policy)['log_population']
        self.assertEqual(rep['reason'], 'imputed_with_train_statistic'); self.assertAlmostEqual(rep['train_coverage'], .95)

    def test_coverage_below_minimum_drops_the_feature(self):
        rows = with_gap(40, range(10))
        self.assertNotIn(3, eligible_features(rows, [], 'reconciled_retrospective', 6, FeaturePolicy('coverage', .9, 'median')))

    def test_statistic_is_fitted_on_training_rows_only(self):
        train = [row(i) for i in range(10)]
        for i, r in enumerate(train):
            r['x'][3] = float(i)
        test = [row(100, year=2025)]; test[0]['x'][3] = None
        policy = FeaturePolicy('coverage', .9, 'median')
        stats = fit_imputer(train, [3], policy)
        self.assertEqual(stats[3], 4.5)
        outlier = [row(200, year=2025)]; outlier[0]['x'][3] = 1e9           # evaluation values never move the statistic
        self.assertEqual(fit_imputer(train, [3], policy)[3], 4.5)
        self.assertEqual(design(test, [3], stats, policy)[0][0], 4.5)

    def test_missing_value_without_a_fitted_statistic_is_an_error_never_zero(self):
        with self.assertRaises(ValueError):
            design([row(0, x=[3., .5, None])], [0, 2], {}, FeaturePolicy())

    def test_missing_indicator_columns_flag_imputed_cells(self):
        policy = FeaturePolicy('coverage', .5, 'mean', missing_indicator=True)
        train = [row(i) for i in range(10)]; train[0]['x'][3] = None
        m = design(train, [0, 3], fit_imputer(train, [0, 3], policy), policy)
        self.assertEqual(m.shape, (10, 4)); self.assertEqual(m[0, 3], 1.); self.assertEqual(m[1, 3], 0.)

    def test_release_gate_failure_is_not_imputed(self):
        rows = [row(i) for i in range(20)]
        rows[0]['feature_meta']['log_population']['available'] = '2030-01-01'
        st = feature_status(3, rows, [], 'point_in_time', FeaturePolicy('coverage', .5, 'median'), feature_allowed)
        self.assertEqual(st['reason'], 'release_or_reference_gate')

    def test_invalid_policies_are_rejected(self):
        for bad in (dict(strategy='strict', imputation='median'), dict(strategy='coverage', imputation='none'),
                    dict(strategy='coverage', imputation='median', min_train_coverage=0), dict(strategy='x')):
            with self.assertRaises(ValueError):
                FeaturePolicy(**bad)

    def test_target_is_never_imputed_by_the_fit(self):
        train = [row(i) for i in range(30)]; train[3]['y'] = None
        with self.assertRaises(Exception):
            fit_predict('ols', dict(features=[0], params={}, mode='reconciled_retrospective'), train, [row(99, year=2025)], 42)


class RegistryAndFuture(unittest.TestCase):
    def test_registry_matches_features_and_encodes_eligibility(self):
        feature_registry.check_alignment()
        by = {s.name: s for s in feature_registry.SPECS}
        self.assertEqual(feature_registry.eligible_for(by['urban_share'], 'trafo_dist_quantidade')[0], True)      # cross-family, from UCBT
        self.assertEqual(feature_registry.eligible_for(by['log_trafo_count'], 'trafo_dist_quantidade'), (False, 'not_defined_for_asset'))   # own lag
        self.assertEqual(feature_registry.eligible_for(by['log_energy_per_client'], 'ucbt_quantidade')[0], True)
        self.assertEqual(feature_registry.eligible_for(by['log_gdp'], 'rede_mt_extensao_km'), (False, 'unit_mismatch:conjunto'))
        self.assertEqual(feature_registry.eligible_for(by['dec'], 'rede_mt_extensao_km'), (False, 'source_not_obtained'))
        self.assertTrue(feature_registry.eligible_for(by['log_stock'], 'rede_mt_extensao_km')[0])

    def test_registry_measures_coverage_and_availability(self):
        rows = with_gap(10, [0, 1, 2, 3, 4])
        rows[5]['feature_meta']['log_population']['available'] = '2026-10-28'
        out = {r['name']: r for r in feature_registry.build(rows, 'ucbt_quantidade')}
        self.assertAlmostEqual(out['log_population']['coverage'], .5)
        self.assertEqual(out['log_population']['point_in_time_rows'], 4)
        self.assertEqual(out['log_population']['retrospective_rows'], 5)
        self.assertEqual(out['log_population']['availability_max'], '2026-10-28')


def bridge(status='PENDING_HOMOLOGATION', **kw):
    b = dict(id='B1', version=1, kind='absorption', unit_kind='municipality', successor_dist=6600, predecessor_dist=6611, effective_year=2023,
             entering_units=['a', 'b'], overlap_units=['c'], status=status, decision=None, evidence={}, policy='x')
    b.update(kw)
    return b


class Bridges(unittest.TestCase):
    def test_pending_bridge_quarantines_entering_and_overlap_for_its_year_only(self):
        self.assertEqual(set(bridges.quarantine([bridge()], 6600, 2023, 'municipality')), {'a', 'b', 'c'})
        self.assertEqual(bridges.quarantine([bridge()], 6600, 2024), {})
        self.assertEqual(bridges.quarantine([bridge()], 26, 2023), {})
        self.assertEqual(bridges.quarantine([bridge(status='REJECTED')], 6600, 2023), {})

    def test_pending_or_rejected_bridge_never_combines_records(self):
        for st in ('PENDING_HOMOLOGATION', 'REJECTED'):
            with self.assertRaises(ValueError):
                bridges.combine({'x': 1}, {'y': 2}, bridge(st))

    def test_homologated_bridge_needs_a_decision_and_declared_overlap(self):
        with self.assertRaises(ValueError):
            bridges.validate(bridge('HOMOLOGATED'))
        b = bridges.validate(bridge('HOMOLOGATED', decision=dict(by='human', at='2026-11-01')))
        with self.assertRaises(ValueError):
            bridges.combine({'x': 1, 'z': 5}, {'x': 2, 'z': 6}, b)             # undeclared overlap is never summed
        self.assertEqual(bridges.combine({'a': 1, 'c': 5}, {'b': 2, 'c': 6}, b), {'a': 1, 'b': 2})

    def test_decision_cannot_be_recorded_on_a_pending_bridge(self):
        with self.assertRaises(ValueError):
            bridges.validate(bridge(decision=dict(by='x')))

    def test_versioned_epb_bridge_is_pending(self):
        loaded = bridges.load(ROOT / 'motor_v2' / 'bridges')
        epb = next(b for b in loaded if b['id'] == 'EPB_EBO_2023')
        self.assertEqual(epb['status'], 'PENDING_HOMOLOGATION'); self.assertIsNone(epb['decision'])
        self.assertEqual(len(epb['entering_units']), 6)


class SyntheticAssets(unittest.TestCase):
    def mk(self, root, eq, un, entity_pair=('EQTRMT', 'UNTRMT'), year=2022):
        db = duckdb.connect(); base = Path(root); base.mkdir(parents=True, exist_ok=True)
        db.execute(f"COPY (SELECT * FROM (VALUES {eq}) t(COD_ID,TUC,UNI_TR_MT)) TO '{(base/(entity_pair[0]+'.parquet')).as_posix()}' (FORMAT parquet)")
        db.execute(f"COPY (SELECT * FROM (VALUES {un}) t(COD_ID,MUN,POT_NOM)) TO '{(base/(entity_pair[1]+'.parquet')).as_posix()}' (FORMAT parquet)")
        db.close()
        return dict(year=year, base=str(base))

    def extract(self, eq, un, measure='count'):
        with tempfile.TemporaryDirectory() as t:
            src = self.mk(Path(t) / 'in', eq, un); dest = Path(t) / 'out'; dest.mkdir()
            con = duckdb.connect()
            qa = extract_transformers(con, src, dest, '565', measure)
            rows = duckdb.connect().execute('SELECT UNIT,value,rows FROM read_parquet(?) ORDER BY 1', [str(dest / 'territorial.parquet')]).fetchall()
            return qa, rows

    def test_only_tuc_565_is_counted_and_eq_un_are_not_added(self):
        qa, rows = self.extract("('e1','565','u1'),('e2','565','u2'),('e3','570','u3'),('e4','000','u4')",
                            "('u1','2500001',75.),('u2','2500002',45.),('u3','2500001',1000.),('u4','2500003',15.)")
        self.assertEqual(qa['value'], 2.); self.assertEqual(qa['audit']['eq_total'], 2); self.assertEqual(qa['coverage'], 1.)
        self.assertEqual(rows, [('2500001', 1., 1), ('2500002', 1., 1)])

    def test_unlinked_and_non_bijective_equipment_is_counted_in_total_but_not_assigned(self):
        qa, rows = self.extract("('e1','565','u1'),('e2','565','u1'),('e3','565','uX'),('e4','565','u2')",
                            "('u1','2500001',75.),('u2','2500002',45.)")
        self.assertEqual(qa['audit']['eq_total'], 4)
        self.assertEqual((qa['audit']['linked'], qa['audit']['unlinked']), (1, 3))     # u1 shared by two EQ: not bijective
        self.assertEqual(rows, [('2500002', 1., 1)])

    def test_power_series_is_withheld_when_link_coverage_is_low_or_power_invalid(self):
        qa, _ = self.extract("('e1','565','u1'),('e2','565','uX')", "('u1','2500001',75.)", 'kva')
        self.assertIsNone(qa['value'])                                                 # 50% link coverage < 98%
        qa, rows = self.extract("('e1','565','u1'),('e2','565','u2')", "('u1','2500001',75.),('u2','2500002',-3.)", 'kva')
        self.assertIsNone(qa['value'])                                                 # invalid power never becomes zero or a total
        self.assertEqual(qa['audit']['invalid_power'], 1)

    def test_power_is_summed_in_kva_from_the_unit(self):
        qa, rows = self.extract("('e1','565','u1'),('e2','565','u2')", "('u1','2500001',75.),('u2','2500001',45.)", 'kva')
        self.assertEqual(qa['value'], 120.); self.assertEqual(rows, [('2500001', 120., 2)])

    def test_network_km_by_conjunto_and_duplicate_ids_withhold_the_total(self):
        with tempfile.TemporaryDirectory() as t:
            db = duckdb.connect(); base = Path(t) / 'in'; base.mkdir(); dest = Path(t) / 'out'; dest.mkdir()
            def write(vals):
                db.execute(f"COPY (SELECT * FROM (VALUES {vals}) t(COD_ID,COMP,CONJ)) TO '{(base/'SSDMT.parquet').as_posix()}' (FORMAT parquet)")
            write("('s1',1000.,'C1'),('s2',500.,'C1'),('s3',250.,'C2'),('s4',100.,NULL)")
            qa = extract_network(duckdb.connect(), dict(year=2022, base=str(base)), dest)
            self.assertAlmostEqual(qa['value'], 1.85); self.assertAlmostEqual(qa['audit']['km_without_conj'], .1)
            write("('s1',1000.,'C1'),('s1',500.,'C1')")
            self.assertIsNone(extract_network(duckdb.connect(), dict(year=2022, base=str(base)), dest)['value'])

    def test_asset_registry_declares_units_and_counts(self):
        self.assertFalse(ASSETS['rede_mt_extensao_km']['count']); self.assertEqual(ASSETS['rede_mt_extensao_km']['unit_kind'], 'conjunto')
        self.assertTrue(ASSETS['trafo_dist_potencia_kva']['experimental'])


class PanelWithBridgeAndAssets(unittest.TestCase):
    def build(self, root, asset, years, data, bridge_dir=None):
        db = duckdb.connect(); history = []
        for y in years:
            d = Path(root) / '6600' / asset / str(y); d.mkdir(parents=True)
            f = d / 'territorial.parquet'
            vals = ','.join(f"('{u}',CAST({v} AS DOUBLE),1)" for u, v in data[y].items())
            db.execute(f"COPY (SELECT * FROM (VALUES {vals}) t(UNIT,value,rows)) TO '{f.as_posix()}' (FORMAT parquet)")
            atomic(d / 'checkpoint.json', dict(output_sha256=digest(f)))
            history.append(dict(year=y, available=f'{y}-10-01', rupture=False, value=sum(data[y].values()), qa=dict(territorial_conflicts=0)))
        atomic(Path(root) / '6600' / asset / 'result.json', dict(dist=6600, history=history))

    def test_bridge_quarantines_rows_without_dropping_the_audit_total(self):
        with tempfile.TemporaryDirectory() as t:
            m = ['2500001', '2500002', '2500003']
            self.build(t, 'trafo_dist_quantidade', (2022, 2023), {2022: dict.fromkeys(m, 10), 2023: dict.fromkeys(m, 11)})
            rows, quality, _ = load_panel(t, 'trafo_dist_quantidade', [bridge(overlap_units=['2500003'], entering_units=[])])
            flagged = {r['group']: r['rupture'] for r in rows}
            self.assertEqual(flagged, {'2500001': False, '2500002': False, '2500003': True})
            self.assertTrue(next(r for r in rows if r['group'] == '2500003')['rupture_reason'].startswith('perimeter_bridge_pending'))
            self.assertEqual(next(q for q in quality if q['year'] == 2023)['municipal_total'], 33)

    def test_conjunto_asset_has_no_municipal_validity_filter_and_no_urban_or_energy(self):
        with tempfile.TemporaryDirectory() as t:
            self.build(t, 'rede_mt_extensao_km', (2022, 2023), {2022: {'C1': 100., 'MISSING': 5.}, 2023: {'C1': 110., 'MISSING': 5.}})
            rows, _, _ = load_panel(t, 'rede_mt_extensao_km')
            self.assertEqual([r['group'] for r in rows], ['C1'])
            self.assertEqual(rows[0]['x'][1:], [None, None]); self.assertEqual(rows[0]['unit_kind'], 'conjunto')


class RealParquets(unittest.TestCase):
    """Real 2025 Parquets for EAC (DIST 26) against the versioned national contract (skipped when D: data is absent)."""
    SRC = Path('D:/NUCLEO_BDGD_2025/staging_parquet/DIST=26/DATA_BASE=2025-12-31')

    def contract(self, concept, metric):
        import csv
        rows = csv.DictReader(open(ROOT / 'output-historico/contrato-integracao/serie_fisica_nacional.csv', encoding='utf-8'))
        return next(float(r['valor']) for r in rows if (r['dist'], r['ano'], r['conceitoId'], r['metrica']) == ('26', '2025', concept, metric))

    @unittest.skipUnless(SRC.exists(), 'real Parquets not available')
    def test_transformers_tuc_565_match_contract_with_full_eq_un_link(self):
        with tempfile.TemporaryDirectory() as t:
            qa = extract_transformers(duckdb.connect(), dict(year=2025, base=str(self.SRC)), Path(t), '565', 'count')
            self.assertEqual(qa['value'], self.contract('trafo_dist', 'quantidade'))
            self.assertEqual(qa['audit']['entities'], ['EQTRMT', 'EQTRAT'] if 'EQTRAT' in qa['audit']['entities'] else ['EQTRMT'])
            self.assertGreaterEqual(qa['coverage'], .98)
            n = duckdb.connect().execute('SELECT sum(rows) FROM read_parquet(?)', [str(Path(t) / 'territorial.parquet')]).fetchone()[0]
            self.assertEqual(n, qa['audit']['linked'])
            kva = extract_transformers(duckdb.connect(), dict(year=2025, base=str(self.SRC)), Path(t), '565', 'kva')
            self.assertGreater(kva['value'], 0); self.assertEqual(kva['audit']['invalid_power'], 0)

    @unittest.skipUnless(SRC.exists(), 'real Parquets not available')
    def test_medium_voltage_network_matches_contract(self):
        with tempfile.TemporaryDirectory() as t:
            qa = extract_network(duckdb.connect(), dict(year=2025, base=str(self.SRC)), Path(t))
            self.assertAlmostEqual(qa['value'], self.contract('rede_mt', 'extensao_km'), places=5)
            self.assertEqual(qa['audit']['rows'], qa['audit']['unique_ids'])


if __name__ == '__main__':
    unittest.main()
