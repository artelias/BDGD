"""Plausibility gate of the scenarios: synthetic cases (runs on Linux CI without the D: drive)."""
import math
import unittest

from motor_v2.nacional import plausibilidade as P

LIM = dict(up=.45, dn=-.2, p95=.25, p99=.45, p01=-.2, passo_up=.15, passo_dn=-.1, nivel='teste', n=500)
lg = math.log1p


def dec(lado, g, gm, A, h, anc=2025, nc=frozenset(), lim=LIM):
    return P.decidir(lado, g, gm, A, h, anc, set(nc), lim, {}, {}, 1, 'obj', {})


class Decisao(unittest.TestCase):
    def test_growth_inside_support_is_accepted(self):
        h = {2022: 1000., 2023: 1100., 2024: 1210., 2025: 1330.}
        r = dec('up', .2, .05, 1330., h)
        self.assertEqual(r['estado'], 'ACEITO'); self.assertEqual(r['g_pub'], .2)

    def test_first_entry_from_zero_is_blocked_as_cadastral_rupture(self):
        h = {2022: 0., 2023: 0., 2024: 0., 2025: 66.}
        g = lg(66) - lg(0)
        r = dec('up', g, 0., 66., h)
        self.assertEqual((r['estado'], r['classe']), ('BLOQUEADO', 'RUPTURA_CADASTRAL')); self.assertIsNone(r['g_pub'])

    def test_zero_anchor_blocks_extremes(self):
        r = dec('up', .3, 0., 0., {2022: 0., 2023: 0., 2024: 0., 2025: 0.})
        self.assertEqual((r['estado'], r['classe']), ('BLOQUEADO', 'HISTORICO_INSUFICIENTE'))

    def test_small_base_step_is_blocked(self):
        h = {2022: 40., 2023: 40., 2024: 3., 2025: 70.}      # 3 -> 70 on a tiny base, no sustained window
        g = lg(70) - lg(3)
        r = dec('up', g, 0., 70., h)
        self.assertEqual((r['estado'], r['classe']), ('BLOQUEADO', 'BASE_HISTORICA_PEQUENA'))

    def test_real_sustained_growth_is_kept_with_evidence_and_never_beyond_what_was_shown(self):
        h = {2022: 1000., 2023: 1700., 2024: 2900., 2025: 4900.}         # ~+55 %/yr, every step beyond the relevant step
        w = (lg(4900) - lg(1700)) / 2
        g = lg(4900) - lg(2900) + .5                                       # an extreme above the demonstrated rate
        r = dec('up', g, .1, 4900., h)
        self.assertEqual(r['classe'], 'PLAUSIVEL_COM_EVIDENCIA')
        self.assertIn(r['estado'], ('CORRIGIDO', 'ACEITO'))
        self.assertLessEqual(r['g_pub'], max(g, w) + 1e-9)
        if r['estado'] == 'CORRIGIDO':
            self.assertGreater(r['g_pub'], .45)                              # corrected to a demonstrated rate, not to an arbitrary cap
            self.assertAlmostEqual(r['g_pub'], (lg(4900) - lg(1000)) / 3, places=6)

    def test_cadastral_renumbering_year_is_not_comparable(self):
        h = {2022: 1000., 2023: 1000., 2024: 5200., 2025: 5300.}         # 2024 jump flagged non comparable by the engine
        g = lg(5200) - lg(1000)
        self.assertIsNone(P.janela_recente(h, 2025, {2024}, LIM, 'up'))
        r = dec('up', g, 0., 5300., h, nc={2024})
        self.assertEqual(r['estado'], 'BLOQUEADO')

    def test_sustained_decline_uses_the_downward_condition(self):
        h = {2022: 1000., 2023: 700., 2024: 480., 2025: 330.}            # about -35 %/yr
        w = P.janela_recente(h, 2025, set(), LIM, 'dn')
        self.assertIsNotNone(w); self.assertLess(w, 0)
        self.assertIsNone(P.janela_recente(h, 2025, set(), LIM, 'up'))   # a fall is never evidence of growth
        g = lg(330) - lg(480) - .6
        r = dec('dn', g, -.1, 330., h)
        self.assertEqual(r['classe'], 'PLAUSIVEL_COM_EVIDENCIA')

    def test_isolated_drop_is_not_sustained(self):
        h = {2022: 1000., 2023: 1000., 2024: 1010., 2025: 300.}
        r = dec('dn', lg(300) - lg(1010), 0., 300., h)
        self.assertEqual(r['estado'], 'BLOQUEADO')

    def test_degenerate_extreme_is_not_an_alert(self):
        r = dec('up', .05, .05, 100., {2022: 100., 2023: 105., 2024: 110., 2025: 100.})
        self.assertEqual(r['estado'], 'ACEITO'); self.assertEqual(r['severidade'], '')

    def test_neutral_growth_is_always_inside_the_support(self):
        lim = dict(LIM, up=0.0, dn=0.0)
        self.assertTrue(P.moderado_sustentado(0., lim, []))


