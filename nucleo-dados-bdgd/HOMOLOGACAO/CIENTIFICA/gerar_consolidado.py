"""Gera 09_ESTADO_POR_METRICA_E_HORIZONTE.csv a partir das avaliações já executadas (nada é treinado):
  * 03/04: Moderado publicado do produto, avaliação final 2024 → 2025 (h=1) e diagnóstico h=2, com os critérios pré-definidos (01);
  * PILOTO_GRANULAR/05: as cinco famílias do piloto granular/hierárquico (candidato congelado × modelo atual).
Horizontes 3–5 sempre NAO_HOMOLOGAVEL_COM_EVIDENCIA_ATUAL (não há origem com alvo a 3–5 anos em 2022–2025).

    python HOMOLOGACAO/CIENTIFICA/gerar_consolidado.py"""
import csv
import json
from pathlib import Path

AQUI = Path(__file__).resolve().parent
PILOTO = {"ucbt": None, "trafo_qtd": ("trafo_dist", "quantidade"), "trafo_kva": ("trafo_dist", "potencia_kva"),
          "rede_bt": ("rede_bt", "extensao_km"), "rede_mt": ("rede_mt", "extensao_km")}


def main():
    res = [r for r in csv.DictReader(open(AQUI / "03_RESULTADOS_BACKTEST.csv", encoding="utf-8")) if r["moderado_publicado"] == "True"]
    mat = {(r["conceito"], r["metrica"], r["horizonte"]): r for r in csv.DictReader(open(AQUI / "04_MATRIZ_APROVACAO_MODELOS.csv", encoding="utf-8"))
           if r["moderado_publicado"] == "True"}
    piloto = {r["ativo"]: r for r in csv.DictReader(open(AQUI / "PILOTO_GRANULAR/05_COMPARACAO_MODELOS.csv", encoding="utf-8"))}
    por_metrica = {}
    for a, k in PILOTO.items():
        if k:
            por_metrica[k] = piloto[a]
    linhas = []
    for r in sorted(res, key=lambda x: (x["conceito"], x["metrica"], int(x["horizonte"]))):
        k = (r["conceito"], r["metrica"])
        m = mat.get((*k, r["horizonte"]), {})
        p = por_metrica.get(k) if r["horizonte"] == "1" else None
        linhas.append(dict(conceito=k[0], metrica=k[1], horizonte=int(r["horizonte"]), modelo_publicado=r["modelo"], dist_avaliadas=r["n"], grupos=r["grupos"],
                           wape=r["wape"], mae=r["mae"], rmse=r["rmse"], vies=r["vies"], r2_crescimento=r["r2_crescimento"], r2_estoque=r["r2_estoque"],
                           melhor_baseline=r["melhor_baseline"], wape_melhor_baseline=r["wape_melhor_baseline"], ic95_dif_vs_baseline=r["ic95_dif_wape"],
                           estado_cientifico=m.get("nivel", ""), motivo=m.get("motivo", ""),
                           piloto_granular=(f"{p['classe']} ({p['candidato']} {p['nivel']}: WAPE {float(p['wape_candidato']):.4f} × atual {float(p['wape_modelo_atual']):.4f} na coorte do painel)" if p else "")))
        if r["horizonte"] == "2":
            for h in (3, 4, 5):
                linhas.append(dict(conceito=k[0], metrica=k[1], horizonte=h, modelo_publicado=r["modelo"], estado_cientifico="NAO_HOMOLOGAVEL_COM_EVIDENCIA_ATUAL",
                                   motivo="2022–2025 não tem origem com alvo a 3–5 anos; competências anteriores a 2022 excluídas pela diretriz de 04/11/2026"))
    p = piloto["ucbt"]
    linhas.append(dict(conceito="ucbt (painel Motor V2)", metrica="quantidade", horizonte=1, modelo_publicado="ridge_painel (Moderado de consumidores, reexecutado)",
                       estado_cientifico="SEM_AVALIACAO_DO_PUBLICADO", motivo="UCBT não é conceito do produto público; só o piloto o avaliou",
                       piloto_granular=f"{p['classe']} ({p['candidato']} {p['nivel']}: WAPE {float(p['wape_candidato']):.4f} × atual {float(p['wape_modelo_atual']):.4f})"))
    with open(AQUI / "09_ESTADO_POR_METRICA_E_HORIZONTE.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(dict.fromkeys(c for r in linhas for c in r)), lineterminator="\n"); w.writeheader(); w.writerows(linhas)
    cont = {}
    for r in linhas:
        cont.setdefault(r["horizonte"], {}).setdefault(r["estado_cientifico"], 0)
        cont[r["horizonte"]][r["estado_cientifico"]] += 1
    print(json.dumps(cont, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
