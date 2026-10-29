"""Shared attribute matrix, cross-family features, coverage/continuity gates, forward selection, CONJ audit and origins."""
import json
import tempfile
import unittest
from pathlib import Path

import duckdb
import numpy as np

from motor_v2 import audit_conj, origins_audit, shared
from motor_v2.assets import extract_transformers
from motor_v2.comparison import choose_options, load_panel
from motor_v2.externals import feature_allowed
from motor_v2.features import FEATURES
from motor_v2.runner import atomic, digest

ROOT = Path(__file__).resolve().parents[2]
CROSS_IDX = {n: FEATURES.index(n) for n in shared.CROSS}


def write_parquet(path, select):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    duckdb.connect().execute(f"COPY ({select}) TO '{Path(path).as_posix()}' (FORMAT parquet)")


def history(root, dist, asset, years, avail, values=None, cov=None):
    hist = []
    for y in years:
        f = Path(root) / str(dist) / asset / str(y) / 'territorial.parquet'
        atomic(f.parent / 'checkpoint.json', dict(output_sha256=digest(f)))
        hist.append(dict(year=y, available=avail[y], rupture=False, value=None if values is None else values[y],
                         qa=dict(territorial_conflicts=0, coverage=None if cov is None else cov[y])))
    atomic(Path(root) / str(dist) / asset / 'result.json', dict(dist=dist, history=hist))


def tree(tmp, years=(2022, 2023), ucbt_avail=None, tr_avail=None):
    """UCBT run (MUN, CONJ, ARE_LOC, clients, energy) and asset run (trafo count/kVA by UNIT+CONJ, SSDMT km by CONJ) for DIST 6600."""
    uroot, aroot = Path(tmp) / 'ucbt', Path(tmp) / 'assets'
    ua = ucbt_avail or {y: f'{y}-10-01' for y in years}; ta = tr_avail or {y: f'{y}-10-02' for y in years}
    for y in years:
        k = 1 + (y - 2022) * .1
        write_parquet(uroot / '6600' / 'ucbt_quantidade' / str(y) / 'territorial.parquet',
                      f"SELECT * FROM (VALUES ('2500001','C1','UB',{int(100*k)},{int(100*k)},CAST({int(100*k)*1000} AS DOUBLE)),"
                      f"('2500001','C1','NU',{int(20*k)},{int(20*k)},CAST({int(20*k)*500} AS DOUBLE)),"
                      f"('2500002','C2','UB',{int(50*k)},{int(50*k)},CAST({int(50*k)*800} AS DOUBLE))) t(MUN,CONJ,ARE_LOC,clientes_ativos,energia_denominador,energia_kwh)")
        write_parquet(aroot / '6600' / 'trafo_dist_quantidade' / str(y) / 'territorial.parquet',
                      f"SELECT * FROM (VALUES ('2500001','C1',CAST({int(10*k)} AS DOUBLE),{int(10*k)}),('2500002','C2',CAST({int(5*k)} AS DOUBLE),{int(5*k)})) t(UNIT,CONJ,value,rows)")
        write_parquet(aroot / '6600' / 'trafo_dist_potencia_kva' / str(y) / 'territorial.parquet',
                      f"SELECT * FROM (VALUES ('2500001','C1',CAST({int(750*k)} AS DOUBLE),{int(10*k)}),('2500002','C2',CAST({int(375*k)} AS DOUBLE),{int(5*k)})) t(UNIT,CONJ,value,rows)")
        write_parquet(aroot / '6600' / 'rede_mt_extensao_km' / str(y) / 'territorial.parquet',
                      f"SELECT * FROM (VALUES ('C1','C1',CAST({100*k} AS DOUBLE),9),('C2','C2',CAST({40*k} AS DOUBLE),4),('MISSING','MISSING',CAST(1.0 AS DOUBLE),1)) t(UNIT,CONJ,value,rows)")
    history(uroot, 6600, 'ucbt_quantidade', years, ua)
    for a in ('trafo_dist_quantidade', 'trafo_dist_potencia_kva', 'rede_mt_extensao_km'):
        history(aroot, 6600, a, years, ta)
    return str(aroot), str(uroot)


