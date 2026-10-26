"""Validação fechada do painel. Alvos ausentes nunca são imputados."""
from datetime import date
import math
from .registry import validate_registry

SCHEMA = "painel-bdgd-1"
OBSERVED = {"observado", "zero_verificado"}
STATES = OBSERVED | {"zero_tecnico", "ausente", "nao_homologado", "nao_aplicavel"}


def iso(value):
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError(f"Data inválida: {value}")
    return date.fromisoformat(value)


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def series_key(row):
    return (str(row["DIST"]), row["objetivo_id"], row["metrica"], row["territorio"]["nivel"],
            str(row["territorio"]["id"]), row["perimetro_id"], row["regra_versao"])


def validate_panel(panel, registry):
    targets = validate_registry(registry)
    if panel.get("schema_version") != SCHEMA or not panel.get("dataset_version"):
        raise ValueError("Versão do painel ausente/incompatível")
    if not isinstance(panel.get("sintetico"), bool):
        raise ValueError("Identifique explicitamente se o painel é sintético")
    definitions = panel.get("feature_definitions", {})
    if panel.get("territorial_mapping") is not None:
        from .territorial import validate_municipal_mapping
        validate_municipal_mapping(panel["territorial_mapping"])
    objective_ids = {key[0] for key in targets}
    for name, spec in definitions.items():
        if not name or spec.get("tipo") not in {"numerica", "categorica"} or not spec.get("unidade"):
            raise ValueError(f"Feature sem tipo/unidade: {name}")
        if "comparabilidade_validada" in spec and not isinstance(spec["comparabilidade_validada"], bool):
            raise ValueError("Comparabilidade da feature deve ser booleana")
        applies = spec.get("objetivos_aplicaveis", [])
        if not isinstance(applies, list) or len(set(applies)) != len(applies) or any(x not in objective_ids for x in applies):
            raise ValueError("Escopo da feature contém objetivo inválido/duplicado")
        if "permite_imputacao" in spec and not isinstance(spec["permite_imputacao"], bool):
            raise ValueError("Permissão de imputação deve ser booleana")
        for other in spec.get("dividir_por", []) + spec.get("interagir_com", []):
            if spec["tipo"] != "numerica" or definitions.get(other, {}).get("tipo") != "numerica":
                raise ValueError("Razões/interações exigem duas features numéricas declaradas")
    keys = set()
    for row in panel["rows"]:
        for field in ("ano", "DIST", "objetivo_id", "metrica", "unidade", "valor_alvo", "features",
                      "status_qualidade", "fonte", "competencia", "territorio", "perimetro_id", "regra_versao",
                      "disponivel_em", "ruptura", "nao_somar", "homologado", "status_homologacao", "cobertura"):
            if field not in row:
                raise ValueError(f"Campo obrigatório ausente: {field}")
        if not isinstance(row["ano"], int) or isinstance(row["ano"], bool) or not 1900 <= row["ano"] <= 2100:
            raise ValueError("Ano inválido")
        if str(row["DIST"]).isdigit() is False or int(row["DIST"]) <= 0:
            raise ValueError("DIST inválida")
        if str(int(row["DIST"])) != str(row["DIST"]):
            raise ValueError("DIST deve usar código canônico sem zeros à esquerda")
        target = targets.get((row["objetivo_id"], row["metrica"]))
        if target is None or row["unidade"] != target["unidade"]:
            raise ValueError("Objetivo/métrica/unidade incompatível")
        if iso(row["competencia"]).isoformat() != f"{row['ano']}-12-31":
            raise ValueError("Primeira versão aceita competências anuais completas")
        if row["disponivel_em"] is not None:
            if iso(row["disponivel_em"]) < iso(row["competencia"]):
                raise ValueError("Alvo observado disponibilizado antes de encerrar a competência")
        if row["cobertura"] is not None and (not finite(row["cobertura"]) or not 0 <= row["cobertura"] <= 1):
            raise ValueError("Cobertura inválida")
        if not row["fonte"] or not row["perimetro_id"] or not row["regra_versao"]:
            raise ValueError("Proveniência/perímetro/regra ausente")
        for b in ("ruptura", "nao_somar", "homologado"):
            if not isinstance(row[b], bool):
                raise ValueError(f"Booleano inválido: {b}")
        if "comparabilidade_validada" in row and not isinstance(row["comparabilidade_validada"], bool):
            raise ValueError("Comparabilidade do alvo deve ser booleana")
        if not isinstance(row["status_homologacao"], str) or not row["status_homologacao"]:
            raise ValueError("Status de homologação obrigatório")
        if (row["status_homologacao"] == "HOMOLOGADO") != row["homologado"]:
            raise ValueError("Estado de homologação contraditório")
        territory = row["territorio"]
        if territory.get("nivel") not in target.get("territorios", ["dist"]) or not str(territory.get("id", "")):
            raise ValueError("Granularidade territorial inválida")
        if territory["nivel"] == "dist" and str(territory["id"]) != str(row["DIST"]):
            raise ValueError("DIST não corresponde ao território")
        status, value = row["status_qualidade"], row["valor_alvo"]
        if status not in STATES:
            raise ValueError("Estado desconhecido")
        if status in OBSERVED | {"zero_tecnico"}:
            if not finite(value) or value < 0:
                raise ValueError("Alvo observado inválido")
            if target.get("tipo_alvo") == "contagem" and value != int(value):
                raise ValueError("Contagem observada fracionária")
            if status in {"zero_verificado", "zero_tecnico"} and value != 0:
                raise ValueError("Estado zero com valor diferente de zero")
            if value == 0 and status == "observado":
                raise ValueError("Zero exige classificação explícita")
            if status == "zero_verificado" and not row.get("evidencia_zero"):
                raise ValueError("Zero verificado exige evidência independente")
        elif value is not None:
            raise ValueError("Dado ausente/não aplicável/não homologado deve ser null")
        if not isinstance(row["features"], dict):
            raise ValueError("Features devem ser um objeto")
        for name, feature in row["features"].items():
            if name not in definitions or not isinstance(feature, dict):
                raise ValueError(f"Feature não declarada: {name}")
            spec = definitions[name]
            if spec.get("objetivos_aplicaveis") and row["objetivo_id"] not in spec["objetivos_aplicaveis"]:
                raise ValueError("Feature fora do escopo do objetivo")
            for field in ("valor", "disponivel_em", "referencia", "fonte", "unidade"):
                if field not in feature:
                    raise ValueError(f"Feature {name} sem {field}")
            iso(feature["disponivel_em"]); iso(feature["referencia"])
            if feature["unidade"] != spec["unidade"] or not isinstance(feature["fonte"], str) or not feature["fonte"].strip():
                raise ValueError("Unidade/fonte da feature incompatível")
            if "ruptura" in feature and not isinstance(feature["ruptura"], bool):
                raise ValueError("Ruptura da feature deve ser booleana")
            if feature.get("status_comparabilidade", "VALIDADA") not in {"VALIDADA", "PENDENTE", "INCOMPATIVEL"}:
                raise ValueError("Status de comparabilidade da feature inválido")
            if "versao" in feature and (not isinstance(feature["versao"], str) or not feature["versao"].strip()):
                raise ValueError("Versão da feature inválida")
            value = feature["valor"]
            if value is not None and not (finite(value) if spec["tipo"] == "numerica" else isinstance(value, str)):
                raise ValueError("Tipo inválido de feature")
        key = series_key(row) + (row["ano"],)
        if key in keys:
            raise ValueError(f"Chave duplicada: {key}")
        keys.add(key)
    return panel


def usable(row):
    return (row["status_qualidade"] in OBSERVED and row["cobertura"] == 1 and not row["nao_somar"]
            and not row.get("ponte_pendente", False) and row["status_homologacao"] not in {"BLOQUEADO", "PENDENTE_DECISAO", "NAO_DISPONIVEL"})


def contiguous_tail(rows):
    """Corta no último bloqueio, lacuna ou ruptura; jamais atravessa a quebra."""
    tail = []
    for row in sorted(rows, key=lambda r: r["ano"]):
        if not usable(row):
            tail = []
            continue
        if row["ruptura"] or (tail and row["ano"] != tail[-1]["ano"] + 1):
            tail = []
        tail.append(row)
    return tail
