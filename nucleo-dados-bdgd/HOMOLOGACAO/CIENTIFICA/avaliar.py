"""Avaliação científica conforme 01_PROTOCOLO_VALIDACAO.md (critérios pré-definidos). Não treina nada: lê os erros ponto a ponto
da otimização experimental (origem final 2024 → 2025, h=1; diagnóstico 2023 → 2025, h=2) e o produto publicado.

    python HOMOLOGACAO/CIENTIFICA/avaliar.py <PONTOS_AVALIACAO.csv> <cenarios-motor.json> <indice_motor_v2.json> <saida_dir>

Saídas: 03_RESULTADOS_BACKTEST.csv (métricas e IC por modelo, métrica e horizonte) e 04_MATRIZ_APROVACAO_MODELOS.csv (nível por critério)."""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

SEMENTE, REPLICAS = 20261103, 2000
BASELINES = ("persistencia", "deriva", "crescimento_geometrico")
MIN_DIST_VALIDADO, MIN_PONTOS = 20, 10
VIES_VALIDADO, VIES_REPROVADO = 0.05, 0.10


def wape(y, yh):
    return float(np.abs(yh - y).sum() / np.abs(y).sum())


def r2(a, b):
    if len(a) < 5:
        return None
    sst = float(((a - a.mean()) ** 2).sum())
    return None if sst <= 0 else 1 - float(((a - b) ** 2).sum()) / sst


def bootstrap(dists, grupo, y, ym, yb, rng):
    """IC95% percentil da diferença e da razão de WAPE (modelo − baseline), reamostrando grupos econômicos inteiros."""
    gs = sorted({grupo.get(d, d) for d in dists})
    idx = {g: [i for i, d in enumerate(dists) if grupo.get(d, d) == g] for g in gs}
    dif, raz = [], []
    for _ in range(REPLICAS):
        sel = [i for g in rng.choice(gs, size=len(gs), replace=True) for i in idx[g]]
        a, b = wape(y[sel], ym[sel]), wape(y[sel], yb[sel])
        dif.append(a - b); raz.append(a / b if b > 0 else np.nan)
    return [float(np.percentile(dif, 2.5)), float(np.percentile(dif, 97.5))], [float(np.nanpercentile(raz, 2.5)), float(np.nanpercentile(raz, 97.5))], len(gs)


def nivel(r, moderado_publicado):
    """Critérios da seção 6, nesta ordem."""
    if r["horizonte"] != 1:
        return "NAO_HOMOLOGAVEL_COM_EVIDENCIA_ATUAL", "horizonte sem origem final independente (só diagnóstico 2023 → 2025)"
    if r["metrica"] == "potencia_kva":
        return "NAO_HOMOLOGAVEL_COM_EVIDENCIA_ATUAL", "métrica experimental (potência via EQ→UN, não homologada)"
    if r["n"] < MIN_PONTOS:
        return "NAO_HOMOLOGAVEL_COM_EVIDENCIA_ATUAL", f"{r['n']} pontos de avaliação < {MIN_PONTOS}"
    lo, hi = r["ic95_dif_wape"]
    if lo > 0 or abs(r["vies"]) > VIES_REPROVADO:
        return "REPROVADO", ("IC95% da diferença de WAPE contra o melhor baseline totalmente > 0" if lo > 0 else f"viés {r['vies']:+.1%} fora de ±10%")
    restr = "1 origem final, h=1" + ("; avaliação final NÃO independente da seleção do Moderado publicado" if moderado_publicado else "")
    if hi < 0 and abs(r["vies"]) <= VIES_VALIDADO and r["n"] >= MIN_DIST_VALIDADO:
        return "VALIDADO_RETROSPECTIVAMENTE_COM_RESTRICOES", restr
    if r["wape"] < r["wape_melhor_baseline"]:
        return "EXPERIMENTAL", "melhor que o baseline na estimativa pontual, sem IC95% totalmente negativo" + ("" if r["n"] >= MIN_DIST_VALIDADO else f" ({r['n']} DIST < {MIN_DIST_VALIDADO})")
    return "EXPERIMENTAL", "não supera o melhor baseline na estimativa pontual (IC95% inclui zero)"


