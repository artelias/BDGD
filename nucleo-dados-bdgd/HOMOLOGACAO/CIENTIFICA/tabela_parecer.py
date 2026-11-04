"""Tabela h=1 do parecer consolidado (10) a partir de 09_ESTADO_POR_METRICA_E_HORIZONTE.csv. Só formata; não calcula modelos.

    python HOMOLOGACAO/CIENTIFICA/tabela_parecer.py   # imprime a tabela Markdown em UTF-8 no arquivo tabela_h1.md"""
import csv
import json
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ROT = {"VALIDADO_RETROSPECTIVAMENTE_COM_RESTRICOES": "validado (restrições)", "EXPERIMENTAL": "experimental",
       "NAO_HOMOLOGAVEL_COM_EVIDENCIA_ATUAL": "não homologável", "SEM_AVALIACAO_DO_PUBLICADO": "—"}
PIL = {"VALIDADO_RETROSPECTIVAMENTE_COM_RESTRICOES": "validado restrito (kVA experimental)", "SEM_GANHO": "sem ganho", "REJEITADO": "rejeitado"}


def br(x, casas):
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v, casas=2):
    return "N/D" if v in ("", None, "None") else br(float(v) * 100, casas) + "%"


def num(v):
    return "N/D" if v in ("", None, "None") else br(float(v), 1 if abs(float(v)) < 100 else 0)   # erro médio: estatística contínua


def main():
    out = ["| Métrica | Moderado publicado | DIST / grupos | WAPE | Melhor baseline (WAPE) | IC95% dif. vs baseline (p.p.) | MAE | RMSE | Viés | R² crescimento | Estado h=1 | Piloto granular |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in csv.DictReader(open(AQUI / "09_ESTADO_POR_METRICA_E_HORIZONTE.csv", encoding="utf-8")):
        if r["horizonte"] != "1":
            continue
        ic = json.loads(r["ic95_dif_vs_baseline"]) if r.get("ic95_dif_vs_baseline") else None
        icx = f"[{br(ic[0] * 100, 2)}; {br(ic[1] * 100, 2)}]" if ic else "N/D"
        r2 = "N/D" if r.get("r2_crescimento") in ("", None, "None") else br(float(r["r2_crescimento"]), 3)
        pil = PIL.get((r.get("piloto_granular") or "").split(" (")[0], "—")
        base = f"{r['melhor_baseline']} ({pct(r['wape_melhor_baseline'])})" if r.get("melhor_baseline") else "—"
        out.append(f"| {r['conceito']} / {r['metrica']} | {r['modelo_publicado']} | {r.get('dist_avaliadas') or '—'} / {r.get('grupos') or '—'} | {pct(r.get('wape'))} | {base} | {icx} | "
                   f"{num(r.get('mae'))} | {num(r.get('rmse'))} | {pct(r.get('vies'), 1)} | {r2} | {ROT.get(r['estado_cientifico'], r['estado_cientifico'])} | {pil} |")
    (AQUI / "tabela_h1.md").write_text("\n".join(out) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