class SharedMatrix(unittest.TestCase):
    def test_municipal_and_conjunto_matrices_use_only_fields_of_the_records(self):
        with tempfile.TemporaryDirectory() as t:
            a, u = tree(t)
            m = shared.build(a, u, [6600], 'municipality')
            v = m[6600, 2022, '2500001']['values']
            self.assertEqual((v['ucbt_clients'], v['trafo_count'], v['trafo_kva']), (120., 10., 750.))
            self.assertAlmostEqual(v['ucbt_urban_share'], 100 / 120); self.assertAlmostEqual(v['clients_per_trafo'], 12.)
            self.assertAlmostEqual(v['kva_per_client'], 750 / 120); self.assertNotIn('mt_km', v)    # SSDMT has no MUN: never attributed
            c = shared.build(a, u, [6600], 'conjunto')
            self.assertEqual(c[6600, 2022, 'C1']['values']['mt_km'], 100.); self.assertNotIn((6600, 2022, 'MISSING'), c)
            self.assertEqual(c[6600, 2022, 'C1']['values']['trafo_count'], 10.)

    def test_availability_is_the_publication_date_of_each_family(self):
        with tempfile.TemporaryDirectory() as t:
            a, u = tree(t)
            m = shared.build(a, u, [6600], 'municipality')
            self.assertEqual(m[6600, 2022, '2500001']['avail']['ucbt'], '2022-10-01')
            self.assertEqual(m[6600, 2022, '2500001']['avail']['trafo_kva'], '2022-10-02')
            self.assertEqual(m[6600, 2022, '2500001']['avail']['ratio'], '2022-10-02')

    def test_ratios_need_positive_denominators(self):
        with tempfile.TemporaryDirectory() as t:
            a, u = tree(t, years=(2022,))
            write_parquet(Path(a) / '6600' / 'trafo_dist_quantidade' / '2022' / 'territorial.parquet',
                          "SELECT * FROM (VALUES ('2500001','C1',CAST(0 AS DOUBLE),0),('2500002','C2',CAST(5 AS DOUBLE),5)) t(UNIT,CONJ,value,rows)")
            history(a, 6600, 'trafo_dist_quantidade', (2022,), {2022: '2022-10-02'})
            m = shared.build(a, u, [6600], 'municipality')
            self.assertIsNone(m[6600, 2022, '2500001']['values']['clients_per_trafo'])

    def test_tampered_aggregate_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            a, u = tree(t, years=(2022,))
            f = Path(a) / '6600' / 'trafo_dist_quantidade' / '2022' / 'territorial.parquet'
            f.write_bytes(f.read_bytes() + b'x')
            with self.assertRaises(ValueError):
                shared.build(a, u, [6600], 'municipality')


def panel_row(group='2500001', year=2023):
    return dict(dist=6600, year=year, group=group, feature_year=year-1, feature_available=f'{year-1}-12-31', feature_revision_available=f'{year-1}-12-31',
                target_available=f'{year}-12-31', x=[3., None, None], stock=20., y=21., rupture=False, key=f'6600:{year}:{group}', unit_kind='municipality')


