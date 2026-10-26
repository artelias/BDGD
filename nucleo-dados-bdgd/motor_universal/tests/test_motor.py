"""Dados sintéticos só nas fixtures; integração real é somente leitura."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from motor_universal.registry import registry_from_catalog, read_json, validate_registry
from motor_universal.contracts import validate_panel, contiguous_tail, series_key
from motor_universal.features import FeaturePipeline, feature_row
from motor_universal.models import CANDIDATES, predict
from motor_universal.engine import run, metrics
from motor_universal.adapters import national_panel
from motor_universal.reconcile import reconcile

ROOT = Path(__file__).resolve().parents[2]
CATALOG = read_json(ROOT / "etl/bdgd2025/config/conceitos_2025.json")


def fixture(n=16):
    registry = registry_from_catalog(CATALOG)
    panel = {"schema_version": "painel-bdgd-1", "dataset_version": "SINTETICO-TESTE-1", "sintetico": True,
             "feature_definitions": {}, "rows": []}
    for year in range(2010, 2010+n):
        panel["rows"].append({"ano": year, "DIST": "26", "objetivo_id": "consumidores", "metrica": "quantidade",
                              "unidade": "itens", "valor_alvo": 100+10*(year-2010), "status_qualidade": "observado",
                              "competencia": f"{year}-12-31", "disponivel_em": f"{year}-12-31", "fonte": "SINTETICO",
                              "features": {}, "territorio": {"nivel": "dist", "id": "26"}, "perimetro_id": "teste",
                              "regra_versao": "teste-1", "homologado": False, "status_homologacao": "SINTETICO_NAO_HOMOLOGADO", "ruptura": False, "nao_somar": False, "cobertura": 1})
    return panel, registry


class RegistryTests(unittest.TestCase):
    def test_all_assets_and_declared_metrics(self):
        registry = registry_from_catalog(CATALOG)
        self.assertEqual({x["objetivo_id"] for x in registry["objetivos"]}, {x["id"] for x in CATALOG["ativos"]})
        self.assertIn(("trafo_dist", "potencia_kva"), validate_registry(registry))
        self.assertEqual(len({x["objetivo_id"] for x in registry["objetivos"]}), len(CATALOG["ativos"]))

    def test_new_catalog_asset_needs_no_code_change(self):
        catalog = deepcopy(CATALOG)
        catalog["conceitos"]["bay_sintetico"] = {"nome": "Bay", "entidades": ["BAY"], "medidas": ["quantidade"], "descricao": "SINTETICO", "cubos": {}}
        catalog["ativos"].append({**catalog["ativos"][-1], "id": "bay_teste", "conceito": "bay_sintetico", "nome": "Bay sintético de teste"})
        self.assertIn(("bay_teste", "quantidade"), validate_registry(registry_from_catalog(catalog)))

    def test_no_installation_equipment_double_count(self):
        t = validate_registry(registry_from_catalog(CATALOG))["trafo_dist", "quantidade"]
        self.assertTrue(all(e.startswith("EQ") for e in t["entidades"]))
        self.assertEqual(t["filtros"], next(a for a in CATALOG["ativos"] if a["id"] == "trafo_dist")["filtro"])

    def test_registry_rejects_duplicate(self):
        _, r = fixture(); r["objetivos"].append(r["objetivos"][0])
        with self.assertRaisesRegex(ValueError, "duplicado"):
            validate_registry(r)


class InputTests(unittest.TestCase):
    def test_valid_and_independent_zero(self):
        p, r = fixture(); p["rows"][0].update(valor_alvo=0, status_qualidade="zero_verificado", evidencia_zero="SINTETICO-proof")
        validate_panel(p, r)

    def test_rejects_invalid_inputs(self):
        mutations = [lambda p: p["rows"].append(deepcopy(p["rows"][0])),
                     lambda p: p["rows"][0].update(unidade="km"),
                     lambda p: p["rows"][0].update(valor_alvo=float("nan")),
                     lambda p: p["rows"][0].update(valor_alvo=-1),
                     lambda p: p["rows"][0].update(valor_alvo=0),
                     lambda p: p["rows"][0].update(valor_alvo=0, status_qualidade="ausente"),
                     lambda p: p["rows"][0].update(valor_alvo=0, status_qualidade="zero_verificado"),
                     lambda p: p["rows"][0].update(valor_alvo=2.5),
                     lambda p: p["rows"][0].update(cobertura=float("nan")),
                     lambda p: p.update(schema_version="futura"),
                     lambda p: p["rows"][0].update(ruptura="false"),
                     lambda p: p["rows"][0].update(disponivel_em="2009-01-01")]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                p, r = fixture(); mutation(p)
                with self.assertRaises(ValueError): validate_panel(p, r)

    def test_missing_target_not_imputed(self):
        p, r = fixture(4); p["rows"][-1].update(valor_alvo=None, status_qualidade="ausente")
        result = run(p, r, base_year=2013, final_year=2018)
        self.assertFalse(result["series"][0]["projecoes"])
        self.assertIsNone(result["series"][0]["historico"][-1]["valor"])

    def test_break_and_gap_cut_history(self):
        p, _ = fixture(8); p["rows"][5]["ruptura"] = True
        self.assertEqual([r["ano"] for r in contiguous_tail(p["rows"])], [2015, 2016, 2017])
        self.assertEqual([r["ano"] for r in contiguous_tail(p["rows"][:3] + p["rows"][5:])], [2015, 2016, 2017])

    def test_no_overlap_no_incomplete_coverage(self):
        p, _ = fixture(4); p["rows"][-1]["nao_somar"] = True
        self.assertEqual(contiguous_tail(p["rows"]), [])
        p["rows"][-1]["nao_somar"] = False; p["rows"][-1]["cobertura"] = 0.5
        self.assertEqual(contiguous_tail(p["rows"]), [])

    def test_substation_keys_do_not_collide(self):
        p, r = fixture(4)
        for row in p["rows"]:
            row["territorio"] = {"nivel": "subestacao", "id": "A"}
        second = deepcopy(p["rows"])
        for row in second: row["territorio"]["id"] = "B"
        p["rows"] += second
        validate_panel(p, r)
        self.assertNotEqual(series_key(p["rows"][0]), series_key(second[0]))


class FeatureTests(unittest.TestCase):
    def test_training_transform_cannot_see_future_extreme(self):
        model = FeaturePipeline().fit([{"x": 10, "grupo": "A"}, {"x": 20, "grupo": "B"}])
        before = deepcopy(model.numeric)
        model.transform([{"x": 1000000, "grupo": "C"}])
        self.assertEqual(model.numeric, before)
        self.assertEqual(model.categories["grupo"], ["A", "B"])

    def test_lags_exclude_current_target(self):
        p, _ = fixture(4); history = p["rows"]
        row = feature_row(history, 2012, {}, {}, "2011-12-31")
        self.assertEqual(row["lag_1"], 110)
        self.assertEqual(row["media_movel_3"], 105)

    def test_external_availability_and_reference(self):
        p, _ = fixture(4)
        defs = {"pib": {"tipo": "numerica", "unidade": "BRL_real", "comparabilidade_validada": True, "evidencia_comparabilidade": "SINTETICO"}}
        source = {"features": {"pib": {"valor": 10, "disponivel_em": "2013-01-01", "referencia": "2011-12-31"}}}
        with self.assertRaisesRegex(ValueError, "INDISPONIVEL"):
            feature_row(p["rows"][:2], 2012, source, defs, "2011-12-31")
        source["features"]["pib"].update(disponivel_em="2011-12-31", referencia="2012-12-31")
        with self.assertRaisesRegex(ValueError, "CONTEMPORANEA"):
            feature_row(p["rows"][:2], 2012, source, defs, "2011-12-31")
        source["features"]["pib"]["cenario_id"] = "SINTETICO"
        self.assertEqual(feature_row(p["rows"][:2], 2012, source, defs, "2011-12-31")["pib"], 10)

    def test_declared_ratios_and_interactions(self):
        p, _ = fixture(4); defs = {"clientes": {"tipo": "numerica", "unidade": "itens", "dividir_por": ["area"], "interagir_com": ["area"]}, "area": {"tipo": "numerica", "unidade": "km2"}}
        source = {"features": {k: {"valor": v, "disponivel_em": "2011-12-31", "referencia": "2011-12-31"} for k, v in [("clientes", 100), ("area", 20)]}}
        for spec in defs.values(): spec.update(comparabilidade_validada=True, evidencia_comparabilidade="SINTETICO")
        x = feature_row(p["rows"][:2], 2012, source, defs, "2011-12-31")
        self.assertEqual(x["razao:clientes/area"], 5)
        self.assertEqual(x["interacao:clientes*area"], 2000)


class BacktestTests(unittest.TestCase):
    def test_four_years_never_become_validated_forecast(self):
        p, r = fixture(4)
        result = run(p, r, base_year=2013, final_year=2018)
        s = result["series"][0]
        self.assertFalse(result["previsao_validada"])
        self.assertEqual(s["modelo_selecionado"], "persistencia")
        self.assertEqual(s["validacao"], "retrospectiva_limitada")
        self.assertTrue(all(x["intervalo"] is None for x in s["projecoes"]))
        self.assertFalse(s["projecoes"][-1]["horizonte_com_backtest"])

    def test_folds_are_expanding_and_multi_horizon(self):
        p, r = fixture(8); s = run(p, r, base_year=2017, final_year=2022)["series"][0]
        for c in s["candidatos"]:
            for fold in c["folds"]:
                self.assertGreater(fold["ano"], fold["origem"])
                self.assertEqual(fold["ano"] - fold["origem"], fold["horizonte"])
        self.assertIn("5", s["candidatos"][0]["por_horizonte"])

    def test_holdout_never_selects_model(self):
        p, r = fixture(8)
        a = run(p, r, base_year=2017, final_year=2022, candidates=["persistencia", "tendencia_ols"])
        p["rows"][-1]["valor_alvo"] = 9999
        b = run(p, r, base_year=2017, final_year=2022, candidates=["persistencia", "tendencia_ols"])
        self.assertEqual(a["series"][0]["modelo_selecionado"], b["series"][0]["modelo_selecionado"])
        self.assertEqual(a["series"][0]["modelo_selecionado"], "tendencia_ols")

    def test_negative_projection_rejected_not_silently_truncated(self):
        p, _ = fixture(4)
        for row, value in zip(p["rows"], [100, 60, 20, 1]): row["valor_alvo"] = value
        with self.assertRaisesRegex(ValueError, "NEGATIVA"):
            predict(CANDIDATES["tendencia_ols"], p["rows"], [2020])

    def test_zero_denominator_wape_is_null(self):
        self.assertIsNone(metrics([{"observado": 0, "previsto": 1}])["wape"])
        self.assertEqual(metrics([{"observado": 2, "previsto": 1}, {"observado": 4, "previsto": 6}])["wape"], 0.5)

    def test_future_target_and_future_availability_blocked(self):
        p, r = fixture(5)
        with self.assertRaisesRegex(ValueError, "posterior"):
            run(p, r, base_year=2013, final_year=2018)
        p["rows"][-1]["disponivel_em"] = "2030-01-01"
        self.assertEqual(run(p, r, base_year=2014, final_year=2019)["series"][0]["projecoes"], [])

    def test_reproducibility(self):
        p, r = fixture(4)
        self.assertEqual(run(p, r, base_year=2013, final_year=2018), run(p, r, base_year=2013, final_year=2018))

    def test_optional_ml_runs_on_synthetic_training_only(self):
        try: import sklearn  # noqa: F401
        except ImportError: self.skipTest("Instale requirements-ml.txt para testar os estimadores opcionais")
        p, _ = fixture(35)
        for c in CANDIDATES.values():
            if c.sklearn_class:
                with self.subTest(model=c.id):
                    values, info = predict(c, p["rows"], [2045, 2046], {}, {}, "2044-12-31")
                    self.assertEqual(len(values), 2)
                    self.assertTrue(all(v >= 0 for v in values))
                    self.assertTrue(info["transformacoes_ajustadas_no_treino"])


class AggregationTests(unittest.TestCase):
    def test_no_implicit_national_total(self):
        self.assertIsNone(reconcile([], expected_territories=["A"])["valor"])

    def test_disjoint_complete_aggregation_only(self):
        row = {"ano": 2030, "objetivo_id": "consumidores", "metrica": "quantidade", "unidade": "itens", "perimetro_id": "p", "valor": 10, "territorio_id": "A"}
        rows = [row, {**row, "territorio_id": "B", "valor": 20}]
        args = dict(expected_territories=["A", "B"], coverage_complete=True, disjoint_evidence="SINTETICO-evidencia")
        self.assertEqual(reconcile(rows, **args)["valor"], 30)
        self.assertIsNone(reconcile(rows[:1], **args)["valor"])
        self.assertIsNone(reconcile([row, row], **args)["valor"])
        self.assertIsNone(reconcile([row, {**rows[1], "unidade": "km"}], **args)["valor"])


class RealIntegrationTests(unittest.TestCase):
    def test_real_contract_only_read_and_zero_not_approved(self):
        r = registry_from_catalog(CATALOG)
        p = national_panel(ROOT / "output-historico/contrato-integracao", r)
        validate_panel(p, r)
        self.assertEqual(len(p["rows"]), read_json(ROOT / "output-historico/contrato-integracao/MANIFESTO.json")["linhas"])
        self.assertFalse(p["sintetico"])
        self.assertFalse(any(x["status_qualidade"] == "zero_verificado" for x in p["rows"]))
        self.assertTrue(any(x["status_qualidade"] == "zero_tecnico" for x in p["rows"]))
        self.assertTrue(all(x["valor_alvo"] is None for x in p["rows"] if x["status_qualidade"] in {"ausente", "nao_homologado", "nao_aplicavel"}))


if __name__ == "__main__": unittest.main()
