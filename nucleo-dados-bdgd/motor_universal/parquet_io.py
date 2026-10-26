"""Contrato principal: alvos long ANO/DIST/OBJETIVO_ID/METRICA e features wide ANO/DIST."""
from collections import defaultdict
from datetime import date
import hashlib
import json
from pathlib import Path
import re
from .contracts import validate_panel, iso, finite

FIELDS = {"ano": "ANO", "DIST": "DIST", "objetivo_id": "OBJETIVO_ID", "metrica": "METRICA",
          "unidade": "UNIDADE", "valor_alvo": "VALOR_ALVO", "status_qualidade": "STATUS_QUALIDADE",
          "status_homologacao": "STATUS_HOMOLOGACAO", "homologado": "HOMOLOGADO", "fonte": "FONTE",
          "competencia": "COMPETENCIA", "disponivel_em": "DISPONIVEL_EM", "cobertura": "COBERTURA",
          "perimetro_id": "PERIMETRO_ID", "regra_versao": "REGRA_VERSAO", "ruptura": "RUPTURA_CADASTRAL", "nao_somar": "NAO_SOMAR",
          "comparabilidade_validada": "COMPARABILIDADE_VALIDADA", "evidencia_comparabilidade": "EVIDENCIA_COMPARABILIDADE",
          "natureza_alvo": "NATUREZA_ALVO"}
DATE_FIELDS = {"COMPETENCIA", "DISPONIVEL_EM"}
SUFFIXES = ("disponivel_em", "referencia", "fonte", "cenario_id")


def arrow():
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise ValueError("Instale motor_universal/requirements.txt para ingestão Parquet") from exc
    return pa, pq


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _feature_schema(definitions):
    pa, _ = arrow()
    fields = [("ANO", pa.int32()), ("DIST", pa.string())]
    for name, spec in sorted(definitions.items()):
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name) or "__" in name:
            raise ValueError("Nome de feature wide inválido/reservado")
        fields.append((name, pa.float64() if spec["tipo"] == "numerica" else pa.string()))
        fields += [(name + "__" + suffix, pa.date32() if suffix in {"disponivel_em", "referencia"} else pa.string()) for suffix in SUFFIXES]
    return pa.schema(fields)


def write_bundle(panel, registry, directory):
    validate_panel(panel, registry)
    pa, pq = arrow()
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=False)
    target_rows, feature_rows, target_keys = [], {}, set()
    definitions = panel["feature_definitions"]
    fschema = _feature_schema(definitions)
    for row in panel["rows"]:
        if row["territorio"] != {"nivel": "dist", "id": str(row["DIST"])}:
            raise ValueError("Parquet v1 é DIST × ano; municipal requer contrato territorial v2")
        key = (row["ano"], str(row["DIST"]), row["objetivo_id"], row["metrica"])
        if key in target_keys:
            raise ValueError("Chave long duplicada ANO+DIST+OBJETIVO_ID+METRICA; canonize regra/perímetro antes da ingestão")
        target_keys.add(key)
        defaults = {"comparabilidade_validada": False, "evidencia_comparabilidade": None, "natureza_alvo": "estoque_fisico"}
        current = {**defaults, **row}
        converted = {column: (iso(current[field]) if column in DATE_FIELDS and current[field] is not None else str(current[field]) if column == "DIST" else current[field]) for field, column in FIELDS.items()}
        converted["PROVENIENCIA_JSON"] = json.dumps(row.get("proveniencia", {}), ensure_ascii=False, sort_keys=True, allow_nan=False)
        converted["METADADOS_JSON"] = json.dumps({k: v for k, v in row.items() if k not in FIELDS and k not in {"features", "territorio", "proveniencia"}}, ensure_ascii=False, sort_keys=True, allow_nan=False)
        target_rows.append(converted)
        fkey = row["ano"], str(row["DIST"])
        if fkey in feature_rows and feature_rows[fkey] != row["features"]:
            raise ValueError("Features wide conflitantes para ANO+DIST; use colunas qualificadas por ativo")
        feature_rows[fkey] = row["features"]
    wide = []
    for (year, dist), features in sorted(feature_rows.items()):
        item = {"ANO": year, "DIST": dist}
        for name, spec in definitions.items():
            f = features.get(name, {})
            item[name] = f.get("valor")
            for suffix in SUFFIXES:
                v = f.get(suffix)
                item[name + "__" + suffix] = iso(v) if v is not None and suffix in {"referencia", "disponivel_em"} else v
        wide.append(item)
    schema = pa.schema([(column, pa.int32() if column == "ANO" else pa.float64() if column in {"VALOR_ALVO", "COBERTURA"}
                         else pa.bool_() if column in {"HOMOLOGADO", "RUPTURA_CADASTRAL", "NAO_SOMAR", "COMPARABILIDADE_VALIDADA"}
                         else pa.date32() if column in DATE_FIELDS else pa.string()) for column in FIELDS.values()] +
                       [("PROVENIENCIA_JSON", pa.string()), ("METADADOS_JSON", pa.string())])
    pq.write_table(pa.Table.from_pylist(target_rows, schema=schema), root / "targets.parquet", compression="zstd")
    pq.write_table(pa.Table.from_pylist(wide, schema=fschema), root / "features.parquet", compression="zstd")
    metadata = {k: v for k, v in panel.items() if k != "rows"}
    manifest = {"schema_version": "bdgd-parquet-1", "grain": "DIST_ANO", "target_key": ["ANO", "DIST", "OBJETIVO_ID", "METRICA"],
                "feature_key": ["ANO", "DIST"], "metadata": metadata,
                "sha256": {name: sha(root / name) for name in ("targets.parquet", "features.parquet")}}
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return manifest


