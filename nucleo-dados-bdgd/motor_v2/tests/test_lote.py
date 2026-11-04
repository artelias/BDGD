"""Inventory classification, extraordinary isolation, batch scopes and the snapshot feature (synthetic; no BDGD read)."""
import tempfile
import unittest
from pathlib import Path

from motor_v2 import extraordinary as ex
from motor_v2.comparison import scope_pool
from motor_v2.features import FEATURES, attach_snapshot_features
from motor_v2.inventory import classify


def item(dist, ano, item_id, ents, sha='s'):
    return dict(ano=ano, dist=dist, item_id=item_id, entidades=ents, source_sha=sha, base=None, origem='parquet_2022_2024')


class InventoryClassification(unittest.TestCase):
    def setUp(self):
        self.sel = {('10', 2023): dict(items={'A'}, status={}, ruptura=0)}
        self.pubs = {k: dict(data_base='2023-12-31', publicado_em='2025-10-08T00:00:00', atualizado_em='2025-10-09T00:00:00') for k in 'ABCD'}

    def test_contract_item_is_ordinary_and_other_versions_are_extraordinary(self):
        rows = classify([item('10', 2023, 'A', {'UCBT': 100}), item('10', 2023, 'B', {'UCBT': 104}, 't'),
                         item('10', 2023, 'C', {'UCBT': 100})], self.sel, self.pubs)
        by = {r['item_id']: r for r in rows}
        self.assertEqual((by['A']['natureza'], by['A']['nova_observacao_temporal']), ('ordinaria', True))
        self.assertEqual((by['B']['tipo'], by['B']['nova_observacao_temporal']), ('versao_alternativa_mesma_competencia', False))
        self.assertEqual(by['B']['delta_vs_ordinaria'], {'UCBT': 4})
        self.assertEqual(by['C']['tipo'], 'duplicata_da_ordinaria')            # same counts and same source checksum
        self.assertEqual(by['A']['disponivel_em'], '2025-10-09')                 # availability = latest of publication/revision

    def test_item_of_an_uncovered_competence_is_a_new_extraordinary_observation(self):
        rows = classify([item('10', 2021, 'D', {'UCBT': 90})], self.sel, self.pubs)
        self.assertEqual((rows[0]['natureza'], rows[0]['tipo'], rows[0]['nova_observacao_temporal']), ('extraordinaria', 'fora_do_contrato', True))


def prov(item_id, natureza, competencia=2023, dist='10', disp='2025-10-08'):
    return ex.Provenance(item_id=item_id, dist=dist, competencia=competencia, data_base=f'{competencia}-12-31', disponivel_em=disp,
                         versao='V11', natureza=natureza, tipo='t', qualidade='candidato', origem='parquet')


class ExtraordinaryIsolation(unittest.TestCase):
    def setUp(self):
        self.inv = {'A': prov('A', ex.ORDINARY), 'B': prov('B', ex.EXTRAORDINARY), 'N': prov('N', ex.EXTRAORDINARY, competencia=2021),
                    'U': prov('U', ex.EXTRAORDINARY, competencia=None, dist='')}

    def test_public_products_accept_ordinary_items_only(self):
        self.assertTrue(ex.assert_public_safe({'A'}, self.inv))
        with self.assertRaises(ex.IsolationError):
            ex.assert_public_safe({'A', 'B'}, self.inv)
        with self.assertRaises(ex.IsolationError):
            ex.assert_public_safe({'desconhecido'}, self.inv)                      # unknown is refused, not assumed ordinary

    def test_research_outputs_never_go_under_a_public_root(self):
        with self.assertRaises(ex.IsolationError):
            ex.research_path(ex.ROOT / 'web/public/data/previsoes/x.json')
        with self.assertRaises(ex.IsolationError):
            ex.research_path(ex.ROOT / 'output-historico/contrato-integracao/x.csv')
        with self.assertRaises(ex.IsolationError):
            ex.research_path(Path(tempfile.gettempdir()) / 'x.csv')                # outside the research root
        self.assertTrue(str(ex.research_path(ex.RESEARCH_ROOT / 'lote/x.csv')).endswith('x.csv'))

    def test_no_retroactive_use_before_availability(self):
        self.assertFalse(ex.usable_at(self.inv['B'], '2025-10-07'))
        self.assertTrue(ex.usable_at(self.inv['B'], '2025-10-08'))
        self.assertFalse(ex.usable_at(prov('X', ex.EXTRAORDINARY, disp=''), '2030-01-01'))

    def test_second_version_of_a_covered_competence_is_sensitivity_only(self):
        self.assertEqual(ex.training_role(self.inv['B'], self.inv), ex.SENSITIVITY)
        self.assertEqual(ex.training_role(self.inv['N'], self.inv), ex.NEW_TEMPORAL)
        self.assertEqual(ex.training_role(self.inv['U'], self.inv), ex.UNUSABLE)
        self.assertTrue(all(not r['publico'] for r in ex.plan(self.inv)))

    @unittest.skipUnless(Path('D:/NUCLEO_BDGD_2025/motor_v2/inventario_v2/INVENTARIO_PUBLICACOES_LOCAIS.csv').exists(), 'inventário local não gerado')
    def test_real_national_contract_references_ordinary_items_only(self):
        inv = ex.load('D:/NUCLEO_BDGD_2025/motor_v2/inventario_v2/INVENTARIO_PUBLICACOES_LOCAIS.csv')
        self.assertTrue(ex.assert_contract_ordinary(ex.ROOT / 'output-historico/contrato-integracao/serie_fisica_nacional.csv', inv))


