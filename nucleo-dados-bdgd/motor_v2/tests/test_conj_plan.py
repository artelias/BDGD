"""CONJ bridge proposals (evidence, never assumed equivalence) and the 2021 acquisition plan (nothing downloaded)."""
import json
import unittest
from pathlib import Path

from motor_v2 import bridges, conj_bridge, plan_2021
from motor_v2.origins_audit import parse

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / 'auditoria/fase6/evidencias/catalogo_arcgis_atual.json'


def year(ssd, ucbt=None, entity=None):
    """ssd/ucbt: {(ctmt, conj): stock}; entity: {conj: (name, area)}"""
    return dict(ssd=ssd, ucbt=ucbt if ucbt is not None else dict(ssd), entity=entity or {})


def kinds(b):
    return {m['new_code']: m['kind'] for m in b['mapping'] if 'new_code' in m}


class Proposal(unittest.TestCase):
    def test_pure_renumbering_is_one_to_one_only_with_mutual_flow_in_km_and_customers(self):
        prev = year({('c1', 'A'): 10., ('c2', 'A'): 10., ('c3', 'Z'): 80.}, entity={'A': ('ALFA', 2.), 'Z': ('ZETA', 8.)})
        cur = year({('c1', 'B'): 10., ('c2', 'B'): 10., ('c3', 'Z'): 80.}, entity={'B': ('ALFA', 2.), 'Z': ('ZETA', 8.)})
        b = conj_bridge.propose(1, 2024, prev, cur)
        self.assertEqual(kinds(b), {'B': 'one_to_one', 'Z': 'persisting_unchanged'})
        m = next(x for x in b['mapping'] if x.get('new_code') == 'B')
        self.assertTrue(m['name_equal']); self.assertEqual(m['best_old_code'], 'A')
        gone = next(x for x in b['mapping'] if x.get('kind') == 'gone')
        self.assertEqual((gone['old_code'], gone['name_continues_as']), ('A', ['B']))
        self.assertEqual(b['entering_units'], ['B']); self.assertEqual(b['overlap_units'], [])
        self.assertAlmostEqual(b['evidence']['coverage']['share_strong'], 1.)

    def test_equal_names_alone_never_make_a_one_to_one(self):
        prev = year({('c1', 'A'): 50., ('c2', 'A'): 50.}, entity={'A': ('ALFA', 2.)})
        cur = year({('c1', 'B'): 50., ('c2', 'C'): 50.}, entity={'B': ('ALFA', 1.), 'C': ('GAMA', 1.)})   # A was split; B keeps the name
        b = conj_bridge.propose(1, 2024, prev, cur)
        self.assertEqual(kinds(b)['B'], 'carved_from')
        m = next(x for x in b['mapping'] if x.get('new_code') == 'B')
        self.assertTrue(m['name_equal']); self.assertAlmostEqual(m['share_of_old_in_new'], .5)

    def test_merge_and_new_circuits_are_distinguished(self):
        prev = year({('c1', 'A'): 40., ('c2', 'B'): 40., ('c3', 'Z'): 20.})
        cur = year({('c1', 'M'): 40., ('c2', 'M'): 40., ('c3', 'Z'): 20., ('n1', 'N'): 10.})
        k = kinds(conj_bridge.propose(1, 2024, prev, cur))
        self.assertEqual((k['M'], k['N']), ('merge', 'new_circuits'))

    def test_persisting_code_with_changed_composition_is_flagged_and_quarantined(self):
        prev = year({('c1', 'A'): 90., ('c2', 'B'): 30., ('c4', 'B'): 100.})
        cur = year({('c1', 'A'): 90., ('c2', 'A'): 30., ('c4', 'B'): 100.})           # circuit c2 moved from B to A
        b = conj_bridge.propose(1, 2024, prev, cur)
        self.assertEqual(kinds(b)['A'], 'persisting_changed'); self.assertIn('A', b['overlap_units'])

    def test_low_circuit_continuity_means_insufficient_evidence(self):
        prev = year({('c1', 'A'): 100.})
        cur = year({('n1', 'B'): 60., ('n2', 'C'): 30., ('c1', 'A'): 10.})            # 90% of the stock in circuits that did not exist
        b = conj_bridge.propose(1, 2024, prev, cur)
        self.assertEqual(set(kinds(b).values()) - {'persisting_changed'}, {'insufficient_evidence'})
        self.assertLess(b['evidence']['coverage']['ctmt_continuity'], conj_bridge.MIN_CTMT_CONTINUITY)

    def test_predecessor_names_are_evidence_for_absorption_not_a_mapping(self):
        prev = year({('c1', 'A'): 100.})
        cur = year({('c1', 'A'): 100., ('n1', 'N'): 10.}, entity={'N': ('CAMPINA GRANDE', 1.)})
        b = conj_bridge.propose(1, 2023, prev, cur, predecessor_names={'CAMPINA GRANDE'})
        m = next(x for x in b['mapping'] if x.get('new_code') == 'N')
        self.assertTrue(m['name_in_predecessor']); self.assertEqual(m['kind'], 'new_circuits')

    def test_proposal_is_pending_without_decision_and_passes_the_bridge_schema(self):
        b = conj_bridge.propose(1, 2024, year({('c1', 'A'): 10.}), year({('c1', 'B'): 10.}))
        self.assertEqual((b['status'], b['decision'], b['kind']), ('PENDING_HOMOLOGATION', None, 'conjunto_redefinition'))
        bridges.validate(b)
        self.assertEqual(bridges.quarantine([b], 1, 2024, 'conjunto'), {'B': b['id']})
        self.assertEqual(bridges.quarantine([b], 1, 2024, 'municipality'), {})          # a conjunto bridge never quarantines municipal assets
        with self.assertRaises(ValueError):
            bridges.combine({'B': 1}, {'A': 1}, b)

    def test_a_mapping_that_is_not_a_list_is_rejected(self):
        b = conj_bridge.propose(1, 2024, year({('c1', 'A'): 10.}), year({('c1', 'B'): 10.}))
        b['mapping'] = {'A': 'B'}
        with self.assertRaises(ValueError):
            bridges.validate(b)

    def test_loading_the_top_folder_also_finds_the_conjunto_proposals_without_touching_municipal_units(self):
        loaded = bridges.load(ROOT / 'motor_v2/bridges')
        ids = {b['id'] for b in loaded}
        self.assertTrue({'EPB_EBO_2023', 'CONJ_26_2024'} <= ids)
        self.assertEqual(bridges.quarantine(loaded, 26, 2024, 'municipality'), {})
        self.assertIn('17306', bridges.quarantine(loaded, 26, 2024, 'conjunto'))
        self.assertIn('2504009', bridges.quarantine(loaded, 6600, 2023, 'municipality'))
        self.assertNotIn('2504009', bridges.quarantine(loaded, 6600, 2023, 'conjunto'))

    def test_real_proposals_are_versioned_pending_and_cover_the_eac_split(self):
        loaded = {b['id']: b for b in bridges.load(ROOT / 'motor_v2/bridges/conj')}
        self.assertEqual(set(loaded), {'CONJ_26_2024', 'CONJ_6585_2023', 'CONJ_6600_2023', 'CONJ_6600_2024'})
        for b in loaded.values():
            self.assertEqual((b['status'], b['decision']), ('PENDING_HOMOLOGATION', None))
        eac = loaded['CONJ_26_2024']
        self.assertEqual(eac['entering_units'], ['17306', '17307', '17308', '17309', '17310', '17311'])
        gone = {m['old_code']: m for m in eac['mapping'] if m.get('kind') == 'gone'}
        self.assertEqual(set(gone), {'12590', '12596', '12597'})
        self.assertAlmostEqual(gone['12590']['destinations_km']['17306'], .5836, places=3)       # TAQUARI was split, not merely renumbered
        self.assertGreater(len(gone['12590']['destinations_km']), 2)
        self.assertGreater(eac['evidence']['coverage']['ctmt_continuity'], .99)