def read_bundle(directory, registry):
    _, pq = arrow()
    root = Path(directory)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "bdgd-parquet-1" or manifest.get("grain") != "DIST_ANO":
        raise ValueError("Contrato/granularidade Parquet incompatível")
    if manifest.get("target_key") != ["ANO", "DIST", "OBJETIVO_ID", "METRICA"] or manifest.get("feature_key") != ["ANO", "DIST"]:
        raise ValueError("Chaves Parquet incompatíveis")
    for name in ("targets.parquet", "features.parquet"):
        if sha(root / name) != manifest["sha256"].get(name):
            raise ValueError("Hash Parquet divergente: " + name)
    metadata = manifest["metadata"]
    definitions = metadata["feature_definitions"]
    features = pq.read_table(root / "features.parquet")
    if set(features.column_names) != set(_feature_schema(definitions).names):
        raise ValueError("Colunas wide não correspondem às definições de features")
    wide = {}
    for row in features.to_pylist():
        if not isinstance(row["ANO"], int) or isinstance(row["ANO"], bool) or not 1900 <= row["ANO"] <= 2100 or not str(row["DIST"]).isdigit() or int(row["DIST"]) <= 0:
            raise ValueError("Chave wide inválida")
        key = row["ANO"], str(row["DIST"])
        if key in wide:
            raise ValueError("Features wide duplicadas ANO+DIST")
        fs = {}
        for name, spec in definitions.items():
            if row[name + "__disponivel_em"] is None and row[name] is None:
                continue  # ausência real; não cria valor nem disponibilidade
            fs[name] = {"valor": row[name], "unidade": spec["unidade"]}
            for suffix in SUFFIXES:
                v = row[name + "__" + suffix]
                if suffix == "cenario_id" and v is None:
                    continue
                fs[name][suffix] = v.isoformat() if isinstance(v, date) else v
            iso(fs[name]["disponivel_em"]); iso(fs[name]["referencia"])
            if not fs[name]["fonte"] or (fs[name]["valor"] is not None and not (finite(fs[name]["valor"]) if spec["tipo"] == "numerica" else isinstance(fs[name]["valor"], str))):
                raise ValueError("Feature wide inválida")
        wide[key] = fs
    targets = pq.read_table(root / "targets.parquet")
    if set(targets.column_names) != set(FIELDS.values()) | {"PROVENIENCIA_JSON", "METADADOS_JSON"}:
        raise ValueError("Colunas long incompatíveis")
    rows, keys, last = [], set(), {}
    for row in targets.to_pylist():
        key = row["ANO"], str(row["DIST"]), row["OBJETIVO_ID"], row["METRICA"]
        if key in keys:
            raise ValueError("Alvos long duplicados")
        keys.add(key)
        if key[:2] not in wide:
            raise ValueError("Alvo sem linha correspondente no painel wide ANO+DIST")
        item = json.loads(row["METADADOS_JSON"])
        if any(k in item for k in FIELDS) or "features" in item or "territorio" in item:
            raise ValueError("Metadados tentam sobrescrever campos do contrato")
        item.update({field: row[column].isoformat() if isinstance(row[column], date) else row[column] for field, column in FIELDS.items()})
        item.update({"territorio": {"nivel": "dist", "id": str(row["DIST"])}, "features": wide[key[:2]],
                     "proveniencia": json.loads(row["PROVENIENCIA_JSON"])})
        rows.append(item)
        skey = key[1:]
        if skey not in last or key[0] > last[skey]["ano"]:
            last[skey] = item
    max_year = max((row["ano"] for row in rows), default=0)
    # Cenários futuros wide são juntados sem fabricar observação do alvo.
    for (year, dist), fs in sorted(wide.items()):
        if year <= max_year:
            continue
        for (d, _, _), previous in last.items():
            if d == dist:
                rows.append({**previous, "ano": year, "competencia": f"{year}-12-31", "valor_alvo": None,
                             "status_qualidade": "ausente", "features": fs, "homologado": False,
                             "status_homologacao": "NAO_DISPONIVEL", "ruptura": False, "disponivel_em": None,
                             "proveniencia": {"features_only": True, "parquet_sha256": manifest["sha256"]["features.parquet"]}})
    panel = {**metadata, "rows": rows}
    validate_panel(panel, registry)
    return panel