class CrossFamilyFeatures(unittest.TestCase):
    def matrix(self, **kw):
        with tempfile.TemporaryDirectory() as t:
            a, u = tree(t, **kw)
            return shared.build(a, u, [6600], 'municipality')

    def test_transformer_asset_receives_ucbt_and_cross_family_values_from_t_minus_1(self):
        m = self.matrix()
        r = shared.attach([panel_row()], m, 'trafo_dist_quantidade')[0]
        x = lambda n: r['x'][CROSS_IDX[n]]
        self.assertAlmostEqual(x('urban_share'), 100 / 120)
        self.assertAlmostEqual(x('log_ucbt_clients'), np.log1p(120.)); self.assertAlmostEqual(x('log_trafo_kva'), np.log1p(750.))
        self.assertIsNone(x('log_trafo_count'))                                  # own lag of the target: never offered
        self.assertEqual(r['feature_meta']['log_trafo_kva']['reference_year'], 2022)

    def test_own_lag_is_skipped_for_each_target(self):
        m = self.matrix()
        k = shared.attach([panel_row()], m, 'trafo_dist_potencia_kva')[0]
        self.assertIsNone(k['x'][CROSS_IDX['log_trafo_kva']]); self.assertIsNotNone(k['x'][CROSS_IDX['log_trafo_count']])

    def test_assets_that_do_not_use_cross_features_are_untouched(self):
        r = panel_row()
        self.assertEqual(shared.attach([r], self.matrix(), 'ucbt_quantidade')[0]['x'], r['x'])

    def test_point_in_time_gate_uses_the_availability_of_the_source_publication(self):
        late = self.matrix(ucbt_avail={2022: '2024-06-01', 2023: '2024-06-01'}, tr_avail={2022: '2022-12-30', 2023: '2023-12-30'})
        r = shared.attach([panel_row()], late, 'trafo_dist_quantidade')[0]
        i = CROSS_IDX['log_ucbt_clients']
        self.assertFalse(feature_allowed(r, i, 'point_in_time'))                 # UCBT revision published after the origin year end
        self.assertTrue(feature_allowed(r, i, 'reconciled_retrospective'))
        self.assertTrue(feature_allowed(r, CROSS_IDX['log_trafo_kva'], 'point_in_time'))   # published 2022-12-30, before 2022-12-31
        # a cross-family value in the urban_share slot is gated too (indices < 3 are no longer a blanket pass)
        self.assertFalse(feature_allowed(r, CROSS_IDX['urban_share'], 'point_in_time'))

    def test_unit_without_a_matrix_cell_stays_missing(self):
        r = shared.attach([panel_row('2599999')], self.matrix(), 'trafo_dist_quantidade')[0]
        self.assertTrue(all(r['x'][i] is None for i in CROSS_IDX.values()))


class Gates(unittest.TestCase):
    def build(self, root, asset, years, data, values, cov=None, avail=None):
        for y in years:
            vals = ','.join(f"('{u}',CAST({v} AS DOUBLE),1)" for u, v in data[y].items())
            write_parquet(Path(root) / '6600' / asset / str(y) / 'territorial.parquet', f"SELECT * FROM (VALUES {vals}) t(UNIT,value,rows)")
        history(root, 6600, asset, years, avail or {y: f'{y}-10-01' for y in years}, values, cov)

    def test_coverage_gate_withholds_a_year_whose_territorial_sum_misses_the_physical_total(self):
        with tempfile.TemporaryDirectory() as t:
            m = ['2500001', '2500002', '2500003']
            data = {2022: dict.fromkeys(m, 10.), 2023: dict.fromkeys(m, 10.), 2024: dict.fromkeys(m, 10.)}
            self.build(t, 'trafo_dist_quantidade', (2022, 2023, 2024), data, {2022: 30., 2023: 60., 2024: 30.})   # 2023: units cover only half
            rows, q, _ = load_panel(t, 'trafo_dist_quantidade', None, min_coverage=.98)
            self.assertEqual({(r['year'], r['rupture']) for r in rows}, {(2023, True), (2024, True)})   # 2023 as target year, 2024 via its t-1
            self.assertTrue(next(x for x in q if x['year'] == 2023)['territorial_coverage'] == .5)
            self.assertTrue(rows[0]['rupture_reason'].startswith('coverage_gate'))
            free, _, _ = load_panel(t, 'trafo_dist_quantidade')                                          # default: no gate, previous behaviour
            self.assertFalse(any(r['rupture'] for r in free))

    def test_withheld_physical_value_blocks_the_year(self):
        with tempfile.TemporaryDirectory() as t:
            m = ['2500001', '2500002']
            self.build(t, 'trafo_dist_potencia_kva', (2022, 2023), {2022: dict.fromkeys(m, 5.), 2023: dict.fromkeys(m, 5.)}, {2022: 10., 2023: None})
            rows, q, _ = load_panel(t, 'trafo_dist_potencia_kva', None, min_coverage=.98)
            self.assertTrue(all(r['rupture'] for r in rows)); self.assertIsNone(next(x for x in q if x['year'] == 2023)['territorial_coverage'])

    def test_asset_link_coverage_is_part_of_the_gate(self):
        with tempfile.TemporaryDirectory() as t:
            m = ['2500001', '2500002']
            self.build(t, 'trafo_dist_quantidade', (2022, 2023), {2022: dict.fromkeys(m, 5.), 2023: dict.fromkeys(m, 5.)}, {2022: 10., 2023: 10.}, cov={2022: 1., 2023: .90})
            rows, _, _ = load_panel(t, 'trafo_dist_quantidade', None, min_coverage=.98)
            self.assertTrue(all(r['rupture'] for r in rows))

    def test_continuity_gate_withholds_a_renumbered_conjunto_transition(self):
        with tempfile.TemporaryDirectory() as t:
            data = {2022: {'C1': 50., 'C2': 50.}, 2023: {'C1': 10., 'N1': 45., 'N2': 45.}, 2024: {'C1': 11., 'N1': 46., 'N2': 46.}}
            self.build(t, 'rede_mt_extensao_km', (2022, 2023, 2024), data, {2022: 100., 2023: 100., 2024: 103.})
            rows, q, _ = load_panel(t, 'rede_mt_extensao_km', None, min_continuity=.95)
            flag = {(r['group'], r['year']): r['rupture'] for r in rows}
            self.assertTrue(flag['C1', 2023]); self.assertFalse(flag['C1', 2024]); self.assertFalse(flag['N1', 2024])
            self.assertAlmostEqual(next(x for x in q if x['year'] == 2023)['unit_continuity'], .1)
            self.assertFalse(any(r['rupture'] for r in load_panel(t, 'rede_mt_extensao_km')[0]))        # off by default


