from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from motor_universal.tests.test_motor import fixture
from motor_universal.parquet_io import write_bundle, read_bundle, write_results, arrow, sha
from motor_universal.engine import run
from motor_universal.features import feature_row


class ParquetTests(unittest.TestCase):
    def test_long_targets_wide_features_roundtrip(self):
        p, r = fixture(4)
        p["rows"][0].update(status_qualidade="zero_tecnico", valor_alvo=0)
        p["rows"][1].update(status_qualidade="ausente", valor_alvo=None)
        more = deepcopy(p["rows"])
        for row in more: row["objetivo_id"] = "geradores"
        p["rows"] += more
        with tempfile.TemporaryDirectory() as root:
            bundle = Path(root) / "bundle"; write_bundle(p, r, bundle)
            _, pq = arrow()
            self.assertEqual(pq.read_table(bundle / "targets.parquet").num_rows, 8)
            self.assertEqual(pq.read_table(bundle / "features.parquet").num_rows, 4)
            restored = read_bundle(bundle, r)
            self.assertEqual(restored["rows"][0]["valor_alvo"], 0)
            self.assertEqual(restored["rows"][0]["status_qualidade"], "zero_tecnico")
            self.assertIsNone(restored["rows"][1]["valor_alvo"])
            columns = pq.read_table(bundle / "targets.parquet").column_names
            for name in ["ANO", "DIST", "OBJETIVO_ID", "METRICA", "STATUS_HOMOLOGACAO", "RUPTURA_CADASTRAL", "PROVENIENCIA_JSON", "NATUREZA_ALVO", "COMPARABILIDADE_VALIDADA"]:
                self.assertIn(name, columns)

    def test_primary_key_does_not_hide_two_rule_versions(self):
        p, r = fixture(4); extra = deepcopy(p["rows"][0]); extra["regra_versao"] = "outra"; p["rows"].append(extra)
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError, "Chave long duplicada"):
                write_bundle(p, r, Path(root) / "bad")

    def test_wide_conflict_between_assets_rejected(self):
        p, r = fixture(4)
        p["feature_definitions"] = {"populacao": {"tipo": "numerica", "unidade": "pessoas"}}
        for row in p["rows"]:
            row["features"] = {"populacao": {"valor": 1000, "referencia": "2009-12-31", "disponivel_em": "2009-12-31", "fonte": "SINTETICO", "unidade": "pessoas"}}
        extra = deepcopy(p["rows"][0]); extra["objetivo_id"] = "geradores"; extra["features"]["populacao"]["valor"] = 2000
        p["rows"].append(extra)
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError, "conflitantes"):
                write_bundle(p, r, Path(root) / "bad")

    def test_wide_duplicates_and_corruption_rejected(self):
        p, r = fixture(4)
        with tempfile.TemporaryDirectory() as root:
            bundle = Path(root) / "bundle"; write_bundle(p, r, bundle)
            pa, pq = arrow(); path = bundle / "features.parquet"
            table = pq.read_table(path); pq.write_table(pa.concat_tables([table, table.slice(0, 1)]), path)
            manifest = json.loads((bundle / "manifest.json").read_text()); manifest["sha256"]["features.parquet"] = sha(path)
            (bundle / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "wide duplicadas"): read_bundle(bundle, r)
            path.write_bytes(b"corrompido")
            with self.assertRaisesRegex(ValueError, "Hash Parquet"): read_bundle(bundle, r)

    def test_municipal_grain_not_implicitly_enabled(self):
        p, r = fixture(4)
        for row in p["rows"]: row["territorio"] = {"nivel": "municipio", "id": "1234567"}
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError, "territorial v2"): write_bundle(p, r, Path(root) / "bad")

    def test_power_requires_explicit_comparability(self):
        p, r = fixture(4)
        for row in p["rows"]: row.update(objetivo_id="trafo_dist", metrica="potencia_kva", unidade="kVA")
        result = run(p, r, base_year=2013, final_year=2018)
        self.assertIn("METRICA_SEM_COMPARABILIDADE_VALIDADA", result["series"][0]["motivos"])
        self.assertTrue(all(h["variacao_liquida"] is None for h in result["series"][0]["historico"]))
        for row in p["rows"]: row.update(comparabilidade_validada=True, evidencia_comparabilidade="SINTETICO: prova de semântica estável")
        self.assertTrue(run(p, r, base_year=2013, final_year=2018)["series"][0]["projecoes"])

    def test_consumption_demand_features_need_validation(self):
        p, _ = fixture(4)
        for name, unit in [("demanda", "MW"), ("consumo", "MWh"), ("potencia", "kVA")]:
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, "COMPARABILIDADE"):
                    feature_row(p["rows"][:2], 2012, {"features": {}}, {name: {"tipo": "numerica", "unidade": unit}}, "2011-12-31")

    def test_stock_change_not_expansion_need_and_result_parquet(self):
        p, r = fixture(8)
        result = run(p, r, base_year=2017, final_year=2022, candidates=["persistencia", "tendencia_ols"])
        s = result["series"][0]
        self.assertEqual(s["projecoes"][0]["variacao_liquida"], 10)
        self.assertIsNone(s["projecoes"][0]["necessidade_expansao"])
        self.assertEqual(s["natureza_alvo"], "estoque_fisico")
        with tempfile.TemporaryDirectory() as root:
            manifest = write_results(result, root)
            _, pq = arrow(); table = pq.read_table(Path(root) / "projecoes.parquet")
            self.assertEqual(table.num_rows, 5)
            self.assertFalse(table.to_pylist()[0]["previsao_validada"])
            self.assertIn("não são observações independentes", manifest["interpretacao_amostral"])


if __name__ == "__main__": unittest.main()