def write_results(report, directory):
    """Dados de resultado em Parquet; JSON permanece só para metadados e a visão web."""
    pa, pq = arrow()
    root = Path(directory)
    projections, folds, evaluations = [], [], []
    for series in report["series"]:
        dimensions = {"DIST": series["DIST"], "OBJETIVO_ID": series["objetivo_id"], "METRICA": series["metrica"],
                      "UNIDADE": series["unidade"], "NATUREZA_ALVO": series["natureza_alvo"]}
        for point in series["projecoes"]:
            projections.append({**dimensions, **point, "modelo": series["modelo_selecionado"], "previsao_validada": False})
        for c in series["candidatos"]:
            for point in c["folds"]:
                folds.append({**dimensions, "modelo": c["modelo"], **point})
            evaluations.append({**dimensions, "modelo": c["modelo"], "elegivel_selecao": c["elegivel_selecao"],
                                **c["metricas_diagnosticas"], "auditoria_mae": c["metricas_auditoria"]["mae"],
                                "falhas_json": json.dumps(c["falhas"], ensure_ascii=False),
                                "falha_projecao": c["falha_projecao"], "hiperparametros_json": json.dumps(c["hiperparametros"], sort_keys=True)})
    for name, data in [("projecoes", projections), ("backtests", folds), ("metricas", evaluations)]:
        table = pa.Table.from_pylist(data) if data else pa.table({"sem_linhas": pa.array([], type=pa.bool_())})
        pq.write_table(table, root / f"{name}.parquet", compression="zstd")
    manifest = {k: v for k, v in report.items() if k not in {"series", "comparacao_objetivos", "comparacao_familias"}}
    manifest["diagnosticos_series"] = [{k: v for k, v in series.items() if k not in {"candidatos", "historico", "projecoes", "proveniencia_treino"}} for series in report["series"]]
    manifest["interpretacao_amostral"] = "Linhas agregadas compartilham empresas, ativos e anos; não são observações independentes. São quatro anos por série, sem pooling nesta versão."
    manifest["sha256_resultados"] = {name: sha(root / name) for name in ("projecoes.parquet", "backtests.parquet", "metricas.parquet")}
    return manifest
