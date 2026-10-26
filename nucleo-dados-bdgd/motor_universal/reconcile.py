"""Agregação opt-in com universo explícito e prova de disjunção do fornecedor."""
from .contracts import finite


def reconcile(rows, *, expected_territories, coverage_complete=False, disjoint_evidence=None):
    if coverage_complete is not True or not isinstance(disjoint_evidence, str) or not disjoint_evidence:
        return {"valor": None, "motivo": "COBERTURA_OU_DISJUNCAO_NAO_COMPROVADA"}
    if not rows or any(r.get("nao_somar", False) or r.get("valor") is None for r in rows):
        return {"valor": None, "motivo": "SERIE_AUSENTE_OU_NAO_SOMAVEL"}
    dimensions = {(r["ano"], r["objetivo_id"], r["metrica"], r["unidade"], r["perimetro_id"]) for r in rows}
    ids = [r["territorio_id"] for r in rows]
    if len(dimensions) != 1 or len(set(ids)) != len(ids) or len(set(expected_territories)) != len(expected_territories) or set(ids) != set(expected_territories):
        return {"valor": None, "motivo": "UNIVERSO_DUPLICADO_INCOMPLETO_OU_METRICAS_INCOMPATIVEIS"}
    if any(not finite(r["valor"]) or r["valor"] < 0 for r in rows):
        raise ValueError("Valor físico negativo")
    return {"valor": sum(r["valor"] for r in rows), "motivo": None,
            "evidencia_disjuncao": disjoint_evidence, "n_territorios": len(ids), "homologacao_automatica": False}
