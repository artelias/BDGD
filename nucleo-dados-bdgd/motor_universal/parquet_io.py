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
CONTROLS = ("status_comparabilidade", "evidencia_comparabilidade", "ruptura", "versao")


def arrow():
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise ValueError("Instale motor_universal/requirements.txt para ingestão Parquet") from exc
    return pa, pq


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _feature_schema(definitions, *, scoped=False, version=2):
    pa, _ = arrow()
    fields = [("ANO", pa.int32()), ("DIST", pa.string())]
    if scoped:
        fields.append(("OBJETIVO_ID", pa.string()))
    for name, spec in sorted(definitions.items()):
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name) or "__" in name or name in {"ANO", "DIST", "OBJETIVO_ID"}:
            raise ValueError("Nome de feature wide inválido/reservado")
        fields.append((name, pa.float64() if spec["tipo"] == "numerica" else pa.string()))
        fields += [(name + "__" + suffix, pa.date32() if suffix in {"disponivel_em", "referencia"} else pa.string()) for suffix in SUFFIXES]
        if version == 2:
            fields += [(name + "__" + suffix, pa.bool_() if suffix == "ruptura" else pa.string()) for suffix in CONTROLS]
    return pa.schema(fields)


def _target_schema():
    pa, _ = arrow()
    return pa.schema([(column, pa.int32() if column == "ANO" else pa.float64() if column in {"VALOR_ALVO", "COBERTURA"}
                      else pa.bool_() if column in {"HOMOLOGADO", "RUPTURA_CADASTRAL", "NAO_SOMAR", "COMPARABILIDADE_VALIDADA"}
                      else pa.date32() if column in DATE_FIELDS else pa.string()) for column in FIELDS.values()] +
                     [("PROVENIENCIA_JSON", pa.string()), ("METADADOS_JSON", pa.string())])


def _check_schema(table, expected):
    if len(table.column_names) != len(set(table.column_names)) or set(table.column_names) != set(expected.names):
        raise ValueError("Colunas Parquet incompatíveis/duplicadas")
    if any(table.schema.field(f.name).type != f.type for f in expected):
        raise ValueError("Tipos Parquet incompatíveis com o contrato")


def _merge_features(store, key, values):
    dest = store.setdefault(key, {})
    for name, feature in values.items():
        if name in dest and dest[name] != feature:
            raise ValueError("Features wide conflitantes na mesma chave; não multiplicar observações")
        dest[name] = feature


def _write_wide(pq, pa, root, filename, values, definitions, *, scoped=False):
    wide = []
    for key, features in sorted(values.items()):
        item = {"ANO": key[0], "DIST": key[1]}
        if scoped:
            item["OBJETIVO_ID"] = key[2]
        for name in definitions:
            f = features.get(name, {})
            item[name] = f.get("valor")
            for suffix in SUFFIXES + CONTROLS:
                v = f.get(suffix)
                item[name + "__" + suffix] = iso(v) if v is not None and suffix in {"referencia", "disponivel_em"} else v
        wide.append(item)
    pq.write_table(pa.Table.from_pylist(wide, schema=_feature_schema(definitions, scoped=scoped)), root / filename, compression="zstd")


def write_bundle(panel, registry, directory):
    validate_panel(panel, registry)
    pa, pq = arrow()
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=False)
    target_rows, feature_rows, scoped_rows, target_keys = [], {}, {}, set()
    definitions = panel["feature_definitions"]
    shared_defs = {n: s for n, s in definitions.items() if not s.get("objetivos_aplicaveis")}
    scoped_defs = {n: s for n, s in definitions.items() if s.get("objetivos_aplicaveis")}
    _feature_schema(definitions)
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
        _merge_features(feature_rows, fkey, {n: f for n, f in row["features"].items() if n in shared_defs})
        if scoped_defs:
            _merge_features(scoped_rows, (*fkey, row["objetivo_id"]), {n: f for n, f in row["features"].items() if n in scoped_defs})
    pq.write_table(pa.Table.from_pylist(target_rows, schema=_target_schema()), root / "targets.parquet", compression="zstd")
    _write_wide(pq, pa, root, "features.parquet", feature_rows, shared_defs)
    filenames = ["targets.parquet", "features.parquet"]
    if scoped_defs:
        _write_wide(pq, pa, root, "features_objetivo.parquet", scoped_rows, scoped_defs, scoped=True)
        filenames.append("features_objetivo.parquet")
    metadata = {k: v for k, v in panel.items() if k != "rows"}
    manifest = {"schema_version": "bdgd-parquet-2", "grain": "DIST_ANO", "target_key": ["ANO", "DIST", "OBJETIVO_ID", "METRICA"],
                "feature_key": ["ANO", "DIST"], "metadata": metadata,
                "objective_feature_key": ["ANO", "DIST", "OBJETIVO_ID"] if scoped_defs else None,
                "sha256": {name: sha(root / name) for name in filenames}}
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return manifest


