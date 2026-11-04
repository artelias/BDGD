"""python3 -m motor_universal --help (diretório nucleo-dados-bdgd)."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import gzip
from importlib.metadata import version, PackageNotFoundError
from .registry import read_json, registry_from_catalog
from .adapters import national_panel
from .engine import run
from .models import CANDIDATES
from .parquet_io import write_bundle, read_bundle, write_results
from .coverage import write_coverage


def code_digest():
    h = hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob("*.py")):
        h.update(path.name.encode()); h.update(path.read_bytes().replace(b"\r\n", b"\n"))   # code identity independent of CRLF checkouts
    return h.hexdigest()


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8")


from motor_v2.metric_contract import nature_of  # noqa: E402


def fisico(futuro, unidade):
    """Public projections follow the physical nature of the unit: discrete counts are non-negative integers (half-up, declared);
    km, kVA, kWh and ratios keep their decimals. The raw value is not part of the public summary."""
    from motor_v2.metric_contract import nature_of, physical_prediction
    nature = nature_of(unidade)
    return [physical_prediction(v, nature) for v in futuro]


def summary(report):
    """Resumo estático sem dados individuais nem artefato de treino volumoso."""
    return {k: report[k] for k in ("schema_version", "experiment_id", "dataset_version", "dataset_sha256", "source_sha256", "code_version",
            "as_of", "base_year", "horizontes", "sintetico", "previsao_validada", "objetivos", "limites", "agregacao_nacional")} | {
        "series": [{k: row.get(k) for k in ("DIST", "empresa", "objetivo_id", "metrica", "unidade", "status", "motivos",
                      "territorio", "perimetro_id", "regra_versao", "observacoes_treino", "modelo_selecionado", "validacao", "justificativa", "origens_selecao", "origem_auditoria")} |
                   {"natureza_fisica": nature_of(row["unidade"])} |
                   {"historico": [{"ano": h["ano"], "valor": h["valor"], "estado": h["estado"], "variacao_liquida": h["variacao_liquida"]} for h in row["historico"]],
                    "modelos": [{"modelo": c["modelo"], "metricas": c["metricas_diagnosticas"],
                                 "auditoria": c["metricas_auditoria"], "elegivel_selecao": c["elegivel_selecao"],
                                 "motivo": c["falha_projecao"], "futuro": fisico(c["futuro"], row["unidade"])}
                                for c in row["candidatos"] if c["metricas_diagnosticas"]["n"] > 0 or c["futuro"]]}
                   for row in report["series"]],
        "series_elegiveis": sum(bool(s["projecoes"]) for s in report["series"]),
        "objetivos_catalogados": len({t["objetivo_id"] for t in report["objetivos"]}),
        "extensoes_nao_implementadas": report["extensoes_nao_implementadas"],
        "candidatos": [{"id": c.id, "minimo_treino": c.min_train, "dependencia_ml": bool(c.sklearn_class)} for c in CANDIDATES.values()],
    }


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Motor Universal BDGD: experimento auditável, sem homologação automática")
    parser.add_argument("--catalog", type=Path, default=root / "etl/bdgd2025/config/conceitos_2025.json")
    parser.add_argument("--registry", type=Path, help="Substitui o adaptador pelo contrato universal objetivos-1")
    parser.add_argument("--panel", type=Path, help="Bundle Parquet bdgd-parquet-1/2; JSON aceito apenas como adaptador de migração/teste")
    parser.add_argument("--national", type=Path, default=root / "output-historico/contrato-integracao")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--web-summary", type=Path)
    parser.add_argument("--check-web", action="store_true")
    parser.add_argument("--debug-json", action="store_true", help="Cópia JSON opcional de diagnóstico; dados principais permanecem Parquet")
    parser.add_argument("--as-of", default="2026-10-26", help="Corte explícito e reproduzível AAAA-MM-DD")
    parser.add_argument("--base-year", type=int, default=2025)
    parser.add_argument("--final-year", type=int, default=2030)
    args = parser.parse_args()
    registry = read_json(args.registry) if args.registry else registry_from_catalog(read_json(args.catalog))
    output = args.output
    if output.exists():
        raise ValueError("Diretório de experimento já existe; preserve o registro e escolha outra saída")
    output.mkdir(parents=True)
    if args.panel and args.panel.is_dir():
        panel = read_bundle(args.panel, registry)
    else:
        panel = read_json(args.panel) if args.panel else national_panel(args.national, registry)
        if args.panel:
            panel["source_sha256"] = hashlib.sha256(args.panel.read_bytes()).hexdigest()
        write_bundle(panel, registry, output / "entrada")
        panel = read_bundle(output / "entrada", registry)
    result = run(panel, registry, base_year=args.base_year, final_year=args.final_year, as_of=args.as_of, code_version=code_digest())
    coverage_summary = write_coverage(panel, registry, result, output / "cobertura")
    write_json(output / "objetivos.json", registry)
    write_json(output / "experimento-manifesto.json", write_results(result, output))
    if args.debug_json:
        write_json(output / "experimento.json", result)
    dependencies = {}
    for name in ("pyarrow", "scikit-learn", "numpy", "scipy"):
        try: dependencies[name] = version(name)
        except PackageNotFoundError: dependencies[name] = None
    write_json(output / "execucao.json", {"experiment_id": result["experiment_id"], "executado_em": datetime.now(timezone.utc).isoformat(),
                                          "python": platform.python_version(), "dependencias": dependencies, "codigo_sha256": code_digest()})
    product = summary(result)
    product["cobertura"] = {k: coverage_summary[k] for k in ("esperado", "observado", "elegivel", "bloqueado", "ausente_no_contrato", "por_metrica")}
    if args.web_summary:
        if args.check_web:
            existing = json.loads(gzip.decompress(args.web_summary.read_bytes())) if args.web_summary.suffix == ".gz" else read_json(args.web_summary)
            if product != existing:
                raise ValueError("Resumo web não corresponde ao motor/dataset versionados")
        else:
            args.web_summary.parent.mkdir(parents=True, exist_ok=True)
            encoded = (json.dumps(product, ensure_ascii=False, separators=(",", ":"), allow_nan=False)+"\n").encode("utf-8")
            args.web_summary.write_bytes(gzip.compress(encoded, mtime=0) if args.web_summary.suffix == ".gz" else encoded)
    print(json.dumps({"experiment_id": result["experiment_id"], "objetivos": product["objetivos_catalogados"],
                      "objetivo_metricas": len(registry["objetivos"]), "series": len(result["series"]),
                      "series_elegiveis": product["series_elegiveis"], "previsao_validada": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