def row(dist, group, grupo, x0=1.0):
    return dict(dist=dist, group=group, grupo=grupo, year=2023, feature_year=2022, feature_available='2022-12-31',
                feature_revision_available='2022-12-31', target_available='2023-12-31', rupture=False, x=[x0, None, None])


class BatchScopes(unittest.TestCase):
    ROWS = [row(1, 'm1', 'G'), row(2, 'm2', 'G', 1.1), row(3, 'm3', 'H', 5.0), row(4, 'm4', 'nao_confirmado', 1.2), row(5, 'm5', 'G', 9.0)]

    def test_group_scope_pools_only_the_same_economic_group(self):
        train, peers = scope_pool(self.ROWS, 1, 2023, 'reconciled_retrospective', 'group_lote', set())
        self.assertEqual(peers, [1, 2, 5]); self.assertEqual({r['dist'] for r in train}, {1, 2, 5})

    def test_group_scope_is_empty_without_peers_or_without_a_confirmed_group(self):
        self.assertEqual(scope_pool(self.ROWS, 3, 2023, 'reconciled_retrospective', 'group_lote', set()), ([], []))
        self.assertEqual(scope_pool(self.ROWS, 4, 2023, 'reconciled_retrospective', 'group_lote', set()), ([], []))

    def test_global_and_peer_scopes(self):
        _, peers = scope_pool(self.ROWS, 1, 2023, 'reconciled_retrospective', 'shared_lote', set())
        self.assertEqual(peers, [1, 2, 3, 4, 5])
        _, peers = scope_pool(self.ROWS, 1, 2023, 'reconciled_retrospective', 'peers_lote', set())
        self.assertEqual(peers, [2, 4, 3])                                         # three nearest on training stock, excluding itself

    def test_held_out_territories_never_enter_any_pool(self):
        for scope in ('shared_lote', 'group_lote', 'peers_lote', 'individual'):
            train, _ = scope_pool(self.ROWS, 1, 2023, 'reconciled_retrospective', scope, {'m2'})
            self.assertNotIn('m2', {r['group'] for r in train})


class SnapshotFeature(unittest.TestCase):
    def test_recent_connection_share_sits_at_its_index_with_t_minus_1_metadata(self):
        r = dict(row(1, 'm1', 'G'), recent_connection_share=0.12, feature_available='2025-10-08')
        out = attach_snapshot_features([r, dict(row(1, 'm2', 'G'))])
        i = FEATURES.index('recent_connection_share')
        self.assertEqual(len(out[0]['x']), len(FEATURES)); self.assertEqual(out[0]['x'][i], 0.12)
        self.assertEqual(out[0]['feature_meta']['recent_connection_share']['reference_year'], 2022)   # the t-1 snapshot, never the target year
        self.assertIsNone(out[1]['x'][i]); self.assertNotIn('recent_connection_share', out[1]['feature_meta'])

    def test_feature_is_last_so_external_and_shared_indices_are_unchanged(self):
        self.assertEqual(FEATURES[-1], 'recent_connection_share')
        self.assertEqual(FEATURES[:3], ('log_stock', 'urban_share', 'log_energy_per_client'))


if __name__ == '__main__':
    unittest.main()
