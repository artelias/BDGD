"""Public scenario product honours the physical nature contract (JSON and CSV), independently of the TypeScript tests."""
import csv
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from motor_v2 import metric_contract as mc  # noqa: E402

PRODUTO = ROOT / "web/public/data/previsoes/cenarios-motor.json"
CSV = Path(__file__).parent / "saida/CENARIOS_CONSERVADOR_MODERADO_AGRESSIVO.csv"
HORIZONTE = ["2026", "2027", "2028", "2029", "2030"]


@unittest.skipUnless(PRODUTO.exists(), "produto não gerado")
class ProdutoPublico(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = json.loads(PRODUTO.read_text(encoding="utf-8"))

    def test_cada_metrica_declara_natureza_coerente_com_a_unidade(self):
        for m in self.d["metricas"]:
            self.assertIn(m["natureza"], mc.NATURES)
            if m["unidade"]:
                self.assertEqual(m["natureza"], mc.nature_of(m["unidade"]), (m["conceito"], m["metrica"]))

    def test_contagens_publicas_sao_inteiros_nao_negativos(self):
        n = 0
        for m in self.d["metricas"]:
            if m["natureza"] != "discrete_count":
                continue
            for s in m["series"].values():
                for c in ("conservador", "moderado", "agressivo"):
                    for v in s[c] or []:
                        n += 1
                        self.assertIs(type(v), int, (m["conceito"], v)); self.assertGreaterEqual(v, 0)
        self.assertGreater(n, 10000)

    def test_extensao_e_potencia_mantem_decimais(self):
        decimais = sum(1 for m in self.d["metricas"] if m["natureza"] in ("continuous_length", "continuous_capacity")
                       for s in m["series"].values() for c in ("conservador", "moderado", "agressivo") for v in (s[c] or []) if isinstance(v, float) and v != int(v))
        self.assertGreater(decimais, 1000)

    def test_historico_observado_de_contagem_e_inteiro_sem_decimais(self):
        n = 0
        for m in self.d["metricas"]:
            if m["natureza"] != "discrete_count":
                continue
            for s in m["series"].values():
                for _, v in s["hist"]:
                    n += 1
                    self.assertIs(type(v), int, (m["conceito"], v)); self.assertGreaterEqual(v, 0)
        self.assertGreater(n, 5000)

    def test_extremo_nunca_sem_moderado_e_ausencia_com_motivo(self):
        """Conservador/Agressivo são definidos em relação ao Moderado: série sem Moderado não publica extremo; quando a métrica
        tem modelo para o cenário e a série fica sem ele, o motivo do gerador está registrado."""
        validos = {"TRAJETORIA_IMPLAUSIVEL_NA_SERIE", "HISTORICO_CONTIGUO_INSUFICIENTE", "MODELO_SEM_PROJECAO_NA_SERIE", "SEM_MODERADO_NA_SERIE"}
        n = 0
        for m in self.d["metricas"]:
            for d, s in m["series"].items():
                if s["moderado"] is None:
                    self.assertIsNone(s["conservador"], (m["conceito"], d)); self.assertIsNone(s["agressivo"], (m["conceito"], d))
                for c in ("conservador", "moderado", "agressivo"):
                    if m["cenarios"][c] and s[c] is None:
                        n += 1
                        self.assertIn(s.get("motivos", {}).get(c), validos, (m["conceito"], m["metrica"], d, c))
        self.assertGreater(n, 0)

    def test_bruto_nao_esta_no_produto_publico(self):
        txt = PRODUTO.read_text(encoding="utf-8")
        self.assertNotIn("raw_prediction", txt)


@unittest.skipUnless(CSV.exists(), "CSV não gerado")
class CsvPublico(unittest.TestCase):
    def test_colunas_de_contagem_sem_fracao_e_cabecalho_com_natureza(self):
        linhas = list(csv.DictReader(CSV.open(encoding="utf-8")))
        self.assertIn("natureza", linhas[0])
        for r in linhas:
            if r["natureza"] == "discrete_count":
                for a in HORIZONTE + ["base_2025"]:
                    if r[a] != "":
                        self.assertRegex(r[a], r"^\d+$", (r["conceito"], a, r[a]))      # 123, nunca 123.0

    def test_cenarios_ordenados_por_distribuidora_quando_modelos_distintos_nao_invertem_arredondamento(self):
        # o arredondamento é monótono: duas trajetórias brutas ordenadas continuam ordenadas depois de inteiras
        for bruto in ([(1.4, 1.5), (2.49, 2.5), (99.5, 99.6)]):
            self.assertLessEqual(mc.round_count(bruto[0]), mc.round_count(bruto[1]))


class ErroFisico(unittest.TestCase):
    """Patch B (Motor V2): erro das previsões inteiras publicáveis ao lado do erro contínuo, só para contagens."""
    def test_erro_fisico_registrado_ao_lado_do_continuo_para_contagens(self):
        with open(ROOT / "web/public/data/previsoes/cenarios-motor.json", encoding="utf-8") as f:
            doc = json.load(f)
        com = 0
        for m in doc["metricas"]:
            for e in m["modelos"].values():
                if m["natureza"] == "discrete_count":
                    if not e["n"]:
                        continue                                                     # modelo sem pontos de backtest: sem erro algum
                    self.assertIn("mae_fisico", e)
                    if e.get("mae_fisico") is not None:
                        com += 1
                        self.assertIsNotNone(e["mae"])                               # o erro contínuo continua publicado
                    else:
                        self.assertEqual(e.get("fisico_motivo"), "PREVISAO_NEGATIVA_NAO_PUBLICAVEL")
                else:
                    self.assertNotIn("mae_fisico", e)
        self.assertGreater(com, 100)


if __name__ == "__main__":
    unittest.main()
