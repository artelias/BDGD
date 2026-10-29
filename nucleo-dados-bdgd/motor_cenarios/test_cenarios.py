"""Testes do motor de cenários: sem vazamento temporal, mesmos pontos para todos os modelos, cenários coerentes."""
import math
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import cenarios as C  # noqa: E402


def painel(n=40, seed=1, ruptura_em=None):
    rnd = random.Random(seed)
    series = {("x", "quantidade"): {}, ("consumidores", "quantidade"): {}}
    fi = {}
    for i in range(n):
        d = str(100 + i)
        g = 0.01 + 0.04 * rnd.random()
        y0 = 1000 * (1 + 9 * rnd.random())
        series[("x", "quantidade")][d] = {a: ("observado", y0 * (1 + g) ** (a - 2022), ruptura_em == a) for a in C.ANOS}
        series[("consumidores", "quantidade")][d] = {a: ("observado", 50 * y0 * (1 + g / 2) ** (a - 2022), False) for a in C.ANOS}
        for a in C.ANOS:
            fi[(a, d)] = {"int_ln_uc": math.log(50 * y0), "int_ln_km_bt": math.log(y0 / 3), "int_ln_km_mt": None,
                          "int_ln_uc_por_km_bt": math.log(150), "int_mwh_por_uc": 2.0 + g}
    return series, fi


class Segmentos(unittest.TestCase):
    def test_contiguo_termina_em_2025_e_corta_ruptura(self):
        anos = {2022: ("observado", 1, False), 2023: ("observado", 2, False), 2024: ("observado", 3, True), 2025: ("observado", 4, False)}
        self.assertEqual(C.segmento(anos), [(2024, 3), (2025, 4)])
        anos[2025] = ("ausente", None, False)
        self.assertEqual(C.segmento(anos), [])
        anos[2025] = ("observado", 0.0, False)          # zero não é estoque positivo treinável
        self.assertEqual(C.segmento(anos), [])


class SemVazamento(unittest.TestCase):
    def test_previsao_na_origem_ignora_anos_posteriores(self):
        series, fi = painel()
        k = ("x", "quantidade")
        alvos = {d: [(a, v[1]) for a, v in sorted(s.items()) if a <= 2023] for d, s in series[k].items()}
        p1, _ = C.Motor(series, fi, {}).prever(k, 2023, alvos)
        # perturba fortemente 2024 e 2025: previsões feitas na origem 2023 não podem mudar
        for d in series[k]:
            for a in (2024, 2025):
                e = series[k][d][a]; series[k][d][a] = (e[0], e[1] * 7.0, e[2])
        p2, _ = C.Motor(series, fi, {}).prever(k, 2023, alvos)
        for m in p1:
            for d in p1[m]:
                self.assertEqual(p1[m][d], p2[m][d], m)

    def test_pares_de_treino_respeitam_origem_e_ruptura(self):
        series, fi = painel(ruptura_em=2024)
        mot = C.Motor(series, fi, {})
        X, g = mot.pares_treino(("x", "quantidade"), 2025, C.FEAT_INT)
        self.assertEqual(len(g), 40 * 2)              # 2022→23 e 2024→25; 2023→24 cruza ruptura
        X, g = mot.pares_treino(("x", "quantidade"), 2023, C.FEAT_INT)
        self.assertEqual(len(g), 40)


class Cenarios(unittest.TestCase):
    def test_mesmos_pontos_e_ordem_dos_cenarios(self):
        series, fi = painel()
        mot = C.Motor(series, fi, {})
        segs, bt, prev, _, _ = C.executar_metrica(mot, ("x", "quantidade"))
        pontos = {m: {(h, o, d) for _, _, h, o, d in v} for m, v in bt.items() if v}
        ref = pontos["persistencia"]
        self.assertTrue(all(p == ref for p in pontos.values()))
        self.assertEqual(len(ref), 40 * 3)            # (2023,h1), (2023,h2), (2024,h1)
        met, cen, just = C.escolher_cenarios(bt, prev, segs)
        self.assertIsNotNone(cen["moderado"])
        g = {c: met[m]["cagr_agregado"] for c, m in cen.items() if m}
        if "conservador" in g: self.assertLess(g["conservador"], g["moderado"])
        if "agressivo" in g: self.assertGreater(g["agressivo"], g["moderado"])
        for c, m in cen.items():
            if m is None:
                self.assertTrue(just[c].startswith("Indisponível"))
            else:
                self.assertTrue(met[m]["elegivel"])
                self.assertLessEqual(met[m]["erros"]["wape"], C.TOLERANCIA_ERRO * met[cen["moderado"]]["erros"]["wape"] + 1e-12)

    def test_crescimento_constante_favorece_crescimento_sobre_persistencia(self):
        series, fi = painel()
        mot = C.Motor(series, fi, {})
        segs, bt, prev, _, _ = C.executar_metrica(mot, ("x", "quantidade"))
        met, cen, _ = C.escolher_cenarios(bt, prev, segs)
        self.assertNotEqual(cen["moderado"], "persistencia")
        self.assertLess(met[cen["moderado"]]["erros"]["wape"], met["persistencia"]["erros"]["wape"])

    def test_sem_series_suficientes_bloqueia_painel(self):
        series, fi = painel(n=5)
        mot = C.Motor(series, fi, {})
        _, bt, _, diag, _ = C.executar_metrica(mot, ("x", "quantidade"))
        self.assertIn("TREINO_INSUFICIENTE", str(diag[2023]["ridge_painel"]))
        self.assertIsNone(bt["ridge_painel"])


if __name__ == "__main__":
    unittest.main()
