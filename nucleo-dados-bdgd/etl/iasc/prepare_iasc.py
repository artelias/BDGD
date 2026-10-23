"""Prepara destaque IASC ANEEL por DIST+ano, exigindo de-para CNPJ auditado.

Entrada oficial: indice-aneel-satisfacao-consumidor.csv (ANEEL)
De-para (arquivo privado/curado): dist,ano,cnpj,status,fonte_vinculo
Saída pública: JSON só com DIST, ano, satisfação, fonte e versão.
Não faz correspondência fuzzy e não expõe CNPJ no artefato publicado.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

SOURCE_URL = ("https://dadosabertos.aneel.gov.br/dataset/"
              "indice-aneel-de-satisfacao-do-consumidor-iasc")
FIELDS = {"NumAno", "NumCNPJ", "MdaIndicadorSatisfacao"}

def cnpj(valor: str) -> str:
    digits = re.sub(r"\D", "", str(valor or ""))
    return digits if len(digits) == 14 else ""

def pontuacao(valor: str) -> float | None:
    t = str(valor or "").strip()
    if not t:
        return None
    t = t.replace(".", "").replace(",", ".") if "," in t else t
    try:
        result = float(t)
    except ValueError:
        return None
    return result if 0 <= result <= 100 else None

def preparar(iasc: list[dict], depara: list[dict], ano: int) -> tuple[list[dict], dict]:
    """Associa exclusivamente 1 DIST <-> 1 CNPJ oficial no ano escolhido."""
    if iasc and not FIELDS.issubset(iasc[0]):
        raise ValueError("CSV IASC sem colunas oficiais obrigatórias")
    if depara and not {"dist", "ano", "cnpj", "status", "fonte_vinculo"}.issubset(depara[0]):
        raise ValueError("De-para não contém os campos de auditoria")

    candidatos = [r for r in depara if str(r.get("ano", "")) == str(ano)
                  and r.get("status") == "verificado"
                  and str(r.get("fonte_vinculo", "")).startswith("https://")
                  and cnpj(r.get("cnpj", ""))]
    por_dist = Counter(str(r["dist"]) for r in candidatos)
    por_cnpj = Counter(cnpj(r["cnpj"]) for r in candidatos)

    linhas_iasc = {}
    for r in iasc:
        if str(r.get("NumAno", "")) != str(ano):
            continue
        chave = cnpj(r.get("NumCNPJ", ""))
        if chave:
            linhas_iasc.setdefault(chave, []).append(r)

    result, rejeitados = [], []
    for r in candidatos:
        dist = str(r["dist"])
        chave = cnpj(r["cnpj"])
        if not dist.isdigit() or por_dist[dist] != 1 or por_cnpj[chave] != 1:
            rejeitados.append({"dist": dist, "motivo": "correspondencia_ambigua"})
            continue
        linhas = linhas_iasc.get(chave, [])
        if len(linhas) != 1:
            rejeitados.append({"dist": dist, "motivo": "resultado_iasc_ausente_ou_duplicado"})
            continue
        nota = pontuacao(linhas[0].get("MdaIndicadorSatisfacao", ""))
        if nota is None:
            rejeitados.append({"dist": dist, "motivo": "nota_ausente_ou_invalida"})
            continue
        result.append({
            "dist": int(dist), "ano": ano, "indicador": "MdaIndicadorSatisfacao",
            "valor": nota, "fonte": SOURCE_URL,
            "fonte_vinculo": r["fonte_vinculo"], "status": "verificado"
        })
    result.sort(key=lambda x: x["dist"])
    return result, {
        "ano": ano, "candidatos_verificados": len(candidatos),
        "resultados_publicaveis": len(result), "rejeitados": rejeitados,
        "observacao": "Satisfação IASC, não índice composto nem medida BDGD; não estimar notas ausentes."
    }

def ler_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        primeira_linha = f.readline()
        f.seek(0)
        return list(csv.DictReader(f, delimiter=";" if ";" in primeira_linha else ","))

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iasc", type=Path, required=True, help="CSV oficial ANEEL local")
    parser.add_argument("--depara", type=Path, required=True, help="DIST/ano/CNPJ com fonte comprovada")
    parser.add_argument("--ano", type=int, default=2025)
    parser.add_argument("--saida", type=Path, required=True)
    args = parser.parse_args()
    result, qa = preparar(ler_csv(args.iasc), ler_csv(args.depara), args.ano)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(json.dumps({"dados": result, "qa": qa}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"publicaveis": len(result), "rejeitados": len(qa["rejeitados"])}))

if __name__ == "__main__":
    main()
