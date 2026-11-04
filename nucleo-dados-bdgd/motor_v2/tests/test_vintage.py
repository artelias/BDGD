import copy
import unittest

from motor_v2.temporal import usable
from motor_v2.vintage import (GENERATION_STAMP, INFERRED, PUBLICATION_RECORD, VINTAGE_PROVEN, VINTAGE_UNPROVEN, Release, VintageError,
                              available, claim, iso, rejected_later, select, view)


def releases():
    """Competence 2022 published 2023-06-30 and revised 2024-03-01; 2023 published 2024-07-15; 2024 published 2025-07-15."""
    return [Release(2022, '2023-06-30', 0, label='2022 v1'), Release(2022, '2024-03-01', 1, label='2022 v2 (revisao)'),
            Release(2023, '2024-07-15', 0, label='2023 v1'), Release(2024, '2025-07-15', 0, label='2024 v1')]


class EarlierCompetenceTests(unittest.TestCase):
    """Forecast with earlier-competence data that was published and available at the origin date; later revisions are rejected."""

    def test_earlier_competence_published_before_origin_is_used_with_its_first_vintage(self):
        v = view(releases(), '2024-01-15', 2024)           # 2022 v1 is out; the 2022 revision (2024-03-01) and 2023 (2024-07-15) are not
        self.assertEqual({c: r.label for c, r in v['selected'].items()}, {2022: '2022 v1'})
        self.assertEqual(v['last_competence'], 2022)
        self.assertEqual(v['effective_horizon'], 2)        # the forecast of 2024 is two competences ahead of the data actually available

    def test_later_revision_of_an_earlier_competence_is_rejected(self):
        v = view(releases(), '2024-01-15', 2024)
        self.assertNotIn('2022 v2 (revisao)', [r.label for r in v['selected'].values()])
        self.assertIn('2022 v2 (revisao)', [r.label for r in v['rejected_later']])
        self.assertIn('2023 v1', [r.label for r in v['rejected_later']])

    def test_revision_becomes_usable_only_once_published(self):
        self.assertEqual(select(releases(), 2022, '2024-02-29').label, '2022 v1')
        self.assertEqual(select(releases(), 2022, '2024-03-01').label, '2022 v2 (revisao)')   # the day of publication counts as available
        self.assertEqual(select(releases(), 2022, '2024-03-02').label, '2022 v2 (revisao)')

    def test_competence_not_yet_published_is_unavailable_not_guessed(self):
        self.assertIsNone(select(releases(), 2023, '2024-07-14'))
        self.assertEqual(select(releases(), 2023, '2024-07-15').label, '2023 v1')

    def test_later_origin_reads_newer_vintages_and_shorter_horizon(self):
        v = view(releases(), '2024-12-31', 2025)
        self.assertEqual({c: r.label for c, r in v['selected'].items()}, {2022: '2022 v2 (revisao)', 2023: '2023 v1'})
        self.assertEqual(v['effective_horizon'], 2)
        self.assertEqual([r.label for r in v['rejected_later']], ['2024 v1'])

    def test_same_day_vintages_are_ordered_by_revision(self):
        both = [Release(2022, '2024-03-01', 0, label='a'), Release(2022, '2024-03-01', 2, label='c'), Release(2022, '2024-03-01', 1, label='b')]
        self.assertEqual(select(both, 2022, '2024-03-01').label, 'c')

    def test_target_already_published_is_a_leak_not_a_forecast(self):
        with self.assertRaisesRegex(VintageError, 'leak'):
            view(releases(), '2024-08-01', 2023)           # 2023 was published on 2024-07-15: the "forecast" of 2023 is already known
        with self.assertRaisesRegex(VintageError, 'after the target year'):
            view(releases(), '2025-01-01', 2024)

    def test_data_never_comes_from_the_target_year_or_later(self):
        v = view(releases(), '2025-12-31', 2025)           # 2024 is the latest competence a forecast of 2025 may read
        self.assertTrue(all(c < 2025 for c in v['selected']))

    def test_dates_are_never_altered(self):
        before, rs = copy.deepcopy(releases()), releases()
        view(rs, '2024-01-15', 2024); available(rs, '2024-01-15'); rejected_later(rs, '2024-01-15')
        self.assertEqual(rs, before)
        with self.assertRaises(Exception):
            rs[0].published = '2020-01-01'                  # releases are immutable

    def test_impossible_or_malformed_dates_are_refused(self):
        with self.assertRaises(VintageError):
            Release(2023, '2022-12-31')                     # published before its own competence year
        for bad in ('2024/01/15', '2024-1-5', '20240115', '2024-02-30', None):
            with self.assertRaises(VintageError):
                iso(bad)
        with self.assertRaises(VintageError):
            Release(2023, '2024-01-15', evidence='rumor')


class VintageClaimTests(unittest.TestCase):
    """No backtest is called vintage-proven without publication records; reconciled runs never are."""

    def test_publication_records_prove_the_vintage(self):
        v = view(releases(), '2024-01-15', 2024)
        self.assertEqual(claim(v['selected'].values())['status'], VINTAGE_PROVEN)

    def test_generation_stamps_and_inferred_dates_are_candidates_only(self):
        for kind in (GENERATION_STAMP, INFERRED):
            rs = [Release(2022, '2023-06-30', evidence=PUBLICATION_RECORD), Release(2023, '2024-07-15', evidence=kind)]
            result = claim(rs)
            self.assertEqual(result['status'], VINTAGE_UNPROVEN)
            self.assertIn(kind, result['reason'])

    def test_reconciled_retrospective_never_acquires_credentials(self):
        self.assertEqual(claim([Release(2022, '2023-06-30')], 'reconciled_retrospective')['status'], VINTAGE_UNPROVEN)

    def test_nothing_read_proves_nothing(self):
        self.assertEqual(claim([])['status'], VINTAGE_UNPROVEN)


class UsableWithExplicitOriginDateTests(unittest.TestCase):
    """`temporal.usable` keeps its legacy clock by default and honours an explicit origin date when one is given."""

    def row(self, **changes):
        r = dict(year=2023, feature_year=2022, feature_available='2022-12-31', feature_revision_available='2022-12-31', target_available='2024-07-15')
        return r | changes

    def test_default_clock_is_unchanged(self):
        r = self.row()
        self.assertFalse(usable(r, 2023, 'point_in_time'))                      # target published 2024-07-15, after the legacy 2023-12-31 cutoff
        self.assertEqual(usable(r, 2023, 'point_in_time'), usable(r, 2023, 'point_in_time', True, None))

    def test_explicit_origin_date_admits_what_was_published_by_then(self):
        r = self.row()
        self.assertTrue(usable(r, 2023, 'point_in_time', True, '2024-07-15'))
        self.assertFalse(usable(r, 2023, 'point_in_time', True, '2024-07-14'))  # one day earlier: not yet published

    def test_later_revision_is_rejected_even_with_a_late_origin_date(self):
        r = self.row(feature_revision_available='2025-01-01')
        self.assertFalse(usable(r, 2023, 'point_in_time', True, '2024-12-31'))

    def test_explicit_origin_date_does_not_open_the_reconciled_mode_or_the_future(self):
        r = self.row()
        self.assertFalse(usable(r, 2022, 'point_in_time', True, '2030-01-01'))  # competence after the origin year is out in every case
        before = copy.deepcopy(r); usable(r, 2023, 'point_in_time', True, '2024-07-15'); self.assertEqual(before, r)


if __name__ == '__main__':
    unittest.main()