class Calculo(unittest.TestCase):
    def raw(self, anc=2025, gm=.05, gc=-.02, ga=.2, a=100., conta=True):
        out = {'Moderado': [], 'Conservador': [], 'Agressivo': []}
        for y in P.YEARS:
            mod = a * math.exp(gm * (y - anc))
            for k, g in (('Conservador', gc), ('Moderado', gm), ('Agressivo', ga)):
                z = lg(mod) + (y - anc) * (g - gm)
                v = math.expm1(z)
                out[k].append(float(round(v)) if conta else v)
        # the moderate path is rounded first, as published
        return out

    def test_physical_rounding_is_not_a_calculation_error(self):
        r = self.raw(a=6., gm=-.076, ga=.56, gc=-.076)
        self.assertFalse(P.erro_de_calculo(r, -.076, -.076, .56, 2025, True))

    def test_true_calculation_error_is_detected(self):
        r = self.raw(a=1000., gm=.05, ga=.2)
        r['Agressivo'][4] *= 1.5
        self.assertTrue(P.erro_de_calculo(r, -.02, .05, .2, 2025, True))

    def test_unordered_scenarios_are_an_error(self):
        r = self.raw(a=1000.)
        r['Conservador'][2] = r['Agressivo'][2] + 5
        self.assertTrue(P.erro_de_calculo(r, -.02, .05, .2, 2025, True))

    def test_corrected_path_is_physical_and_ordered(self):
        mod = [float(round(1000 * math.exp(.05 * i))) for i in range(1, 6)]
        path = P.caminho(mod, 2025, .05, .3, True)
        self.assertTrue(all(float(x).is_integer() for x in path) and all(path[i] >= mod[i] for i in range(5)))
        cont = P.caminho([10.5] * 5, 2025, 0., .1, False)
        self.assertTrue(all(isinstance(x, float) for x in cont))


class Referencia(unittest.TestCase):
    def serie(self, o, unid, h, nc=()):
        return dict(o=o, m='m', unid=unid, h=h, nc=set(nc))

    def test_units_are_never_pooled_and_levels_fall_back(self):
        S = [self.serie('a', 'itens', {2022: 1000. * 1.02 ** i, 2023: 1000. * 1.02 ** (i + 1), 2024: 1000. * 1.02 ** (i + 2), 2025: 1000. * 1.02 ** (i + 3)}) for i in range(60)]
        S += [self.serie('b', 'km', {2022: 5000., 2023: 6000., 2024: 7200., 2025: 8640.}) for _ in range(60)]
        ref = P.Referencia(S)
        li = ref.limiar('itens', 'a', 'm', 1100.)
        lk = ref.limiar('km', 'b', 'm', 6000.)
        self.assertIsNotNone(li); self.assertIsNotNone(lk)
        self.assertLess(li['up'], .1); self.assertGreater(lk['up'], .15)         # km growth (+20 %) does not leak into quantities
        self.assertIsNone(ref.limiar('kVA', 'c', 'm', 100.))

    def test_non_comparable_transitions_do_not_enter_the_reference(self):
        h = {2022: 1000., 2023: 1000., 2024: 9000., 2025: 9100.}
        jan, passos = P.entradas_pool(h, {2024})
        self.assertTrue(all(g < .1 for _, g in passos)); self.assertEqual(jan, [])


if __name__ == '__main__':
    unittest.main()
