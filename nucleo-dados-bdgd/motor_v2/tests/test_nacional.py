"""National run: choice policy, scenarios, Level B pools, national scopes, quarantine, municipal bridge and ZIP classification
(synthetic data only; no BDGD read)."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from motor_v2 import convert_zips
from motor_v2.comparison import comparable, scope_pool
from motor_v2.nacional import cenarios, distribuidora as B, selecao


def cand(kind, per, keys=frozenset({'k'}), fb=None):
    m = dict(n=10, origens=len(per), mae=sum(per.values()) / len(per), rmse=1., vies=0., wape=.1, mae_por_origem=per,
             robusto=sum(per.values()) / len(per) + (max(per.values()) - min(per.values())) / 2)
    return dict(kind=kind, keys=set(keys), m=m, fallback_share=fb)


class Choice(unittest.TestCase):
    def test_stable_ml_is_experimental_never_homologated(self):
        d = selecao.choose({'persistencia': cand('baseline', {'2023': 10, '2024': 10}), 'deriva': cand('baseline', {'2023': 9, '2024': 9.5}),
                            'ridge:comparaveis': cand('ml', {'2023': 6, '2024': 7})})
        self.assertEqual(d['melhor_modelo_experimental'], 'ridge:comparaveis')
        self.assertEqual(d['melhor_baseline'], 'deriva'); self.assertEqual(d['modelo_fallback'], 'deriva')
        self.assertIsNone(d['modelo_homologado']); self.assertIn('2 origem', d['motivo_nao_homologado'])
        self.assertFalse(d['persistencia_superior_empiricamente'])

    def test_ml_worse_in_one_origin_is_not_chosen(self):
        # with two origins the robust score is the larger per-origin MAE: 9.4 < 10, yet worse than persistence in 2024 (9.4 > 5)
        d = selecao.choose({'persistencia': cand('baseline', {'2023': 10, '2024': 5}), 'ols:individual': cand('ml', {'2023': 9, '2024': 9.4})})
        self.assertIsNone(d['melhor_modelo_experimental']); self.assertEqual(d['modelo_projecao'], 'persistencia')
        self.assertIn('instavel', d['motivo_experimental'])

    def test_persistence_by_policy_is_not_an_empirical_win(self):
        d = selecao.choose({})
        self.assertEqual(d['modelo_projecao'], 'persistencia'); self.assertFalse(d['persistencia_superior_empiricamente'])
        self.assertIn('politica', d['motivo_fallback'])
        d = selecao.choose({'persistencia': cand('baseline', {'2023': 1, '2024': 1}), 'rf:x': cand('ml', {'2023': 3, '2024': 3})})
        self.assertTrue(d['persistencia_superior_empiricamente'])

    def test_candidate_on_other_test_keys_is_not_compared(self):
        d = selecao.choose({'persistencia': cand('baseline', {'2023': 10, '2024': 10}), 'ols:x': cand('ml', {'2023': 1, '2024': 1}, keys={'outro'})})
        self.assertIsNone(d['melhor_ml'])

    def test_single_origin_is_never_stable(self):
        d = selecao.choose({'persistencia': cand('baseline', {'2024': 10}), 'ols:x': cand('ml', {'2024': 1})})
        self.assertIsNone(d['melhor_modelo_experimental']); self.assertIn('1 origem', d['motivo_experimental'])


class Scenarios(unittest.TestCase):
    def test_order_and_degenerate_case(self):
        mod = {y: 100. * 1.02 ** (y - 2025) for y in cenarios.YEARS}
        sc, meta = cenarios.scenarios(2025, 100., mod, [-0.01, 0.05])
        for y in cenarios.YEARS:
            self.assertLessEqual(sc['Conservador'][y], sc['Moderado'][y]); self.assertLessEqual(sc['Moderado'][y], sc['Agressivo'][y])
        self.assertAlmostEqual(sc['Moderado'][2030], mod[2030])
        sc, meta = cenarios.scenarios(2025, 100., {y: 100. for y in cenarios.YEARS}, [])
        self.assertTrue(meta['cenarios_degenerados']); self.assertEqual(sc['Conservador'], sc['Agressivo'])

    def test_baseline_paths_and_fallbacks(self):
        p, why = cenarios.baseline_path('deriva', [(2023, 10.), (2025, 14.)], 2025)
        self.assertAlmostEqual(p[2026], 16.); self.assertIsNone(why)
        p, why = cenarios.baseline_path('cagr', [(2024, 0.), (2025, 5.)], 2025)
        self.assertEqual((p[2030], why), (5., 'nonpositive_endpoint'))
        p, why = cenarios.baseline_path('deriva', [(2024, 10.), (2025, 2.)], 2025)
        self.assertEqual(why, 'negative_forecast'); self.assertEqual(p[2030], 2.)

    def test_ml_path_repeats_the_one_step_change(self):
        p = cenarios.ml_path(99., 109., 2025)
        self.assertAlmostEqual(p[2026], 109.); self.assertAlmostEqual(p[2027], 100 * 1.21 - 1, places=6)


class LevelB(unittest.TestCase):
    def setUp(self):
        def cell(v, ok=True, rup=False):
            return dict(value=v, usable=ok, rupture=rup)
        self.cells = {(1, 'c', 2022): cell(10.), (1, 'c', 2023): cell(11.), (1, 'c', 2024): cell(12., rup=True), (1, 'c', 2025): cell(13.),
                      (2, 'c', 2022): cell(5.), (2, 'c', 2023): cell(None, ok=False)}

    def test_comparable_transitions_respect_rupture_and_usability(self):
        self.assertTrue(B.comparable(self.cells, 1, 'c', 2023)); self.assertFalse(B.comparable(self.cells, 1, 'c', 2024))
        self.assertTrue(B.comparable(self.cells, 1, 'c', 2025)); self.assertFalse(B.comparable(self.cells, 2, 'c', 2023))
        self.assertEqual(B.segment(self.cells, 1, 'c', 2025), [(2024, 12.), (2025, 13.)])

    def test_one_step_baselines(self):
        self.assertEqual(B.one_step('persistencia', [(2024, 12.)]), (12., None))
        self.assertEqual(B.one_step('deriva', [(2024, 12.)]), (12., 'short_series'))
        self.assertAlmostEqual(B.one_step('cagr', [(2023, 100.), (2024, 121.)])[0], 121 * 1.21)

    def test_group_pool_needs_a_confirmed_group_with_two_companies(self):
        rows = [dict(dist=d, concept='c', year=2023, x=[1., 1., None, None], y=1., stock=1.) for d in (1, 2, 3)]
        tr, why = B.pool(rows, 'c', 1, 2023, 'grupo_economico', {1: 'g', 2: 'g'}, rows[0])
        self.assertIsNone(why); self.assertEqual({r['dist'] for r in tr}, {1, 2})
        self.assertEqual(B.pool(rows, 'c', 3, 2023, 'grupo_economico', {1: 'g', 2: 'g'}, rows[2])[1], 'controle nao confirmado')

    def test_pool_never_uses_rows_after_the_origin(self):
        rows = [dict(dist=d, concept='c', year=y, x=[1., 1., None, None], y=1., stock=1.) for d in (1, 2) for y in (2023, 2024, 2025)]
        tr, _ = B.pool(rows, 'c', 1, 2023, 'comparaveis', {}, rows[0])
        self.assertEqual({r['year'] for r in tr}, {2023})


def prow(dist, group, grupo, stock, year=2023, future=False):
    return dict(dist=dist, group=group, grupo=grupo, year=year, feature_year=year - 1, feature_available='2022-12-31', feature_revision_available='2022-12-31',
                target_available='2023-12-31', rupture=False, x=[stock, None, None], y=None if future else stock, future=future)


class NationalScopes(unittest.TestCase):
    ROWS = [prow(d, f'm{d}{i}', g, s) for d, g, s in ((1, 'G', 1.), (2, 'G', 1.2), (3, 'H', 5.), (4, 'nao_confirmado', 1.1), (5, 'G', 9.), (6, 'H', 1.05))
            for i in range(2)]

    def test_economic_group_scope(self):
        tr, peers = scope_pool(self.ROWS, 1, 2023, 'reconciled_retrospective', 'grupo_economico', set())
        self.assertEqual(peers, [1, 2, 5])
        self.assertEqual(scope_pool(self.ROWS, 4, 2023, 'reconciled_retrospective', 'grupo_economico', set()), ([], []))

    def test_comparable_scope_is_self_plus_k_nearest(self):
        peers = comparable([r for r in self.ROWS], 1, k=2)
        self.assertIn(1, peers); self.assertEqual(len(peers), 3); self.assertNotIn(5, peers)

    def test_future_rows_never_enter_a_pool(self):
        rows = self.ROWS + [prow(1, 'm1x', 'G', 1., year=2023, future=True)]
        for scope in ('individual', 'grupo_economico', 'comparaveis'):
            tr, _ = scope_pool(rows, 1, 2023, 'reconciled_retrospective', scope, set())
            self.assertFalse(any(r.get('future') for r in tr))


class ZipClassification(unittest.TestCase):
    def test_base_decides_the_competence(self):
        with mock.patch.object(convert_zips, 'ordinary_counts', return_value=('ITEM', {'UCBT': 10, 'SSDMT': 5})):
            k, y, _ = convert_zips.classify(2023, 1, {'DAT_INC': '01/01/2024', 'DAT_FNL': '31/12/2024'}, {'UCBT': 10, 'SSDMT': 5})
            self.assertEqual((k, y), ('duplicata_da_competencia_2024', 2024))
            k, _, _ = convert_zips.classify(2023, 1, {'DAT_INC': '01/01/2024', 'DAT_FNL': '31/12/2024'}, {'UCBT': 11, 'SSDMT': 5})
            self.assertEqual(k, 'competencia_divergente_2024')
        self.assertEqual(convert_zips.classify(2022, 1, {'DAT_INC': '01/01/2022', 'DAT_FNL': '30/11/2022'}, {})[0], 'competencia_confirmada_data_base_divergente')
        self.assertEqual(convert_zips.classify(2022, 1, {'DAT_INC': '06/03/2024', 'DAT_FNL': '06/03/2024'}, {})[0], 'competencia_indeterminada')
        self.assertEqual(convert_zips.classify(2022, 1, {'DAT_INC': '01/01/2022', 'DAT_FNL': '31/12/2022'}, {})[0], 'competencia_confirmada')


class MunicipalBridge(unittest.TestCase):
    def test_zero_plus_six_digit_codes_are_proposed_but_left_pending(self):
        import pyarrow as pa, pyarrow.parquet as pq
        from motor_v2.nacional import municipios
        ref = {'4209102': dict(nome='Joinville', uf='SC'), '4205407': dict(nome='Florianopolis', uf='SC')}
        with tempfile.TemporaryDirectory() as t:
            for y, codes in ((2022, ('4209102', '4205407')), (2023, ('0420910', '0420540')), (2024, ('4209102', '4205407'))):
                d = Path(t) / '9' / 'ucbt_quantidade' / str(y); d.mkdir(parents=True)
                pq.write_table(pa.Table.from_pylist([dict(MUN=c, CONJ=f'C{i}', clientes_ativos=100 + i) for i, c in enumerate(codes)]), d / 'territorial.parquet')
            scan = municipios.scan(t, [9], ref)
            self.assertEqual([r['share_fora_ibge'] for r in scan], [0., 1., 0.])
            p = municipios.propose(t, 9, 2023, ref)
            self.assertEqual({m['codigo_publicado']: m['candidato_ibge'] for m in p['mapeamento']}, {'0420910': '4209102', '0420540': '4205407'})
            self.assertTrue(p['evidencia_suficiente_para_proposta']); self.assertEqual(p['status'], 'PENDENTE_HOMOLOGACAO'); self.assertIsNone(p['decisao'])


if __name__ == '__main__':
    unittest.main()
