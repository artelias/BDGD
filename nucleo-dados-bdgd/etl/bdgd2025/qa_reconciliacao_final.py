"""Reconciliacao final (somente leitura dos dados processados; nao altera checkpoints nem reprocessa GDB).
1) qa_duplicatas_reconciliadas.csv: uma linha por par de publicacao multipla (inventario 'revisao_pendente'), classificada em
   equivalente | divergente | competencia_unica_valida, a partir de checkpoint/failure e equivalencia_duplicatas.json.
2) qa_sinais_temporais_classificados.csv: os sinais de qa_consistencia_temporal.csv ('revisar' e 'explicada') classificados em
   sucessao_societaria | alteracao_classificacao | anomalia_fonte | variacao_real_plausivel | sem_evidencia_suficiente,
   com a evidencia usada. Classificacao e indicativa para decisao humana; nenhum valor e corrigido."""
import collections, csv, glob, json, pathlib

H = pathlib.Path("D:/NUCLEO_BDGD_2022_2024"); OUT = pathlib.Path("D:/NUCLEO_BDGD_2025/output-historico/2022-2025")
inv = list(csv.DictReader(open(H / "inventario/inventario_historico_2022_2024.csv", encoding="utf-8")))
emp = {r["dist"]: r["empresa"] for r in inv}

# ---- 1) duplicatas
pares = collections.defaultdict(list)
for r in inv:
    if r["status"] == "revisao_pendente": pares[(r["ano"], r["dist"])].append(r)
qa79 = {(r["ano"], r["dist"]): r for r in csv.DictReader(open(OUT / "qa_publicacoes_multiplas.csv", encoding="utf-8-sig"))}
L = []
for (a, d), its in sorted(pares.items(), key=lambda k: (k[0][0], int(k[0][1]))):
    est = {}
    for r in its:
        b = H / "proc" / a / d / r["item_id"]
        if (b / "checkpoint.json").exists(): est[r["item_id"]] = "processado"
        elif (b / "failure.json").exists():
            f = json.load(open(b / "failure.json", encoding="utf-8"))
            est[r["item_id"]] = "competencia_divergente" if "DAT_FNL" in f["error"] else "falha:" + f["error_type"]
        else: est[r["item_id"]] = "nao_processado"
    validos = [i for i, e in est.items() if e == "processado"]
    eqf = H / "proc" / a / d / "equivalencia_duplicatas.json"
    eq = json.load(open(eqf, encoding="utf-8")) if eqf.exists() else None
    if len(validos) == 1 and all(e in ("processado", "competencia_divergente") for e in est.values()):
        cls, dec = "competencia_unica_valida", "nenhuma: o outro item tem BASE.DAT_FNL de outra competencia; usa-se o item valido"
    elif len(validos) >= 2 and eq and sorted(eq.get("itens", [])) == sorted(validos):
        cls = "equivalente" if eq.get("equivalente") else "divergente"
        dec = "nenhuma: equivalencia integral comprovada" if cls == "equivalente" else "escolher a publicacao valida (ou manter fora da serie)"
    else:
        cls, dec = "inconclusivo", "verificar processamento dos itens"
    q = qa79.get((a, d), {})
    ativos = [x for x in q.get("ativos_divergentes", "").split(",") if x]
    ents = sorted({x.split(".")[0] for x in (eq or {}).get("diferencas", []) if "." in x})
    L.append(dict(ano=a, dist=d, empresa=emp.get(d, ""), itens=" + ".join(f"{i} ({e})" for i, e in sorted(est.items())),
                  classificacao=cls, ativos_com_total_diferente=len(ativos), ativos=";".join(ativos), entidades_divergentes=";".join(ents),
                  impacto_no_painel="nenhum nos 26 totais (diferenca so em registros/atributos)" if cls == "divergente" and not ativos else ("altera totais" if ativos else ""),
                  decisao_humana=dec))
