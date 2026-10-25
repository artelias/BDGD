"""Regressões offline: só de-para comprovado e correspondência unívoca."""
import unittest
from prepare_iasc import preparar, pontuacao

BASE = [{"NumAno": "2025", "NumCNPJ": "12.345.678/0001-99", "MdaIndicadorSatisfacao": "72,45"}]
MAP = [{"dist": "6600", "ano": "2025", "cnpj": "12345678000199",
        "status": "verificado", "fonte_vinculo": "https://www.gov.br/aneel/comprovacao"}]

class TestIasc(unittest.TestCase):
    def test_match_exato(self):
        rows, qa = preparar(BASE, MAP, 2025)
        self.assertEqual(rows[0]["valor"], 72.45)
        self.assertEqual(rows[0]["dist"], 6600)
        self.assertNotIn("cnpj", rows[0])
        self.assertEqual(qa["resultados_publicaveis"], 1)

    def test_nao_adivinha_nome_ou_cnpj(self):
        rows, _ = preparar(BASE, [{**MAP[0], "cnpj": "12345678000100"}], 2025)
        self.assertEqual(rows, [])

    def test_nao_aceita_vinculo_sem_fonte(self):
        rows, _ = preparar(BASE, [{**MAP[0], "fonte_vinculo": ""}], 2025)
        self.assertEqual(rows, [])

    def test_ambiguidade_e_reprovada(self):
        rows, qa = preparar(BASE, MAP + [{**MAP[0], "dist": "6601"}], 2025)
        self.assertEqual(rows, [])
        self.assertEqual(len(qa["rejeitados"]), 2)

    def test_duplicidade_na_fonte(self):
        rows, qa = preparar(BASE + BASE, MAP, 2025)
        self.assertEqual(rows, [])
        self.assertEqual(qa["rejeitados"][0]["motivo"], "resultado_iasc_ausente_ou_duplicado")

    def test_conflito_com_registro_nao_verificado_bloqueia(self):
        conflito = {**MAP[0], "cnpj": "12345678000100", "status": "pendente"}
        rows, qa = preparar(BASE, MAP + [conflito], 2025)
        self.assertEqual(rows, [])
        self.assertEqual(qa["rejeitados"][0]["motivo"], "correspondencia_ambigua")

    def test_mesmo_cnpj_em_outra_dist_pendente_bloqueia(self):
        conflito = {**MAP[0], "dist": "6601", "status": "pendente"}
        rows, qa = preparar(BASE, MAP + [conflito], 2025)
        self.assertEqual(rows, [])
        self.assertEqual(qa["rejeitados"][0]["motivo"], "correspondencia_ambigua")

    def test_numerico(self):
        self.assertIsNone(pontuacao("N/D"))
        self.assertIsNone(pontuacao("200"))
        self.assertEqual(pontuacao("0"), 0)
        self.assertEqual(pontuacao("68,35"), 68.35)

if __name__ == "__main__":
    unittest.main()