class ForwardSelection(unittest.TestCase):
    def panel(self, perturb_outer=False):
        rng = np.random.default_rng(7)
        rows = []
        for d in (26, 6585, 6600):
            for y in (2023, 2024, 2025):
                for m in range(80):
                    informative = float(rng.normal())
                    noise = [float(rng.normal()) for _ in range(len(FEATURES))]
                    base = 3. + (m % 7) * .2
                    x = [base, None, None] + noise[3:]
                    x[8] = informative
                    yv = np.expm1(base + .5 * informative + rng.normal(0, .01))
                    if perturb_outer and y > 2024:
                        yv *= 50; x[8] = 99.
                    rows.append(dict(dist=d, year=y, group=str(m), feature_year=y-1, feature_available=f'{y-1}-12-31', feature_revision_available=f'{y-1}-12-31',
                                     target_available=f'{y}-12-31', x=x, stock=float(np.expm1(base)), y=float(yv), rupture=False, key=f'{d}:{y}:{m}',
                                     feature_meta={n: dict(reference_year=y-2, available='2020-01-01', released='2020-01-01') for n in FEATURES[3:]}))
        return rows

    cfg = dict(max_trials=2, seed=42, forward_selection=True, max_features=3)

    def test_forward_selection_finds_the_informative_feature_inside_the_inner_validation(self):
        sel, trials, _ = choose_options(self.panel(), 26, 2024, 'reconciled_retrospective', 'shared_pilot', set(), 'ridge', self.cfg)
        self.assertIn(8, sel['features'])
        self.assertTrue(any(len(t['features']) >= 3 for t in trials))                 # it actually grew the subset
        off, trials_off, _ = choose_options(self.panel(), 26, 2024, 'reconciled_retrospective', 'shared_pilot', set(), 'ridge', dict(self.cfg, forward_selection=False))
        self.assertLess(len(trials_off), len(trials))

    def test_selection_ignores_everything_after_the_inner_origin(self):
        a = choose_options(self.panel(), 26, 2024, 'reconciled_retrospective', 'shared_pilot', set(), 'ridge', self.cfg)
        b = choose_options(self.panel(True), 26, 2024, 'reconciled_retrospective', 'shared_pilot', set(), 'ridge', self.cfg)
        self.assertEqual(a[0]['features'], b[0]['features']); self.assertEqual([t['mae'] for t in a[1]], [t['mae'] for t in b[1]])


