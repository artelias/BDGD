"""Coverage matrix states and the power-metric release rules (synthetic data only; runs on Linux CI without the D: drive)."""
import json
import unittest

from motor_v2.nacional import cobertura as C
from motor_v2.nacional import potencia_b as P
from motor_v2.nacional import reguladores as R


def cell(y, estado='observado', valor='10', lacuna='', base=None, nao_somar='false', ruptura='false', motivo=''):
    return dict(ano=str(y), estado=estado, valor=valor, tipo_lacuna=lacuna, dataBase=base or f'{y}-12-31', nao_somar_em_agregados=nao_somar,
                ruptura_desde_ano_anterior=ruptura, intervalo_base='INTERVALO_ANUAL_COMPATIVEL', motivo_nd=motivo, metrica='quantidade',
                status_homologacao='COMPLETO_TECNICO', publicacao_id='x')


def contrato(d, c, estados):
    return {(d, c, y): e for y, e in zip(range(2022, 2026), estados)}


class Regulators(unittest.TestCase):
    def test_own_and_throughput_ratings(self):
        # 167 kVA single-phase at 13.8 kV line-to-line and 219 A: throughput 1,745 kVA, nameplate = own rating (~10 %)
        self.assertEqual(R.classificar(167, 13800, 219, 'AN')[0], 'PROPRIA')
        self.assertEqual(R.classificar(1670, 13800, 219, 'BN')[0], 'PASSANTE')
        self.assertEqual(R.classificar(500, 13800, 219, 'ABC')[0], 'PROPRIA')          # three-phase: sqrt(3) V I
        self.assertEqual(R.classificar(400, 13800, 219, 'AB')[0], 'PROPRIA')           # phase-phase: V I = 3,022 kVA, ratio 0.13
        self.assertEqual(R.classificar(1360, 13800, 219, 'AB')[0], 'INDETERMINADO')    # ratio 0.45: between the bands
        self.assertEqual(R.classificar(167, None, 219, 'AN'), ('INDETERMINADO', None))
        self.assertEqual(R.classificar(167, 13800, 219, 'XY'), ('INDETERMINADO', None))

    def test_convention_needs_coverage_and_dominance(self):
        self.assertEqual(R.convencao({'PROPRIA': 95, 'INDETERMINADO': 5})[0], 'PROPRIA')
        self.assertEqual(R.convencao({'PROPRIA': 80, 'INDETERMINADO': 20})[0], 'MISTA')        # < 90 % classified
        self.assertEqual(R.convencao({'PROPRIA': 90, 'PASSANTE': 10})[0], 'MISTA')             # < 95 % dominant
        self.assertEqual(R.convencao({})[0], 'SEM_REGISTROS')

    def test_released_series_keep_one_convention(self):
        lin = [dict(DIST=1, ano=y, convencao='PROPRIA', gate_potencia=True) for y in (2023, 2024, 2025)]
        lin += [dict(DIST=2, ano=2024, convencao='PROPRIA', gate_potencia=True), dict(DIST=2, ano=2025, convencao='PASSANTE', gate_potencia=True)]
        lin += [dict(DIST=3, ano=2025, convencao='PASSANTE', gate_potencia=True)]
        self.assertEqual(R.series_liberadas(lin), [(1, 'PROPRIA', [2023, 2024, 2025])])


class PowerRelease(unittest.TestCase):
    def test_tuc570_needs_gate_link_and_agreement(self):
        ct = {(7, 'trafo_forca', y): cell(y) for y in (2024, 2025)}
        audit = [dict(DIST='7', ano='2024', kva_aparente_eq='1000', kva_aparente_instalacao='1010', registros_auditados='10', gate_liberacao_experimental='True'),
                 dict(DIST='7', ano='2025', kva_aparente_eq='1500', kva_aparente_instalacao='1000', registros_auditados='11', gate_liberacao_experimental='True')]
        st = P.estoques_tuc570(audit, ct)
        self.assertTrue(st[7, 2024][1])
        self.assertFalse(st[7, 2025][1]); self.assertIn('EQ x UN divergem', st[7, 2025][2])

    def test_release_rule_two_competences_and_one_convention(self):
        stocks = {'trafo_forca_kva': {(1, 2024): (10.0, True, None, 1), (1, 2025): (11.0, True, None, 1), (2, 2025): (5.0, True, None, 1)},
                  'reguladores_kva_propria': {(3, 2024): (1.0, True, None, 1), (3, 2025): (1.0, True, None, 1)},
                  'reguladores_kva_passante': {(3, 2023): (9.0, True, None, 1), (4, 2024): (9.0, True, None, 1), (4, 2025): (9.0, True, None, 1)}}
        out = P.liberar(stocks)
        self.assertTrue(out['trafo_forca_kva'][1, 2025][1])
        self.assertIn('HISTORICO_INSUFICIENTE', out['trafo_forca_kva'][2, 2025][2])
        self.assertIn('SEM_SEMANTICA', out['reguladores_kva_propria'][3, 2025][2])
        self.assertTrue(out['reguladores_kva_passante'][4, 2025][1])

    def test_transition_gap_is_a_rupture(self):
        ct = {(1, 'trafo_forca', y): cell(y) for y in (2024, 2025)}
        st = {(1, 2024): (1000.0, True, None, 10), (1, 2025): (3000.0, True, None, 10)}      # kVA x3 with the same unit count
        c = P.celulas(st, ct, 'trafo_forca', True)
        self.assertTrue(c[1, 2025]['rupture'])
        st[1, 2025] = (1100.0, True, None, 11)
        self.assertFalse(P.celulas(st, ct, 'trafo_forca', True)[1, 2025]['rupture'])


