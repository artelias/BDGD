"""Tolerância do --check entre plataformas: a folga de 1 unidade das contagens projetadas existe, é limitada e não esconde deslocamentos."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import cenarios as C  # noqa: E402


def produto(trajetorias, hist=((2022, 40), (2025, 50))):
    """Um produto mínimo: uma métrica, uma série por trajetória (lista de 5 inteiros projetados ou floats)."""
    return {"metricas": [{"series": {str(i): {"hist": [list(h) for h in hist], "moderado": list(t)} for i, t in enumerate(trajetorias)}}]}


def comparar(a, b):
    return C.comparar_produtos(a, b)


class ToleranciaDeContagens(unittest.TestCase):
    def test_produto_identico_nao_usa_folga(self):
        p = produto([[50, 51, 52, 53, 54]])
        erros, n, folga = comparar(p, produto([[50, 51, 52, 53, 54]]))
        self.assertEqual((erros, n, folga), ([], 5, 0))

    def test_uma_unidade_em_serie_pequena_e_aceita_e_contada(self):
        erros, n, folga = comparar(produto([[50, 51, 52, 53, 54]]), produto([[50, 51, 52, 53, 55]]))    # 1/55 = 1,8% > 0,5%
        self.assertEqual((erros, folga), ([], 1))

    def test_duas_unidades_sao_erro(self):
        erros, _, _ = comparar(produto([[50, 51, 52, 53, 54]]), produto([[50, 51, 52, 53, 56]]))
        self.assertEqual(len(erros), 1); self.assertIn("54 ≠ 56", erros[0])

    def test_serie_grande_dentro_de_meio_por_cento_nao_usa_a_folga(self):
        erros, _, folga = comparar(produto([[100000, 100000, 100000, 100000, 100000]]), produto([[100400, 100000, 100000, 100000, 100000]]))
        self.assertEqual((erros, folga), ([], 0))
        erros, _, _ = comparar(produto([[100000] * 5]), produto([[100600, 100000, 100000, 100000, 100000]]))
        self.assertEqual(len(erros), 1)

    def test_deslocamento_sistematico_de_uma_unidade_estoura_o_limite(self):
        n = 1000                                                  # 5.000 contagens; limite = 0,5% = 25; todas deslocadas em +1
        erros, total, folga = comparar(produto([[50] * 5] * n), produto([[51] * 5] * n))
        self.assertEqual((total, folga), (5 * n, 5 * n))
        self.assertTrue(any("deslocamento sistemático" in e for e in erros), erros[:3])

    def test_ruido_esparso_de_uma_unidade_passa(self):
        trajetorias = [[50] * 5 for _ in range(1000)]
        novo = [list(t) for t in trajetorias]
        for i in range(10): novo[i][0] = 51                       # 10 pontos em 5.000 (0,2%): ruído, não deslocamento
        erros, total, folga = comparar(produto(trajetorias), produto(novo))
        self.assertEqual((erros, folga), ([], 10))

    def test_historico_observado_continua_exato(self):
        erros, _, _ = comparar(produto([[50] * 5], hist=((2022, 40), (2025, 50))), produto([[50] * 5], hist=((2022, 40), (2025, 51))))
        self.assertEqual(len(erros), 1)

    def test_contagem_ausente_ou_trocada_por_none_e_erro(self):
        erros, _, _ = comparar(produto([[50, 51, 52, 53, 54]]), produto([[50, 51, 52, 53, None]]))
        self.assertTrue(erros)

    def test_continuos_mantem_a_regra_relativa_de_meio_por_cento(self):
        base = produto([[1000.0, 1000.0, 1000.0, 1000.0, 1000.0]])
        self.assertEqual(comparar(base, produto([[1004.9, 1000.0, 1000.0, 1000.0, 1000.0]]))[0], [])
        self.assertEqual(len(comparar(base, produto([[1005.5, 1000.0, 1000.0, 1000.0, 1000.0]]))[0]), 1)


if __name__ == "__main__":
    unittest.main()