class Plan2021(unittest.TestCase):
    def test_pit_clock_counts_packages_generated_before_their_own_year_end(self):
        rows = [dict(dist=26, year=2021, layout='V10', generation_stamp='2021-11-30'), dict(dist=26, year=2022, layout='V11', generation_stamp='2023-11-20'),
                dict(dist=1, year=2022, layout='V11', generation_stamp='2022-01-01')]
        c = plan_2021.pit_clock(rows, dists=(26,), first=2021, last=2025)
        self.assertEqual((c['competences'], c['generated_by_year_end']), (2, 1))

    def test_source_matrix_flags_duplicates_and_missing_items_without_inventing_sizes(self):
        rows = [dict(dist=6600, year=2021, competence='2021-12-31', layout='V10', generation_stamp='2022-07-25', item_id='a', title='t', tags_extra=False),
                dict(dist=6600, year=2021, competence='2021-12-31', layout='M10', generation_stamp='2024-01-19', item_id='b', title='t2', tags_extra=True)]
        m = plan_2021.source_matrix(rows)
        epb = [r for r in m if r['DIST'] == 6600]
        self.assertEqual([r['duplicatas_na_competencia'] for r in epb], [2, 2])
        self.assertTrue(all(r['status_local'] == 'NAO_BAIXADO' and r['tamanho_bytes'].startswith('DESCONHECIDO') for r in epb))
        self.assertTrue(any(r['status_local'] == 'AUSENTE_NO_CATALOGO' and r['DIST'] == 26 for r in m))
        self.assertEqual(epb[0]['url_derivada'], 'https://www.arcgis.com/sharing/rest/content/items/a/data')

    def test_plan_makes_no_guarantee_and_requires_approvals(self):
        text = json.dumps(plan_2021.RISKS, ensure_ascii=False) + json.dumps(plan_2021.STAGES, ensure_ascii=False)
        self.assertIn('não garante 3 backtests elegíveis', text)
        self.assertIn('aprovação para requisição HTTP', text)
        self.assertTrue(all(len(r) == 6 for r in plan_2021.RISKS))
        self.assertTrue(any(r[0] == 'ORIGENS' and r[2] == 'ALTA' for r in plan_2021.RISKS))

    @unittest.skipUnless(CATALOG.exists(), 'catalog snapshot not in this checkout')
    def test_real_catalog_matrix_matches_the_investigation(self):
        m = plan_2021.source_matrix(parse(CATALOG))
        got = {(r['DIST'], r['layout'], r['carimbo_geracao_titulo']) for r in m if r.get('item_id')}
        self.assertEqual(got, {(26, 'V10', '2022-04-01'), (6585, 'V10', '2022-06-30'), (6600, 'V10', '2022-07-25'), (6600, 'M10', '2024-01-19'),
                               (6611, 'V10', '2022-07-18'), (6612, 'V10', '2022-07-19')})
        clock = plan_2021.pit_clock(parse(CATALOG))
        self.assertEqual((clock['competences'], clock['generated_by_year_end']), (19, 0))


if __name__ == '__main__':
    unittest.main()