class CoverageStates(unittest.TestCase):
    def test_blocked_combinations_get_a_specific_state(self):
        na = contrato(5, 'barramentos', [cell(y, 'nao_aplicavel', '', 'ATIVO_NAO_APLICAVEL') for y in range(2022, 2026)])
        self.assertEqual(C.classe_bloqueio(na, 5, 'barramentos', {}, {(5, 'barramentos'): 0})[:2], ('NAO_APLICAVEL', 'C'))
        # the contract says not applicable but the local entity has records: a defect, never hidden as NAO_APLICAVEL
        self.assertEqual(C.classe_bloqueio(na, 5, 'barramentos', {}, {(5, 'barramentos'): 3})[:2], ('BLOQUEIO_TECNICO', 'F'))
        suc = contrato(70, 'postes', [cell(y, 'nao_aplicavel', '', 'SUCESSAO_SOCIETARIA') for y in range(2022, 2026)])
        self.assertEqual(C.classe_bloqueio(suc, 70, 'postes', {70: 'reportado pela DIST 69'}, {})[:2], ('SUCESSAO_SOCIETARIA', 'B'))
        pub = contrato(8, 'postes', [cell(y, 'ausente', '', 'PUBLICACAO_NAO_LOCALIZADA') for y in range(2022, 2026)])
        self.assertEqual(C.classe_bloqueio(pub, 8, 'postes', {}, {})[:2], ('SEM_PUBLICACAO', 'A'))
        nh = contrato(9, 'postes', [cell(y, 'nao_homologado', '', 'BLOQUEIO_COMPETENCIA') for y in range(2022, 2026)])
        self.assertEqual(C.classe_bloqueio(nh, 9, 'postes', {}, {})[:2], ('DADO_NAO_HOMOLOGADO', 'D'))

    def test_incorporated_companies_are_successions(self):
        ct = {(6611, 'postes', 2022): cell(2022)}
        s = C.sucessoes(ct)
        self.assertIn(6611, s); self.assertIn('6600', s[6611])

    def test_projected_states_and_anchor(self):
        self.assertEqual(C._status_gerada(dict(ano_ancora='2025', base_da_projecao='melhor_modelo_experimental'))[0], 'PROJETADA_EXPERIMENTAL')
        self.assertEqual(C._status_gerada(dict(ano_ancora='2025', base_da_projecao='modelo_fallback'))[0], 'PROJETADA_BASELINE')
        st, cl, why = C._status_gerada(dict(ano_ancora='2023', base_da_projecao='modelo_fallback', horizonte_real='3..7 anos a partir de 2023'))
        self.assertEqual((st, cl), ('SEM_ANCORA_2025', 'E')); self.assertIn('2023', why)

    def test_power_state_uses_the_recorded_reasons(self):
        ct = contrato(4, 'trafo_forca', [cell(y) for y in range(2022, 2026)])
        ser = {(4, 'trafo_forca_kva'): dict(motivos=json.dumps({'2025': 'HISTORICO_INSUFICIENTE: 1 competencia(s) utilizavel(is) < 2 exigidas'}))}
        self.assertEqual(C.estado_potencia(ct, 4, 'trafo_forca', 'potencia_kva', {}, {}, ser, {})[0], 'HISTORICO_INSUFICIENTE')
        ct = contrato(4, 'reguladores', [cell(y) for y in range(2022, 2026)])
        from collections import Counter
        st = C.estado_potencia(ct, 4, 'reguladores', 'potencia_kva', {}, {}, {}, {4: Counter(MISTA=2, PROPRIA=2)})
        self.assertEqual(st[0], 'SEM_SEMANTICA_FISICA_HOMOGENEA')

    def test_states_are_the_documented_list(self):
        self.assertEqual(len(C.ESTADOS), 10)
        self.assertTrue(set(C.PROJETADOS) <= set(C.ESTADOS))


if __name__ == '__main__':
    unittest.main()
