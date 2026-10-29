"""Somente leitura de produtos existentes; nenhuma extração BDGD."""
import csv
import hashlib
import json
from pathlib import Path
from .contracts import SCHEMA
from .registry import fingerprint


def national_panel(directory, registry):
    root = Path(directory)
    manifest = json.loads((root / "MANIFESTO.json").read_text())
    filename = "serie_fisica_nacional.csv"
    # SHA-256 over LF-normalised text, like every other gate of the project (87_contrato_nacional.py, the .mjs validators): the
    # same contract must verify on a Windows checkout with CRLF (autocrlf) and on Linux.
    digest = hashlib.sha256((root / filename).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if digest != manifest["saidas"][filename]:
        raise ValueError("SHA-256 do contrato nacional divergente")
    rows = []
    with (root / filename).open(encoding="utf-8-sig", newline="") as handle:
        for r in csv.DictReader(handle):
            value = float(r["valor"]) if r["valor"].strip() else None
            state = r["estado"]
            # O rótulo legado sozinho não comprova verificação independente do zero.
            if value == 0:
                state = "zero_tecnico"
            rows.append({"ano": int(r["ano"]), "DIST": r["dist"], "empresa": r["empresa"],
                         "objetivo_id": r["conceitoId"], "metrica": r["metrica"], "unidade": r["unidade"],
                         "valor_alvo": value, "features": {}, "status_qualidade": state,
                         "cobertura": float(r["cobertura"]) if r["cobertura"].strip() else None,
                         "fonte": r["fonte"] or f"{manifest['versao']}/{filename}; fonte original não informada",
                         "competencia": f"{r['ano']}-12-31",
                         "territorio": {"nivel": "dist", "id": r["dist"]},
                         "perimetro_id": r["perimetroId"], "regra_versao": (
                             r["regraVersao"].replace("+republicacao-mais-recente", "") + "+republicacao-mais-recente"
                             if "republicacao-editorial" in manifest["versao"] else r["regraVersao"]),
                         "disponivel_em": None,  # data original de disponibilidade não consta no CSV
                         "ruptura": r["ruptura_desde_ano_anterior"].lower() == "true",
                         "nao_somar": r["nao_somar_em_agregados"].lower() == "true",
                         "ponte_pendente": bool(r["perimetroBridgeId"].strip()),
                         "homologado": r["fonte_homologada"].lower() == "true",
                         "status_homologacao": r["status_homologacao"],
                         "motivo": r["motivo_nd"], "proveniencia": {k: r.get(k, "") for k in
                         ("publicacao_id", "sha256", "status_homologacao", "tipo_lacuna", "tipo_ruptura", "intervalo_base", "dataBase", "observacao_id", "subtotal_observado", "valores_publicados_json")}})
    return {"schema_version": SCHEMA, "dataset_version": manifest["versao"], "sintetico": False,
            "source_sha256": digest, "registro_sha256": registry.get("catalog_sha256", fingerprint(registry)),
            "feature_definitions": {}, "rows": rows,
            "limites": ["Disponibilidade original das observações desconhecida: backtests retrospectivos, não point-in-time",
                        "Zeros do contrato legado sem prova independente não entram no treino",
                        "Atributos individuais e variáveis externas históricas não estão neste contrato"]}