def main(pontos_csv, publicado, indice_v2, saida):
    saida = Path(saida); saida.mkdir(parents=True, exist_ok=True)
    pub = json.loads(Path(publicado).read_text(encoding="utf-8"))
    mod_pub = {(m["conceito"], m["metrica"]): m["cenarios"]["moderado"] for m in pub["metricas"]}
    grupo = {str(d["dist"]): d["grupo"] or str(d["dist"]) for d in json.loads(Path(indice_v2).read_text(encoding="utf-8"))["dists"]}
    pts = defaultdict(list)
    for r in csv.DictReader(open(pontos_csv, encoding="utf-8")):
        pts[(r["conceito"], r["metrica"], r["etapa"], r["modelo"], r["origem"])].append((r["DIST"], float(r["y_origem"]), float(r["y_observado"]), float(r["y_previsto"])))
    rng = np.random.default_rng(SEMENTE)
    res, mat = [], []
    chaves = sorted({(c, m, e) for c, m, e, _, _ in pts})
    for conc, metr, etapa in chaves:
        h = 1 if etapa == "F" else 2
        base = {b: pts.get((conc, metr, etapa, b, "baseline")) for b in BASELINES}
        base = {b: v for b, v in base.items() if v}
        if not base:
            continue
        for (c2, m2, e2, modelo, origem), lista in sorted(pts.items()):
            if (c2, m2, e2) != (conc, metr, etapa):
                continue
            d = [p[0] for p in lista]
            y0 = np.array([p[1] for p in lista]); y = np.array([p[2] for p in lista]); ym = np.array([p[3] for p in lista])
            # um baseline é comparado com os OUTROS baselines (comparar consigo mesmo daria diferença zero por construção)
            bmap = {b: {p[0]: p[3] for p in v} for b, v in base.items() if b != modelo}
            comuns = [i for i, x in enumerate(d) if all(x in bm for bm in bmap.values())]
            if len(comuns) < 3:
                continue
            d = [d[i] for i in comuns]; y0, y, ym = y0[comuns], y[comuns], ym[comuns]
            wb = {b: wape(y, np.array([bmap[b][x] for x in d])) for b in bmap}
            melhor = min(wb, key=wb.get)
            yb = np.array([bmap[melhor][x] for x in d])
            ic, icr, ngr = bootstrap(d, grupo, y, ym, yb, rng)
            # robustez: sem as 5% maiores variações relativas observadas
            var = np.abs(np.log(y / y0)); corte = np.quantile(var, 0.95)
            k = var <= corte
            r = dict(conceito=conc, metrica=metr, modelo=modelo, origem_modelo=origem, moderado_publicado=modelo == mod_pub.get((conc, metr)),
                     etapa="final_2024_2025" if etapa == "F" else "diagnostico_2023_2025", horizonte=h, n=len(d), grupos=ngr,
                     wape=wape(y, ym), mae=float(np.abs(ym - y).mean()), rmse=float(np.sqrt(((ym - y) ** 2).mean())), vies=float((ym - y).sum() / y.sum()),
                     r2_crescimento=r2(np.log(y / y0), np.log(np.maximum(ym, 1e-9) / y0)), r2_estoque=r2(y, ym),
                     melhor_baseline=melhor, wape_melhor_baseline=wb[melhor], dif_wape=wape(y, ym) - wb[melhor],
                     ic95_dif_wape=ic, ic95_razao_wape=icr, wape_sem_outliers=wape(y[k], ym[k]), wape_baseline_sem_outliers=wape(y[k], yb[k]))
            nv, mot = nivel(r, r["moderado_publicado"])
            r["nivel"], r["motivo"] = nv, mot
            # sensibilidade: o veredito muda sem os outliers?
            r["sensibilidade_outliers"] = "mantem_sinal" if np.sign(r["wape_sem_outliers"] - r["wape_baseline_sem_outliers"]) == np.sign(r["dif_wape"]) else "INVERTE_SINAL"
            res.append(r)
    def fmt(v):
        return json.dumps([round(x, 6) for x in v]) if isinstance(v, list) else (round(v, 6) if isinstance(v, float) else v)
    campos = list(res[0])
    with open(saida / "03_RESULTADOS_BACKTEST.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, lineterminator="\n"); w.writeheader(); w.writerows({k: fmt(v) for k, v in r.items()} for r in res)
    # matriz: um nível por (métrica, modelo, horizonte); horizontes 3 e 5 explicitamente não homologáveis
    for r in res:
        mat.append(dict(conceito=r["conceito"], metrica=r["metrica"], modelo=r["modelo"], origem_modelo=r["origem_modelo"], moderado_publicado=r["moderado_publicado"],
                        horizonte=r["horizonte"], nivel=r["nivel"], motivo=r["motivo"], n=r["n"], wape=fmt(r["wape"]), wape_melhor_baseline=fmt(r["wape_melhor_baseline"]),
                        ic95_dif_wape=fmt(r["ic95_dif_wape"]), vies=fmt(r["vies"]), sensibilidade_outliers=r["sensibilidade_outliers"]))
    for conc, metr in sorted({(r["conceito"], r["metrica"]) for r in res}):
        for hh in (3, 5):
            mat.append(dict(conceito=conc, metrica=metr, modelo="todos", origem_modelo="", moderado_publicado="", horizonte=hh, nivel="NAO_HOMOLOGAVEL_COM_EVIDENCIA_ATUAL",
                            motivo="2022–2025 não permite origem com alvo a 3 ou 5 anos; exige competências anteriores a 2022 (ver 02)", n=0))
    with open(saida / "04_MATRIZ_APROVACAO_MODELOS.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(mat[0]), lineterminator="\n"); w.writeheader(); w.writerows(mat)
    cont = defaultdict(lambda: defaultdict(int))
    for r in mat:
        cont["todos"][r["nivel"]] += 1
        if r.get("moderado_publicado") is True:
            cont[f"moderado_publicado_h{r['horizonte']}"][r["nivel"]] += 1
    print(json.dumps({k: dict(v) for k, v in cont.items()}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:5])
