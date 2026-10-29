"""Converte as respostas brutas do SIDRA/IBGE em um CSV municipal enxuto e versionável, com SHA-256 e URL de cada bruto.
Uso: python preparar_externas.py <raw_dir> <entrada_dir>"""
import csv
import hashlib
import json
import sys
from pathlib import Path

FONTES = {
    "pop_2010": ("pop_censo2010.json", "2010", "https://apisidra.ibge.gov.br/values/t/1378/n6/all/v/93/p/2010/c1/0/c2/0/c287/0/c455/0",
                 "IBGE Censo Demográfico 2010 — população residente (SIDRA 1378, v93)", "2011-11-29"),
    "pop_2022": ("pop_censo2022.json", "2022", "https://apisidra.ibge.gov.br/values/t/4709/n6/all/v/93/p/2022",
                 "IBGE Censo Demográfico 2022 — população residente, revisão de 31/08/2023 (SIDRA 4709, v93)", "2023-08-31"),
    "pop_2021": ("pop_estimativa_2021.json", "2021", "https://apisidra.ibge.gov.br/values/t/6579/n6/all/v/9324/p/2021",
                 "IBGE Estimativas da População 2021, ref. 01/07/2021 (SIDRA 6579, v9324)", "2021-08-27"),
    "pib_2021_mil_reais": ("pib_mun_2020_2023.json", "2021", "https://apisidra.ibge.gov.br/values/t/5938/n6/all/v/37/p/2020,2021,2022,2023",
                           "IBGE PIB dos Municípios 2021, preços correntes, mil R$ (SIDRA 5938, v37)", "2023-12-15"),
}


def main(raw, entrada):
    raw, entrada = Path(raw), Path(entrada)
    entrada.mkdir(parents=True, exist_ok=True)
    tab, man = {}, {}
    for col, (arq, per, url, desc, div) in FONTES.items():
        b = (raw / arq).read_bytes()
        man[col] = {"arquivo_bruto": arq, "sha256_bruto": hashlib.sha256(b).hexdigest(), "url": url, "descricao": desc,
                    "periodo": per, "divulgacao": div, "obtido_em": "2026-10-28"}
        for r in json.loads(b.decode("utf-8"))[1:]:
            if r.get("D3N") == per and r.get("V") not in (None, "", "-", "...", "X"):
                tab.setdefault(r["D1C"], {})[col] = r["V"]
    with open(entrada / "externas_ibge_municipal.csv", "w", encoding="utf-8", newline="\n") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["mun", *FONTES])
        for mun in sorted(tab):
            w.writerow([mun, *[tab[mun].get(c, "") for c in FONTES]])
    json.dump(man, open(entrada / "externas_ibge_manifesto.json", "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    print(len(tab), "municípios")


if __name__ == "__main__":
    main(*sys.argv[1:])