with open(OUT / "qa_duplicatas_reconciliadas.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, list(L[0]), lineterminator="\n"); w.writeheader(); w.writerows(L)
c = collections.Counter((r["ano"], r["classificacao"]) for r in L)
print("duplicatas:", len(L), "pares;", dict(c), "| divergentes sem efeito nos totais:", sum(1 for r in L if r["classificacao"] == "divergente" and not r["ativos_com_total_diferente"]))

# ---- 2) sinais temporais
eventos = list(csv.DictReader(open(OUT / "eventos_sucessao.csv", encoding="utf-8-sig")))
suc = {}
for e in eventos:
    for k in ("dist_destino_2025", "dist_origem"): suc[e[k]] = e["evento_id"]
pop = {}
for r in csv.DictReader(open(OUT / "populacao_conceitos.csv", encoding="utf-8-sig")):
    try: pop[(r["dist"], int(r["ano"]), r["conceito"])] = (float(r["quantidade"] or 0), float(r["sem_tuc_mcpse"] or 0))
    except ValueError: pass
conc = {}
for r in csv.DictReader(open(OUT / "serie_ativos_original.csv", encoding="utf-8-sig")): conc[r["ativo"]] = r["conceito"]
ESTOQUE = {"consumidores", "rede_mt", "rede_bt", "postes", "medidores", "trafo_dist", "ramais", "iluminacao", "alimentadores", "conjuntos"}
S = []
for r in csv.DictReader(open(OUT / "qa_consistencia_temporal.csv", encoding="utf-8")):
    d, at, a0, a1 = r["dist"], r["ativo"], int(r["de"]), int(r["para"]); x0, x1 = float(r["valor_de"]), float(r["valor_para"])
    p0, p1 = pop.get((d, a0, conc.get(at, at))), pop.get((d, a1, conc.get(at, at)))
    sh0 = p0[1] / p0[0] if p0 and p0[0] else None; sh1 = p1[1] / p1[0] if p1 and p1[0] else None
    dsh = None if sh0 is None or sh1 is None else abs(sh1 - sh0)
    razao = (x1 / x0) if x0 else float("inf")
    if d in suc:
        cat, ev = "sucessao_societaria", f"DIST em evento {suc[d]}"
    elif r["comparabilidade"].startswith("quebra") or (dsh is not None and dsh > 0.05):
        cat, ev = "alteracao_classificacao", f"comparabilidade={r['comparabilidade']}; parcela sem TUC {sh0 if sh0 is None else round(100*sh0,1)}% -> {sh1 if sh1 is None else round(100*sh1,1)}%"
    elif at in ESTOQUE and (x0 == 0 or x1 == 0 or razao < 0.2 or razao > 5):
        cat, ev = "anomalia_fonte", f"ativo de estoque variou {x0:,.0f} -> {x1:,.0f} (fisicamente implausivel em 1 ano)"
    elif at == "geradores" and x1 > x0:
        cat, ev = "variacao_real_plausivel", "expansao da geracao distribuida (crescimento consistente com o setor)"
    elif max(x0, x1) < 50:
        cat, ev = "sem_evidencia_suficiente", f"base pequena ({x0:,.0f} -> {x1:,.0f} unidades): variacao relativa pouco informativa"
    else:
        cat, ev = "sem_evidencia_suficiente", "sem quebra de classificacao, sucessao ou padrao de erro identificavel; requer verificacao"
    S.append({**r, "categoria": cat, "evidencia": ev})
with open(OUT / "qa_sinais_temporais_classificados.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, list(S[0]), lineterminator="\n"); w.writeheader(); w.writerows(sorted(S, key=lambda r: (r["categoria"], r["ativo"], int(r["dist"]), r["de"])))
print("sinais:", len(S), dict(collections.Counter(r["categoria"] for r in S)))
print("anomalia_fonte:", [(r["empresa"][:16], r["ativo"], r["de"], r["para"], r["valor_de"], r["valor_para"]) for r in S if r["categoria"] == "anomalia_fonte"][:12])