def _read_wide(root, filename, definitions, *, scoped=False, version=2):
    _, pq = arrow()
    table = pq.read_table(root / filename)
    _check_schema(table, _feature_schema(definitions, scoped=scoped, version=version))
    result = {}
    for row in table.to_pylist():
        if row["ANO"] is None or row["DIST"] is None or not 1900 <= row["ANO"] <= 2100 or not str(row["DIST"]).isdigit() or int(row["DIST"]) <= 0 or str(int(row["DIST"])) != row["DIST"]:
            raise ValueError("Chave wide inválida")
        key = (row["ANO"], row["DIST"], row["OBJETIVO_ID"]) if scoped else (row["ANO"], row["DIST"])
        if key in result:
            raise ValueError("Features wide duplicadas na chave declarada")
        fs = {}
        for name, spec in definitions.items():
            suffixes = SUFFIXES + (CONTROLS if version == 2 else ())
            if row[name] is None and all(row[name + "__" + x] is None for x in suffixes):
                continue
            f = {"valor": row[name], "unidade": spec["unidade"]}
            for suffix in suffixes:
                v = row[name + "__" + suffix]
                if v is None and suffix not in {"disponivel_em", "referencia", "fonte"}:
                    continue
                f[suffix] = v.isoformat() if isinstance(v, date) else v
            iso(f["disponivel_em"]); iso(f["referencia"])
            if not f["fonte"] or (f["valor"] is not None and not (finite(f["valor"]) if spec["tipo"] == "numerica" else isinstance(f["valor"], str))):
                raise ValueError("Feature wide inválida: fonte/tipo")
            if scoped and key[2] not in spec["objetivos_aplicaveis"]:
                raise ValueError("Feature fora do escopo do objetivo")
            fs[name] = f
        result[key] = fs
    return result


def read_bundle(directory, registry):
    _, pq = arrow()
    root = Path(directory)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    schema = manifest.get("schema_version")
    if schema not in {"bdgd-parquet-1", "bdgd-parquet-2"} or manifest.get("grain") != "DIST_ANO":
        raise ValueError("Contrato/granularidade Parquet incompatível; municipal requer contrato territorial v2")
    version = 1 if schema == "bdgd-parquet-1" else 2
    if manifest.get("target_key") != ["ANO", "DIST", "OBJETIVO_ID", "METRICA"] or manifest.get("feature_key") != ["ANO", "DIST"]:
        raise ValueError("Chaves Parquet incompatíveis")
    metadata = manifest["metadata"]
    definitions = metadata["feature_definitions"]
    scoped_defs = {n: s for n, s in definitions.items() if s.get("objetivos_aplicaveis")} if version == 2 else {}
    shared_defs = {n: s for n, s in definitions.items() if n not in scoped_defs}
    filenames = {"targets.parquet", "features.parquet"} | ({"features_objetivo.parquet"} if scoped_defs else set())
    if set(manifest["sha256"]) != filenames:
        raise ValueError("Arquivos declarados incompatíveis com o contrato")
    if version == 2 and manifest.get("objective_feature_key") != (["ANO", "DIST", "OBJETIVO_ID"] if scoped_defs else None):
        raise ValueError("Chave de features por objetivo incompatível")
    for name in filenames:
        if sha(root / name) != manifest["sha256"][name]:
            raise ValueError("Hash Parquet divergente: " + name)
    wide = _read_wide(root, "features.parquet", shared_defs, version=version)
    scoped = _read_wide(root, "features_objetivo.parquet", scoped_defs, scoped=True) if scoped_defs else {}
    targets = pq.read_table(root / "targets.parquet")
    _check_schema(targets, _target_schema())
    rows, keys, last = [], set(), {}
    for row in targets.to_pylist():
        key = row["ANO"], row["DIST"], row["OBJETIVO_ID"], row["METRICA"]
        if key in keys:
            raise ValueError("Alvos long duplicados")
        keys.add(key)
        if key[:2] not in wide:
            raise ValueError("Alvo sem linha correspondente no painel wide ANO+DIST")
        item = json.loads(row["METADADOS_JSON"])
        if any(k in item for k in FIELDS) or any(k in item for k in ("features", "territorio", "proveniencia")):
            raise ValueError("Metadados tentam sobrescrever campos do contrato")
        item.update({field: row[column].isoformat() if isinstance(row[column], date) else row[column] for field, column in FIELDS.items()})
        fs = {**wide[key[:2]], **scoped.get(key[:3], {})}
        # V1 guardava todas as features no mesmo wide, mesmo as de outros ativos.
        fs = {n: f for n, f in fs.items() if not definitions[n].get("objetivos_aplicaveis") or key[2] in definitions[n]["objetivos_aplicaveis"]}
        item.update({"territorio": {"nivel": "dist", "id": row["DIST"]}, "features": fs,
                     "proveniencia": json.loads(row["PROVENIENCIA_JSON"])})
        rows.append(item)
        skey = key[1:]
        if skey not in last or key[0] > last[skey]["ano"]:
            last[skey] = item
    # Cenários são associados por série, nunca pelo maior ano global de outra DIST.
    for (dist, objective, metric), previous in sorted(last.items()):
        years = {y for y, d in wide if d == dist} | {y for y, d, o in scoped if d == dist and o == objective}
        for year in sorted(years):
            if year <= previous["ano"]:
                continue
            fs = {**wide.get((year, dist), {}), **scoped.get((year, dist, objective), {})}
            fs = {n: f for n, f in fs.items() if not definitions[n].get("objetivos_aplicaveis") or objective in definitions[n]["objetivos_aplicaveis"]}
            rows.append({**previous, "ano": year, "competencia": f"{year}-12-31", "valor_alvo": None,
                         "status_qualidade": "ausente", "features": fs, "homologado": False,
                         "status_homologacao": "NAO_DISPONIVEL", "ruptura": False, "disponivel_em": None,
                         "proveniencia": {"features_only": True, "bundle_sha256": manifest["sha256"]}})
    # Linhas órfãs não desaparecem silenciosamente nem criam um novo universo de alvos.
    known_dists = {k[0] for k in last}
    known_objectives = {(k[0], k[1]) for k in last}
    if any(d not in known_dists for _, d in wide) or any((d, o) not in known_objectives for _, d, o in scoped):
        raise ValueError("Feature órfã: DIST/objetivo sem alvo declarado")
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
