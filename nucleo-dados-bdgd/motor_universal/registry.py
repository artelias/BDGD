"""Adaptador de catálogo; não redefine populações nem soma UN* com EQ*."""
import hashlib
import json
from pathlib import Path


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode()).hexdigest()


def registry_from_catalog(catalog):
    targets = []
    for asset in catalog["ativos"]:
        concept = catalog["conceitos"][asset["conceito"]]
        for metric in concept["medidas"]:
            if metric not in catalog["medidas"]:
                raise ValueError(f"Medida sem definição: {metric}")
            targets.append({
                "objetivo_id": asset["id"], "nome": asset["nome"],
                "familia": asset["familia"], "conceito": asset["conceito"],
                "entidades": concept["entidades"], "metrica": metric,
                "unidade": catalog["medidas"][metric]["unidade"],
                "tipo_alvo": "contagem" if metric == "quantidade" else "continuo_nao_negativo",
                "padrao": metric == asset["medida"],
                "natureza_alvo": "estoque_fisico",
                "requer_comparabilidade": metric not in {"quantidade", "extensao_km"},
                "filtros": asset.get("filtro", {}),
                "atributos": sorted({d for cube in concept.get("cubos", {}).values() for d in cube}),
                "regra_agregacao": asset.get("tecnico", concept.get("descricao", "")),
                "granularidade_temporal": "anual", "territorios": ["dist", "municipio", "alimentador", "subestacao"],
                "status_qualidade": "definicao_catalogada_nao_homologa_observacoes",
                "elegibilidade": "avaliada_por_serie", "nao_somar_com_outros_objetivos": True,
            })
    result = {"schema_version": "objetivos-1", "catalog_version": catalog["versao"],
              "catalog_sha256": fingerprint(catalog), "objetivos": targets}
    validate_registry(result)
    return result


def validate_registry(registry):
    if registry.get("schema_version") != "objetivos-1" or not registry.get("objetivos"):
        raise ValueError("Registro de objetivos incompatível/vazio")
    keys = set()
    for t in registry["objetivos"]:
        for k in ("objetivo_id", "nome", "familia", "metrica", "unidade", "entidades", "regra_agregacao"):
            if not t.get(k):
                raise ValueError(f"Objetivo sem {k}")
        key = t["objetivo_id"], t["metrica"]
        if key in keys:
            raise ValueError(f"Objetivo duplicado: {key}")
        keys.add(key)
    return {(t["objetivo_id"], t["metrica"]): t for t in registry["objetivos"]}
