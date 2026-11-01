"""Future covariates: original units first, transform last; provenance, territory, unit and availability rules."""
import math
import unittest

from motor_v2 import future

LAST = {('log_gdp', '2500001'): (1000., 2023), ('population_growth_census', '2500001'): (.01, 2022), ('log_population', '2500001'): (50000., 2024)}
OK = dict(id='GDP-S1', unit='thousand BRL current', approved=True, approved_by='arthur', approved_at='2026-10-30')


def gen(feats, **kw):
    kw.setdefault('as_of', '2026-10-31')
    return future.generate(feats, ['2500001'], LAST, **kw)


def by(cells, f, y):
    return next(c for c in cells if c['feature'] == f and c['year'] == y)


class OriginalUnitsFirst(unittest.TestCase):
    def test_rate_is_applied_to_the_original_value_and_only_then_transformed(self):
        c = by(gen(['log_gdp'], assumptions={'log_gdp': dict(OK, scenarios={'Moderado': {'rate': .02}})}), 'log_gdp', 2026)
        original = 1000. * 1.02 ** 3
        self.assertAlmostEqual(c['value_original'], original)
        self.assertAlmostEqual(c['value'], math.log1p(original))          # a rate on the log would give (log 1000)*1.02^3: wrong
        self.assertNotAlmostEqual(c['value'], math.log1p(1000.) * 1.02 ** 3)
        self.assertEqual((c['unit'], c['transform'], c['kind']), ('thousand BRL current', 'log1p', 'scenario_assumption'))

    def test_identity_features_keep_their_value(self):
        c = by(gen(['population_growth_census'], static_carry=('population_growth_census',)), 'population_growth_census', 2030)
        self.assertEqual((c['value'], c['value_original'], c['method'], c['age_years']), (.01, .01, 'static_carry_forward', 8))

    def test_explicit_path_is_in_original_units(self):
        a = dict(OK, id='P', unit='persons', scenarios={'Moderado': {'path': {2026: 51000., 2027: 52000.}}})
        cells = gen(['log_population'], assumptions={'log_population': a})
        self.assertAlmostEqual(by(cells, 'log_population', 2026)['value'], math.log1p(51000.))
        self.assertEqual(by(cells, 'log_population', 2028)['status'], 'unavailable')   # path has no 2028: no extrapolation

    def test_engine_path_in_original_units(self):
        cells = gen(['log_stock'], engine_paths={('log_stock', '2500001', 'Moderado'): {y: 100. + y for y in future.HORIZON}})
        c = by(cells, 'log_stock', 2026)
        self.assertAlmostEqual(c['value'], math.log1p(2126.)); self.assertEqual(c['kind'], 'engine_estimate')


class Provenance(unittest.TestCase):
    def test_no_source_is_unavailable_never_filled(self):
        for f in ('log_population', 'log_gdp'):
            c = by(gen([f]), f, 2027)
            self.assertEqual((c['status'], c['value'], c['value_original'], c['kind']), ('unavailable', None, None, None))

    def test_unapproved_assumption_is_unavailable(self):
        a = dict(OK, approved=False, scenarios={'Moderado': {'rate': .02}})
        c = by(gen(['log_gdp'], assumptions={'log_gdp': a}), 'log_gdp', 2026)
        self.assertEqual((c['status'], c['reason']), ('unavailable', 'assumption_not_approved'))
        for missing in ('approved_by', 'approved_at'):
            b = dict(OK, scenarios={'Moderado': {'rate': .02}})
            b.pop(missing)
            self.assertEqual(by(gen(['log_gdp'], assumptions={'log_gdp': b}), 'log_gdp', 2026)['reason'], 'assumption_not_approved')

    def test_assumption_approved_after_the_origin_is_not_usable(self):
        a = dict(OK, approved_at='2027-01-01', scenarios={'Moderado': {'rate': .02}})
        self.assertEqual(by(gen(['log_gdp'], assumptions={'log_gdp': a}), 'log_gdp', 2026)['reason'], 'assumption_approved_after_origin')

    def test_assumption_without_the_requested_scenario_is_unavailable(self):
        a = dict(OK, scenarios={'Agressivo': {'rate': .05}})
        self.assertEqual(by(gen(['log_gdp'], assumptions={'log_gdp': a}), 'log_gdp', 2026)['status'], 'unavailable')

    def test_official_projection_is_labelled_and_respects_availability(self):
        r = dict(feature='log_population', geo='2500001', year=2026, value=52000., unit='persons', source_id='IBGE-proj', projected=True, available_at='2026-08-01')
        self.assertEqual(by(gen(['log_population'], official=[r]), 'log_population', 2026)['kind'], 'official_projection')
        late = dict(r, available_at='2026-12-01')
        self.assertEqual(by(gen(['log_population'], official=[late]), 'log_population', 2026)['reason'], 'official_projection_not_available_at_origin')

    def test_one_provenance_per_cell(self):
        r = dict(feature='log_gdp', geo='2500001', year=2026, value=1100., unit='thousand BRL current', source_id='x', projected=True)
        a = dict(OK, scenarios={'Moderado': {'rate': .02}})
        with self.assertRaises(ValueError):
            gen(['log_gdp'], official=[r], assumptions={'log_gdp': a})


class Compatibility(unittest.TestCase):
    def test_wrong_unit_is_rejected(self):
        with self.assertRaises(ValueError):
            gen(['log_gdp'], assumptions={'log_gdp': dict(OK, unit='BRL', scenarios={'Moderado': {'rate': .02}})})
        with self.assertRaises(ValueError):
            gen(['log_population'], official=[dict(feature='log_population', geo='2500001', year=2026, value=1., unit='thousand persons', source_id='x', projected=True)])

    def test_unprojected_official_value_is_rejected(self):
        with self.assertRaises(ValueError):
            gen(['log_population'], official=[dict(feature='log_population', geo='2500001', year=2026, value=1., unit='persons', source_id='x')])

    def test_territorial_incompatibility_is_unavailable_not_mapped(self):
        c = by(future.generate(['log_gdp'], ['C1'], {}, unit_kind='conjunto', assumptions={'log_gdp': dict(OK, scenarios={'Moderado': {'rate': .1}})}), 'log_gdp', 2026)
        self.assertEqual((c['status'], c['reason']), ('unavailable', 'territorial_incompatible'))

    def test_source_not_obtained_feature_is_unavailable(self):
        c = by(future.generate(['dec'], ['C1'], {}, unit_kind='conjunto'), 'dec', 2026)
        self.assertEqual(c['reason'], 'source_not_obtained')

    def test_observed_years_and_invalid_values_are_rejected(self):
        with self.assertRaises(ValueError):
            gen(['log_gdp'], years=(2025, 2026))
        a = dict(OK, scenarios={'Moderado': {'path': {2026: -5.}}})
        with self.assertRaises(ValueError):
            gen(['log_gdp'], assumptions={'log_gdp': a})             # negative GDP is not valid for a non-negative feature

    def test_summary_counts_by_provenance(self):
        s = future.summarize(gen(['log_population']))
        self.assertTrue(all('unavailable' in k for k in s['counts']))


if __name__ == '__main__':
    unittest.main()
