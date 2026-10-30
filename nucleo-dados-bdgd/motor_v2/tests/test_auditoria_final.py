"""Final audit of the national run: one eligibility policy (stock x transition), the v2 envelope screen, the experimental municipal
bridge gates, revision supersession and the power matrix (synthetic data only; no BDGD read)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import duckdb

from motor_v2.nacional import cenarios, elegibilidade as E, potencia, pontes, revisao_a


def cell(year, estado='observado', valor='10', intervalo='INTERVALO_ANUAL_COMPATIVEL', nao_somar='false', base=None, ruptura='false'):
    return dict(ano=str(year), estado=estado, valor=valor, intervalo_base=intervalo, nao_somar_em_agregados=nao_somar,
                dataBase=base or f'{year}-12-31', ruptura_desde_ano_anterior=ruptura, tipo_ruptura='', tipo_lacuna='')


class Eligibility(unittest.TestCase):
    def test_non_annual_interval_is_a_caveat_not_an_exclusion(self):
        ok, why, cav = E.estoque(cell(2025, intervalo='INTERVALO_NAO_ANUAL'))
        self.assertTrue(ok); self.assertIsNone(why); self.assertEqual(cav, ['intervalo_base_nao_anual'])
        self.assertFalse(E.legado_b(cell(2025, intervalo='INTERVALO_NAO_ANUAL')))   # what the first run did
        ok, why, cav = E.transicao(cell(2024), cell(2025, intervalo='INTERVALO_NAO_ANUAL'))
        self.assertTrue(ok); self.assertEqual(cav, ['intervalo_base_nao_anual'])

    def test_stock_rules(self):
        self.assertFalse(E.estoque(cell(2022, nao_somar='true'))[0])
        self.assertFalse(E.estoque(cell(2022, base='2022-11-30'))[0])
        self.assertFalse(E.estoque(cell(2022, estado='bloqueado'))[0])
        self.assertFalse(E.estoque(None)[0])
        self.assertTrue(E.estoque(cell(2022, estado='zero_verificado', valor='0'))[0])

    def test_succession_between_data_bases_is_not_a_transition(self):
        a, b = dict(cell(2022), dist='6600'), dict(cell(2023), dist='6600')
        with mock.patch.object(E, 'sucessoes', lambda: {(6600, 2023): 'EPB_EBO_2023'}):
            ok, why, _ = E.transicao(a, b)
            self.assertFalse(ok); self.assertIn('EPB_EBO_2023', why)
            self.assertTrue(E.transicao(a, b, sucessao=False)[0])
            self.assertTrue(E.transicao(dict(cell(2023), dist='6600'), dict(cell(2024), dist='6600'))[0])
            self.assertTrue(E.estoque(b)[0])          # the stock itself stays eligible

    def test_transition_rules(self):
        self.assertFalse(E.transicao(cell(2023), cell(2024, ruptura='true'))[0])
        self.assertFalse(E.transicao(cell(2022), cell(2024))[0])                    # not consecutive
        self.assertFalse(E.transicao(cell(2023, nao_somar='true'), cell(2024))[0])
        self.assertTrue(E.transicao(cell(2023), cell(2024))[0])


def table(series):
    return cenarios.screen_table_v2(series, {})


class EnvelopeScreenV2(unittest.TestCase):
    def setUp(self):
        # 12 companies growing ~2%/year (three size classes) and the series under test
        self.base = {d: {2022: 100. * d, 2023: 100. * d * 1.02, 2024: 100. * d * 1.0404, 2025: 100. * d * 1.0612} for d in range(1, 13)}

    def classes(self, pts, evid=None):
        t = table(dict(self.base, x=pts))
        return {c['ano']: c for c in cenarios.classify(pts, set(), t, evid)}

    def test_typical_kept(self):
        c = self.classes({2022: 500., 2023: 510., 2024: 520., 2025: 531.})
        self.assertTrue(all(x['classe'] == 'tipica' and x['no_envelope'] for x in c.values()))

    def test_isolated_step_reversal_persistent_and_unverifiable(self):
        c = self.classes({2022: 500., 2023: 800., 2024: 816., 2025: 832.})        # +60% then normal
        self.assertEqual(c[2023]['classe'], 'degrau_isolado'); self.assertFalse(c[2023]['no_envelope'])
        c = self.classes({2022: 500., 2023: 800., 2024: 500., 2025: 510.})        # +60% then back
        self.assertEqual(c[2023]['classe'], 'reversao'); self.assertFalse(c[2023]['no_envelope'])
        c = self.classes({2022: 500., 2023: 800., 2024: 1280., 2025: 1300.})      # +60% twice: structural, kept
        self.assertEqual(c[2023]['classe'], 'persistente'); self.assertTrue(c[2023]['no_envelope'])
        c = self.classes({2022: 500., 2023: 510., 2024: 520., 2025: 900.})        # last step: cannot be verified
        self.assertEqual(c[2025]['classe'], 'sem_ano_seguinte'); self.assertTrue(c[2025]['nao_verificavel'])
        kept, _ = cenarios.screened_growth_v2({2022: 500., 2023: 510., 2024: 520., 2025: 900.}, set(), table(dict(self.base, x={})), incluir_nao_verificaveis=True)
        self.assertEqual(len(kept), 3)

    def test_documented_evidence_comes_first(self):
        pts = {2022: 500., 2023: 800., 2024: 816., 2025: 832.}
        c = self.classes(pts, {2023: dict(categoria='variacao_real_plausivel')})
        self.assertEqual(c[2023]['classe'], 'evidencia_variacao_real'); self.assertTrue(c[2023]['no_envelope'])
        c = self.classes({2022: 500., 2023: 510., 2024: 520., 2025: 531.}, {2024: dict(categoria='alteracao_cadastral')})
        self.assertEqual(c[2024]['classe'], 'evidencia_nao_fisica'); self.assertFalse(c[2024]['no_envelope'])

    def test_reference_is_the_size_class(self):
        # small companies grow 30%/year, large ones 1%: a small series growing 30% is typical for ITS class
        s = {d: {2022: 10. + d, 2023: (10. + d) * 1.3, 2024: (10. + d) * 1.69} for d in range(6)}
        s.update({d: {2022: 1e4 * d, 2023: 1e4 * d * 1.01, 2024: 1e4 * d * 1.0201} for d in range(6, 18)})
        t = table(s)
        c = cenarios.classify({2022: 12., 2023: 15.6, 2024: 20.3}, set(), t)
        self.assertTrue(all(x['classe'] == 'tipica' for x in c))

    def test_moderate_path_never_changes(self):
        mod = {y: 100. * 1.02 ** (y - 2025) for y in cenarios.YEARS}
        sc, _ = cenarios.scenarios(2025, 100., mod, [-.5, .9])
        for y in cenarios.YEARS:      # recomputed through log1p/expm1: equal up to floating point
            self.assertAlmostEqual(sc['Moderado'][y], mod[y], places=9)


class BridgeGates(unittest.TestCase):
    def build(self, root, year_codes):
        for y, codes in year_codes.items():
            d = root / '7' / 'ucbt_quantidade' / str(y); d.mkdir(parents=True)
            con = duckdb.connect()
            con.execute('CREATE TABLE t(MUN VARCHAR, CONJ VARCHAR, CTMT VARCHAR, ARE_LOC VARCHAR, clientes_ativos BIGINT, energia_denominador BIGINT, energia_kwh DOUBLE)')
            con.executemany('INSERT INTO t VALUES (?, ?, ?, ?, ?, ?, ?)', [(c, 'C' + c[-1], 'M1', 'UB', n, n, 10. * n) for c, n in codes])
            con.execute(f"COPY t TO '{(d / 'territorial.parquet').as_posix()}' (FORMAT PARQUET)"); con.close()
            (d / 'checkpoint.json').write_text(json.dumps(dict(output_sha256='x')), encoding='utf-8')

    def test_gates_pass_and_original_is_preserved(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self.build(root, {2022: [('4200051', 10), ('4200101', 20)], 2023: [('0420005', 11), ('0420010', 21)], 2024: [('4200051', 12), ('4200101', 22)]})
            ref = {'4200051', '4200101'}
            with mock.patch.object(pontes, 'PANEL', root):
                ok, gates, written = pontes.check_and_write('B', 7, 2023, {'0420005': '4200051', '0420010': '4200101'}, ref)
                self.assertTrue(ok, gates); self.assertTrue(gates['ucbt_quantidade']['totais_preservados'])
                self.assertEqual(gates['ucbt_quantidade']['linhas_alteradas'], 2); self.assertEqual(len(written), 1)
                self.assertTrue((root / '_originais_ponte' / 'B' / '7' / 'ucbt_quantidade' / '2023' / 'territorial.parquet').exists())
                mun = {r[0] for r in duckdb.connect().execute('SELECT MUN FROM read_parquet(?)', [str(root / '7/ucbt_quantidade/2023/territorial.parquet')]).fetchall()}
                self.assertEqual(mun, ref)
                # a second application is a no-op: the codes are already official, nothing is rewritten
                ok2, gates2, written2 = pontes.check_and_write('B', 7, 2023, {'0420005': '4200051', '0420010': '4200101'}, ref)
                self.assertTrue(ok2); self.assertEqual(written2, []); self.assertFalse(gates2['ucbt_quantidade']['aplicavel'])

    def test_collision_or_invalid_target_blocks(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self.build(root, {2022: [('4200051', 10)], 2023: [('0420005', 11), ('4200051', 3)], 2024: [('4200051', 12)]})
            with mock.patch.object(pontes, 'PANEL', root):
                ok, gates, written = pontes.check_and_write('B', 7, 2023, {'0420005': '4200051'}, {'4200051'})
                self.assertFalse(ok); self.assertEqual(gates['ucbt_quantidade']['colisoes'], 1); self.assertEqual(written, [])
                ok, gates, _ = pontes.check_and_write('B', 7, 2023, {'0420005': '9999999'}, {'4200051'}, dry=True)
                self.assertFalse(ok); self.assertFalse(gates['codigos_ibge_validos'])


class Revisions(unittest.TestCase):
    def test_revision_batch_supersedes_only_its_dist(self):
        st = dict(lotes={'u-01': dict(ativo='a', estado='completed', dists=[1, 2, 3], output='o1'),
                         'u-rev-1': dict(ativo='a', estado='completed', dists=[2], output='o2', revisao='r'),
                         'u-rev-2': dict(ativo='a', estado='failed', dists=[3], output='o3', revisao='r')})
        v = revisao_a.vigentes(st, 'a')
        self.assertEqual(v[1][0], 'u-01'); self.assertEqual(v[2][0], 'u-rev-1'); self.assertEqual(v[3][0], 'u-01')


class PowerMatrix(unittest.TestCase):
    def test_semantics_and_status(self):
        def r(fam, d, y, kva, gate=True, nopow=0, n=10):
            return dict(familia=fam, DIST=d, ano=y, registros_auditados=n, sem_campo_potencia=nopow, cod_potencia_valido=n - nopow,
                        gate_liberacao_experimental=gate, quantidade_confere_contrato=True, kva_aparente_eq=kva, kva_aparente_instalacao=kva)
        rows = [r('trafo_dist_565', 1, y, 100.) for y in (2024, 2025)] + [r('trafo_forca_570', 1, y, 50.) for y in (2024, 2025)] + \
               [r('trafo_medida_575', 1, y, 0., gate=False, nopow=10) for y in (2024, 2025)] + [r('reguladores', 1, y, 500.) for y in (2024, 2025)]
        with mock.patch.object(potencia, 'plausibility', lambda rows: dict(soma_reguladores_2025=500., soma_trafo_dist_2025=100., soma_trafo_forca_2025=50., quantis_kva_2025=[1, 2, 3])):
            m = {x['familia']: x for x in potencia.summarize(rows)}
        self.assertEqual(m['trafo_forca_570']['status'], 'liberacao_experimental_proposta'); self.assertEqual(m['trafo_forca_570']['grandeza'], 'aparente')
        self.assertEqual(m['trafo_medida_575']['status'], 'nao_aplicavel')
        self.assertEqual(m['reguladores']['status'], 'bloqueado_semantica_nao_homogenea')
        self.assertEqual(m['bancos_capacitores']['grandeza'], 'reativa'); self.assertEqual(m['geradores']['unidade'], 'kW')
        self.assertTrue(all('nenhuma' in x['conversao'] for x in m.values()))


class PartialTotals(unittest.TestCase):
    def test_total_is_complete_only_with_every_eligible_dist(self):
        from motor_v2.nacional.consolidar import totals
        proj = [dict(DIST=d, ativo='x', metrica='q', unidade='u', ano='2030', cenario='Moderado', valor=v) for d, v in (('1', 10.), ('2', 30.))]
        ok = {('1', 'x', 'q'), ('2', 'x', 'q')}
        t = totals(proj, ('DIST', 'ativo', 'metrica'), ok, ('ativo', 'metrica', 'unidade'), {('x', 'q'): {'1': 10., '2': 30.}})[0]
        self.assertEqual(t['status_total'], 'COMPLETO'); self.assertEqual(t['cobertura_estoque_2025'], 1.)
        t = totals(proj, ('DIST', 'ativo', 'metrica'), {('2', 'x', 'q')}, ('ativo', 'metrica', 'unidade'), {('x', 'q'): {'1': 10., '2': 30.}})[0]
        self.assertEqual(t['status_total'], 'PARCIAL'); self.assertAlmostEqual(t['cobertura_estoque_2025'], .75); self.assertEqual(t['dist_fora'], '1')
        t = totals(proj, ('DIST', 'ativo', 'metrica'), ok, ('ativo', 'metrica', 'unidade'), {('x', 'q'): {'1': 10., '2': 30., '3': None}})[0]
        self.assertEqual(t['status_total'], 'PARCIAL'); self.assertIsNone(t['cobertura_estoque_2025'])


class PublicVerifier(unittest.TestCase):
    def test_only_baseline_changes_are_preexisting(self):
        from motor_v2.nacional.verificacoes import classify_public_changes
        base = dict(alteracoes=[dict(caminho='n/web/a.ts', status_git=' M', sha256_arquivo='h1')])
        sha = {'n/web/a.ts': 'h1', 'n/web/b.json': 'h2', 'n/output-publicavel/x.csv': 'h3'}.get
        pre, run = classify_public_changes([' M n/web/a.ts'], base, sha)
        self.assertEqual(len(pre), 1); self.assertEqual(run, [])
        pre, run = classify_public_changes([' M n/web/a.ts'], base, {'n/web/a.ts': 'outro'}.get)       # same path, new content
        self.assertEqual(pre, []); self.assertEqual(len(run), 1)
        pre, run = classify_public_changes([' M n/web/a.ts', '?? n/web/b.json', ' D n/output-publicavel/x.csv'], base, sha)
        self.assertEqual({x['caminho'] for x in run}, {'n/web/b.json', 'n/output-publicavel/x.csv'})
        pre, run = classify_public_changes([], base, sha)
        self.assertEqual((pre, run), ([], []))


if __name__ == '__main__':
    unittest.main()
