"""Tabelas em Markdown e RESUMO.json a partir das saídas de recuperar.py (não recalcula nada).

    python HOMOLOGACAO/CIENTIFICA/RECUPERACAO_CENARIOS/tabelas.py <saida_dir> [<MATRIZ_MODELOS_OTIMIZADOS.csv>]
"""
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

LADOS = ("conservador", "agressivo")
GRUPO_CAUSA = {"I": "selecao", "A1": "evidencia_de_modelo", "A2": "evidencia_de_modelo", "B": "evidencia_de_modelo", "C": "evidencia_de_modelo",
               "D": "evidencia_de_modelo", "E": "evidencia_de_modelo", "F": "dados", "G": "dados", "H": "dados", "J": "outra"}


def br(n):
    return f"{n:,}".replace(",", ".")


def pct(a, b):
    return f"{100 * a / b:.1f}%".replace(".", ",") if b else "—"


def tabela(cab, linhas):
    out = ["| " + " | ".join(cab) + " |", "|" + "---|" * len(cab)]
    out += ["| " + " | ".join(str(x) for x in l) + " |" for l in linhas]
    return "\n".join(out)


def main(saida, matriz_otim=None):
    saida = Path(saida)
    rs = list(csv.DictReader(open(saida / "02_MATRIZ_SERIES_CENARIOS.csv", encoding="utf-8")))
    inv = list(csv.DictReader(open(saida / "03_INVENTARIO_MODELOS_EXISTENTES.csv", encoding="utf-8")))
    comp = list(csv.DictReader(open(saida / "05_COMPARACAO_RETROSPECTIVA.csv", encoding="utf-8")))
    res, md = {}, []
    n = len(rs)
    com_mod = [r for r in rs if r["completude_publicada"] != "SEM_PREVISAO"]
    sem_mod = [r for r in rs if r["completude_publicada"] == "SEM_PREVISAO"]
    pubc = Counter(r["completude_publicada"] for r in rs)
    res["universo"] = {"series": n, **pubc}
    # --- Gate A: causas dos extremos ausentes (séries com Moderado)
    aus = Counter(); aus_lado = defaultdict(Counter); pubrep = Counter(); pubrep_lado = defaultdict(Counter); aprov = Counter()
    for r in com_mod:
        for l in LADOS:
            c = r[f"causa_{l}"]
            if c.startswith("PUBLICADO_REPROVADO_"):
                pubrep[c.split("_")[-1]] += 1; pubrep_lado[l][c.split("_")[-1]] += 1
            elif c == "PUBLICADO_APROVADO":
                aprov[l] += 1
            else:
                aus[c] += 1; aus_lado[l][c] += 1
    res["gateA_extremos_ausentes_com_moderado"] = {"total": sum(aus.values()), "por_causa": dict(aus), "por_lado": {l: dict(v) for l, v in aus_lado.items()}}
    res["gateA_publicados"] = {"total": sum(aprov.values()) + sum(pubrep.values()), "aprovados": dict(aprov), "reprovados": dict(pubrep),
                               "reprovados_por_lado": {l: dict(v) for l, v in pubrep_lado.items()}}
    cm = Counter(r["causa_moderado"] for r in sem_mod)
    rec_dec = sum(1 for r in sem_mod if r["possibilidade_recuperacao"] == "MODERADO_RECUPERAVEL_SOB_DECISAO_DE_CONTRATO")
    res["gateA_moderado_ausente"] = {"total": len(sem_mod), "por_causa": dict(cm), "recuperavel_sob_decisao_de_contrato": rec_dec,
                                     "detalhes": dict(Counter(r["causa_moderado_detalhe"].split(":")[1].strip() if ":" in r["causa_moderado_detalhe"] else r["causa_moderado_detalhe"] for r in sem_mod).most_common(12))}
    grp = Counter()
    for c, v in aus.items():
        grp[GRUPO_CAUSA.get(c, "outra")] += v
    grp["dados"] += 2 * len(sem_mod)          # os extremos das séries sem Moderado (H)
    res["gateA_agrupamento_ausencias_extremos"] = dict(grp)
    # --- cobertura
    def classe(r, campo):
        v = r[campo] or r["classe_final"]
        return "COMPLETA" if v.startswith("COMPLETA") else v
    cob = {}
    for campo in ("completude_publicada", "completude_defensavel_antes", "classe_gateB_so_originais", "classe_gateB_originais_e_otimizados", "classe_gateB", "classe_final"):
        cob[campo] = dict(Counter(classe(r, campo) for r in rs))
    cob["classe_final_detalhe"] = dict(Counter(r["classe_final"] for r in rs))
    cob["classe_gateB_detalhe"] = dict(Counter(r["classe_gateB"] for r in rs))
    sem_kva = [r for r in rs if r["experimental_kva"] != "True"]
    cob["sem_kva"] = {"series": len(sem_kva), "publicado_completa": sum(r["completude_publicada"] == "COMPLETA" for r in sem_kva),
                      "defensavel_antes": sum(r["completude_defensavel_antes"] == "COMPLETA" for r in sem_kva),
                      "gateB": sum(r["classe_gateB"].startswith("COMPLETA") for r in sem_kva), "final": sum(r["classe_final"].startswith("COMPLETA") for r in sem_kva),
                      "final_independente": sum(r["classe_final"] == "COMPLETA_INDEPENDENTE" for r in sem_kva)}
    # recuperação por origem (série)
    orig = Counter()
    for r in rs:
        if r["completude_defensavel_antes"] == "COMPLETA":
            orig["ja_completa_defensavel"] += 1
        elif r["classe_gateB_so_originais"].startswith("COMPLETA"):
            orig["recuperada_so_originais"] += 1
        elif r["classe_gateB_originais_e_otimizados"].startswith("COMPLETA"):
            orig["recuperada_com_otimizados"] += 1
        elif r["classe_gateB"].startswith("COMPLETA"):
            orig["recuperada_com_condicional_existente_B_HIST"] += 1
        elif r["classe_final"].startswith("COMPLETA"):
            orig["recuperada_com_modelos_ou_condicionais_novos"] += 1
        elif r["classe_final"] == "PARCIAL":
            orig["continua_parcial"] += 1
        else:
            orig["continua_sem_previsao"] += 1
    cob["origem_da_completude_final"] = dict(orig)
    cats = Counter(); bloq = Counter()
    for r in com_mod:
        for l in LADOS:
            cats[r[f"{l}_final_categoria"]] += 1
            if r[f"{l}_final_categoria"] == "INDISPONIVEL":
                bloq[r[f"causa_final_{l}"]] += 1
    cob["extremos_final_por_categoria"] = dict(cats)
    cob["extremos_bloqueados_por_causa"] = dict(bloq)
    res["cobertura"] = cob
    # perdas: publicados completos que deixam de ser completos defensáveis
    perdas = Counter()
    for r in rs:
        if r["completude_publicada"] == "COMPLETA" and not r["classe_final"].startswith("COMPLETA"):
            perdas["completa_publicada_que_fica_parcial"] += 1
        if r["completude_publicada"] == "COMPLETA" and r["completude_defensavel_antes"] != "COMPLETA":
            perdas["completa_publicada_nao_defensavel_antes"] += 1
    res["perdas"] = dict(perdas)
    # --- por métrica e família
    pm = defaultdict(Counter); pf = defaultdict(Counter); pe = defaultdict(Counter)
    for r in rs:
        for d, key in ((pm, f"{r['conceito']}/{r['metrica']}"), (pf, r["familia"]), (pe, f"{r['DIST']} {r['empresa']}")):
            d[key]["series"] += 1
            d[key]["publicado"] += r["completude_publicada"] == "COMPLETA"
            d[key]["defensavel_antes"] += r["completude_defensavel_antes"] == "COMPLETA"
            d[key]["gateB"] += r["classe_gateB"].startswith("COMPLETA")
            d[key]["final"] += r["classe_final"].startswith("COMPLETA")
            d[key]["independente"] += r["classe_final"] == "COMPLETA_INDEPENDENTE"
            d[key]["condicional"] += r["classe_final"] in ("COMPLETA_MISTA", "COMPLETA_CONDICIONAL")
            d[key]["sem_previsao"] += r["classe_final"] == "SEM_PREVISAO"
    res["por_metrica"] = {k: dict(v) for k, v in pm.items()}
    res["por_familia"] = {k: dict(v) for k, v in pf.items()}
    res["por_empresa"] = {k: dict(v) for k, v in pe.items()}
    # --- modelos que preenchem extremos, por família
    fam_mod = defaultdict(Counter)
    for r in com_mod:
        for l in LADOS:
            if r[f"{l}_final_categoria"] not in ("INDISPONIVEL", "A_PUBLICADO_MANTIDO"):
                fam_mod[r["familia"]][r[f"{l}_final_modelo"]] += 1
    res["modelos_que_recuperam_por_familia"] = {k: dict(v.most_common(5)) for k, v in fam_mod.items()}
    # --- novos modelos: WAPE e R² contra o Moderado
    novos = []
    by = defaultdict(dict)
    for c in comp:
        by[(c["conceito"], c["metrica"], c["etapa"])][c["candidato"]] = c
    for (conc, metr, et), cs in sorted(by.items()):
        mod = next((c for c in cs.values() if c["moderado"] == "True"), None)
        if not mod:
            continue
        for nid in ("N1", "N2n", "N2g"):
            c = cs.get(nid)
            if not c:
                continue
            f = lambda x: float(x) if x not in ("", None) else None
            novos.append({"metrica": f"{conc}/{metr}", "etapa": et, "candidato": nid, "wape": f(c["wape"]), "wape_moderado": f(mod["wape"]),
                          "r2_cresc": f(c["r2_crescimento"]), "r2_cresc_moderado": f(mod["r2_crescimento"]), "ic_vs_moderado": c["ic95_dif_wape_vs_moderado"],
                          "competitivo": c["competitivo"]})
    resumo_n = {}
    for nid in ("N1", "N2n", "N2g"):
        for et in ("F", "PRODUTO"):
            xs = [x for x in novos if x["candidato"] == nid and x["etapa"] == et and x["wape"] is not None]
            ic_neg = sum(1 for x in xs if x["ic_vs_moderado"] and json.loads(x["ic_vs_moderado"])[1] < 0)
            ic_pos = sum(1 for x in xs if x["ic_vs_moderado"] and json.loads(x["ic_vs_moderado"])[0] > 0)
            r2m = sum(1 for x in xs if x["r2_cresc"] is not None and x["r2_cresc_moderado"] is not None and x["r2_cresc"] > x["r2_cresc_moderado"])
            r2pos = sum(1 for x in xs if x["r2_cresc"] is not None and x["r2_cresc"] > 0)
            resumo_n[f"{nid}_{et}"] = {"metricas": len(xs), "wape_menor_que_moderado": sum(1 for x in xs if x["wape"] < x["wape_moderado"]),
                                       "ic95_totalmente_abaixo_do_moderado": ic_neg, "ic95_totalmente_acima_do_moderado": ic_pos,
                                       "r2_crescimento_maior_que_moderado": r2m, "r2_crescimento_positivo": r2pos,
                                       "competitivas": sum(1 for x in xs if x["competitivo"] == "True")}
    res["novos_modelos"] = resumo_n
    # R² do crescimento F dos Moderados e de todos os candidatos competitivos
    r2s = defaultdict(list)
    for c in comp:
        if c["etapa"] == "F" and c["r2_crescimento"] not in ("", None):
            r2s["moderado" if c["moderado"] == "True" else c["categoria"] + ("_competitivo" if c["competitivo"] == "True" else "")].append(float(c["r2_crescimento"]))
    res["r2_crescimento_F"] = {k: {"n": len(v), "mediana": sorted(v)[len(v) // 2], "positivos": sum(x > 0 for x in v), "max": max(v)} for k, v in r2s.items()}
    # inventário: classes
    res["inventario_classes"] = dict(Counter((r["categoria"], r["classe"]) for r in inv).most_common())
    res["inventario_classes"] = {f"{a}|{b}": v for (a, b), v in res["inventario_classes"].items()}
    # --- conciliação com o registro de 1.343 da otimização
    if matriz_otim:
        ot = defaultdict(dict)
        for r in csv.DictReader(open(matriz_otim, encoding="utf-8")):
            if r["cenario"] in LADOS:
                ot[(r["DIST"], r["ativo"], r["metrica"])][r["cenario"]] = r["tipo_escolha"]
        comp_ot = {k for k, v in ot.items() if all(v.get(l) in ("MODELO_INDEPENDENTE", "CONDICIONAL_DO_MODERADO") for l in LADOS)}
        idx = {(r["DIST"], r["conceito"], r["metrica"]): r for r in rs}
        conc = Counter()
        for kk in comp_ot:
            r = idx.get(kk)
            if not r:
                conc["fora_do_universo"] += 1
            elif r["classe_final"].startswith("COMPLETA"):
                conc["completa_aqui"] += 1
            else:
                falhas = [r[f"causa_final_{l}"] for l in LADOS if r[f"{l}_final_categoria"] == "INDISPONIVEL"]
                conc["nao_completa_aqui:" + "+".join(sorted(set(falhas)))] += 1
        aqui_nao_ot = sum(1 for r in rs if r["classe_final"].startswith("COMPLETA") and (r["DIST"], r["conceito"], r["metrica"]) not in comp_ot)
        res["conciliacao_otimizacao"] = {"completas_no_registro_da_otimizacao": len(comp_ot), **dict(conc.most_common()), "completas_aqui_e_nao_na_otimizacao": aqui_nao_ot}
    (saida / "RESUMO.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:3])