class ConjAudit(unittest.TestCase):
    def test_share_and_maps(self):
        self.assertEqual(audit_conj.share({'A': 3., 'B': 1.}, {'A'}), .75)
        with tempfile.TemporaryDirectory() as t:
            write_parquet(Path(t) / 'SSDMT.parquet', "SELECT * FROM (VALUES ('s1',1000.,'C1'),('s2',500.,'C2'),('s3',100.,NULL)) x(COD_ID,COMP,CONJ)")
            write_parquet(Path(t) / 'UNTRMT.parquet', "SELECT * FROM (VALUES ('u1','C1'),('u2','C1'),('u3','C9')) x(COD_ID,CONJ)")
            m = audit_conj.conj_maps(duckdb.connect(), dict(year=2022, base=t))
            self.assertEqual(m['ssdmt'], {'C1': 1., 'C2': .5, 'MISSING': .1}); self.assertEqual(m['untrmt'], {'C1': 2., 'C9': 1.})


class Origins(unittest.TestCase):
    def test_origin_counting_requires_the_year_before_and_after(self):
        self.assertEqual(origins_audit.origins_for([]), [2023, 2024])
        self.assertEqual(origins_audit.origins_for([2021]), [2022, 2023, 2024])
        self.assertEqual(origins_audit.origins_for([2019, 2020, 2021]), [2020, 2021, 2022, 2023, 2024])
        self.assertEqual(origins_audit.origins_for([2019]), [2023, 2024])                  # a gap in 2020-2021 does not add origins

    def test_title_parser_and_feasibility_from_a_catalog_snapshot(self):
        with tempfile.TemporaryDirectory() as t:
            cat = Path(t) / 'c.json'
            items = [dict(id=f'i{y}', title=f'Eletroacre_26_{y}-12-31_V10_20220401-1000', tags=['BDGD']) for y in (2020, 2021)]
            items.append(dict(id='dup', title='Eletroacre_26_2021-12-31_M10_20240119-1000', tags=['BDGD', 'Extra']))
            cat.write_text(json.dumps(dict(items=items)), encoding='utf-8')
            f = origins_audit.feasibility(origins_audit.parse(cat), [26])[0]
            self.assertEqual(f['competences_before_2022'], [2020, 2021]); self.assertEqual(f['duplicates_same_competence'], {2021: 2})
            self.assertEqual(f['origins_if_all_contiguous'], [2021, 2022, 2023, 2024]); self.assertEqual(f['minimum_required'], 3)

    def test_real_catalog_snapshot_reports_earlier_competences(self):
        cat = ROOT / 'auditoria/fase6/evidencias/catalogo_arcgis_atual.json'
        if not cat.exists():
            self.skipTest('catalog snapshot not in this checkout')
        f = {x['DIST']: x for x in origins_audit.feasibility(origins_audit.parse(cat), [26, 6585, 6600])}
        self.assertEqual(f[26]['competences_before_2022'], [2019, 2020, 2021]); self.assertEqual(f[6585]['competences_before_2022'][0], 2016)


class TransformerKeyAudit(unittest.TestCase):
    def test_key_uniqueness_and_orphan_counters(self):
        with tempfile.TemporaryDirectory() as t:
            base = Path(t) / 'in'
            write_parquet(base / 'EQTRMT.parquet', "SELECT * FROM (VALUES ('e1','565','u1'),('e1','565','u2'),('e2','565','u3'),('e3','565','u3'),('e4','565',NULL),('e5','565','uX'),('e6','570','u9')) x(COD_ID,TUC,UNI_TR_MT)")
            write_parquet(base / 'UNTRMT.parquet', "SELECT * FROM (VALUES ('u1','2500001',75.),('u2','2500001',45.),('u3','2500002',30.),('u9','2500001',10.),('u7','2500003',5.),('u7','2500003',5.)) x(COD_ID,MUN,POT_NOM)")
            dest = Path(t) / 'out'; dest.mkdir()
            a = extract_transformers(duckdb.connect(), dict(year=2022, base=str(base)), dest, '565', 'count')['audit']
            self.assertEqual(a['eq_total'], 6)
            self.assertEqual(a['eq_duplicate_ids'], 1)           # e1 twice
            self.assertEqual(a['eq_null_fk'], 1)                 # e4
            self.assertEqual(a['eq_fk_not_in_un'], 1)            # uX
            self.assertEqual(a['un_shared_by_many_eq'], 1)       # u3 serves e2 and e3
            self.assertEqual(a['un_duplicate_ids'], 1)           # u7 twice
            self.assertEqual(a['un_without_eq565'], 3)           # u9 (TUC 570) and the two u7 rows


if __name__ == '__main__':
    unittest.main()
