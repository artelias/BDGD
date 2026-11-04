"""Tabelas do relatório (07) a partir de 04_RESULTADOS_BACKTEST.csv e 05_COMPARACAO_MODELOS.csv: vencedor por métrica na etapa F entre os
três comparadores pré-especificados (candidato congelado, modelo atual, melhor baseline). Só leitura; não treina nada.

    python HOMOLOGACAO/CIENTIFICA/PILOTO_GRANULAR/tabelas_relatorio.py"""
import csv
import json
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ATUAL = {"ucbt": "ridge_painel", "trafo_qtd": "knn_analogos", "trafo_kva": "ridge_painel", "rede_bt": "ridge_painel", "rede_mt": "random_forest_painel"}
METRICAS = [("wape", "min"), ("mae", "min"), ("rmse", "min"), ("vies", "abs"), ("r2_estoque", "max"), ("r2_variacao", "max"), ("mae_variacao", "min"), ("r2_crescimento", "max")]


def main():
    r = list(csv.DictReader(open(AQUI / "04_RESULTADOS_BACKTEST.csv", encoding="utf-8")))
    comp = {x["ativo"]: x for x in csv.DictReader(open(AQUI / "05_COMPARACAO_MODELOS.csv", encoding="utf-8"))}
    linhas = []
    for a, c in comp.items():
        F = [x for x in r if x["ativo"] == a and x["etapa"] == "F"]
        cand = next(x for x in F if x["tipo"] == "granular_congelado")
        atual = next(x for x in F if x["tipo"] == "referencia_dist" and x["modelo"] == ATUAL[a])
        base = next(x for x in F if x["tipo"] == "referencia_dist" and x["modelo"] == c["melhor_baseline"])
        trio = {"candidato": cand, "atual": atual, "baseline": base}
        for m, regra in METRICAS:
            vals = {k: (None if v[m] in ("", "None") else float(v[m])) for k, v in trio.items()}
            ok = {k: v for k, v in vals.items() if v is not None}
            if not ok:
                venc = "N/D"
            elif regra == "min":
                venc = min(ok, key=ok.get)
            elif regra == "max":
                venc = max(ok, key=ok.get)
            else:
                venc = min(ok, key=lambda k: abs(ok[k]))
            linhas.append(dict(ativo=a, metrica=m, candidato=vals["candidato"], atual=vals["atual"], melhor_baseline=vals["baseline"], baseline=c["melhor_baseline"], vencedor=venc))
    with open(AQUI / "05b_VENCEDOR_POR_METRICA.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]), lineterminator="\n"); w.writeheader(); w.writerows(linhas)
    print(json.dumps([(x["ativo"], x["metrica"], x["vencedor"]) for x in linhas], ensure_ascii=False))


if __name__ == "__main__":
    main()
