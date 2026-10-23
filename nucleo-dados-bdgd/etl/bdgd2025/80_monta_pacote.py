"""Monta o pacote publico output-publicavel/2025-12-31 (contrato 1.1.0) a partir de proc/DIST=*/.
So agregados: nenhum COD_ID, nenhuma linha individual. Uso: 80_monta_pacote.py [--saida DIR]
Regra UC v2 (decisao 2): COD_ID distinto e o indicador principal quando nao ha COD_ID nulo, SIT_ATIV so AT/DS
e no maximo 1 registro ativado (AT) por COD_ID; repeticoes AT+DS sao historico de estado no ano, nao conflito."""
import argparse, csv, datetime, hashlib, json, pathlib, shutil, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import bdgd_etl as E
import duckdb

DB = E.DB
R = E.R
PROC, PQ = R / "proc", R / "staging_parquet"
UC, EXT = E.UC, E.EXT
POT = ("UNTRMT", "UNTRAT", "EQTRMT", "EQTRAT", "EQRE")
SEM = "SEM_CODIGO"
DDA_VERSAO = "BDGD_DDA_CATALOG_M10 v1.1"
FAMILIAS = {
    "UCBT": "Consumidores", "UCMT": "Consumidores", "UCAT": "Consumidores",
    "UGBT": "Geração conectada", "UGMT": "Geração conectada", "UGAT": "Geração conectada",
    "SSDBT": "Rede", "SSDMT": "Rede", "SSDAT": "Rede", "RAMLIG": "Rede", "SEGCON": "Rede",
    "UNTRMT": "Transformação", "UNTRAT": "Transformação", "EQTRMT": "Transformação", "EQTRAT": "Transformação",
    "UNSEBT": "Seccionamento", "UNSEMT": "Seccionamento", "UNSEAT": "Seccionamento", "EQSE": "Seccionamento",
    "UNREMT": "Regulação", "UNREAT": "Regulação", "EQRE": "Regulação",
    "UNCRBT": "Compensação reativa", "UNCRMT": "Compensação reativa", "UNCRAT": "Compensação reativa", "EQCR": "Compensação reativa",
    "EQME": "Medição", "EQTRM": "Medição",
    "PONNOT": "Estruturas", "PIP": "Iluminação pública",
    "SUB": "Subestações e circuitos", "CTMT": "Subestações e circuitos", "CTAT": "Subestações e circuitos",
    "BAR": "Subestações e circuitos", "BAY": "Subestações e circuitos", "CONJ": "Subestações e circuitos",
    "PT": "Perdas e balanço", "PNT": "Perdas e balanço", "BE": "Perdas e balanço", "EP": "Perdas e balanço",
    "CRVCRG": "Cadastro auxiliar", "ARAT": "Área de atuação",
}
NAO_ATIVO = {"PT", "PNT", "BE", "EP", "CRVCRG", "ARAT", "CONJ"}   # registros que nao sao ativos fisicos


def rd(p): return list(csv.DictReader(open(p, encoding="utf-8")))
def num(v): return None if v in ("", None) else float(v)
def fmt(v):
    if v is None or v == "": return ""
    s = str(v).strip()
    if "e" not in s.lower():   # ja e decimal fixo (preserva a precisao original, inclusive DECIMAL exato)
        return s[:-2] if s.endswith(".0") else s
    return format(float(s), ".9f").rstrip("0").rstrip(".")


def uc_v2(dist):
    cache = PROC / f"DIST={dist}" / "uc_v2.json"
    if cache.exists(): return json.loads(cache.read_text(encoding="utf-8"))
    con = duckdb.connect(); con.execute("SET threads=1; SET memory_limit='700MB'")
    out = {}
    for e in UC:
        p = PQ / f"DIST={dist}" / f"DATA_BASE={DB}" / f"entidade={e}" / "part-0.parquet"
        if not p.exists(): continue
        n, nn, nd, nat, ndat, outros = con.execute(f"""SELECT count(*), count(COD_ID), count(DISTINCT COD_ID), count(*) FILTER (WHERE SIT_ATIV='AT'),
            count(DISTINCT COD_ID) FILTER (WHERE SIT_ATIV='AT'), count(*) FILTER (WHERE SIT_ATIV IS NULL OR SIT_ATIV NOT IN ('AT','DS'))
            FROM read_parquet('{p.as_posix()}')""").fetchone()
        motivos = []
        if nn < n: motivos.append(f"{n - nn} registros sem COD_ID")
        if nat != ndat: motivos.append(f"{nat - ndat} registros ativados (SIT_ATIV=AT) excedentes para COD_ID ja ativado")
        if outros: motivos.append(f"{outros} registros com SIT_ATIV fora de AT/DS")
        out[e] = {"registros": n, "cod_id_nao_nulo": nn, "cod_id_distinto": nd, "registros_ativados": nat, "cod_id_ativados": ndat,
                  "sit_ativ_outros": outros, "valida": not motivos, "motivos": motivos, "historico_at_ds": nd < n and not motivos}
    con.close()
    cache.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--saida", default=str(R / "output-publicavel" / DB)); a = ap.parse_args()
    OUT = pathlib.Path(a.saida); TMP = OUT.with_name(OUT.name + ".tmp")
    shutil.rmtree(TMP, ignore_errors=True); (TMP / "geo").mkdir(parents=True); (TMP / "schemas").mkdir()
    K = E.Conhecimento()
    inv = {r["dist"]: r for r in rd(R / "inventario" / "inventario_2025.csv")}
    gcfg = json.load(open(pathlib.Path(__file__).parent / "config" / "grupos_2025.json", encoding="utf-8"))
    dist_grp = {str(d): g for g in gcfg["grupos"] for d in g["dists"]}
    ok = sorted((p.parent.name.split("=")[1] for p in PROC.glob("DIST=*/_OK")), key=int)
    falhas = sorted((p.parent.name.split("=")[1] for p in PROC.glob("DIST=*/_FALHA.json")), key=int)
    alvo = [d for d, r in inv.items() if r["data_base_declarada"] == DB]

    def w(name, rows, cols):
        with open(TMP / name, "w", newline="", encoding="utf-8") as f:
            wr = csv.DictWriter(f, cols, extrasaction="ignore", lineterminator="\n"); wr.writeheader(); wr.writerows(rows)

    fatos, facetas, qa, alertas, comp, vinc, ddaqa, filtros, arat_qa, ucs = [], [], [], [], [], [], [], [], [], []
    disj = {}   # (facet_id, ent, metrica) -> todos os DIST disjuntos?
    met_status = {}
    exatas = {}
    for d in ok:
        pd_ = PROC / f"DIST={d}"
        v2 = uc_v2(d)
        for e, x in v2.items(): ucs.append({"dist": d, "entidade": e, **{k: v for k, v in x.items() if k != "motivos"}, "motivos": "; ".join(x["motivos"])})
        for r in rd(pd_ / "fatos.csv"):
            e = r["entidade"]; mot = [m.strip() for m in r["motivo_qualidade"].split(";") if m.strip()]
            if e in UC and e in v2:
                x = v2[e]
                mot = [m for m in mot if not m.startswith(("contagem_distinta_nao_validada", "COD_ID_repetido_sem_conflito"))]
                if x["valida"]:
                    r["quantidade"] = str(x["cod_id_distinto"])
                    if x["historico_at_ds"]: mot.append(f"regra_UC_v2: {x['registros'] - x['cod_id_distinto']} registros de historico AT/DS no ano; 1 registro ativado por COD_ID")
                else:
                    r["quantidade"] = ""
                    mot.append("quantidade N/D (regra UC v2): " + "; ".join(x["motivos"]))
                r["status_qualidade"] = "alerta" if (not x["valida"] or any(m.startswith("sobreposicao_UC") for m in mot)) else "aprovado"
            r["motivo_qualidade"] = "; ".join(mot)
            fatos.append(r)
            # status por metrica (para facetas e catalogo)
            mt = " ".join(mot)
            met_status[(d, e, "quantidade")] = ("bloqueado", "quantidade N/D no fato-base") if r["quantidade"] == "" else ("aprovado", "")
            met_status[(d, e, "quantidade_registros")] = ("aprovado", "")
            met_status[(d, e, "quantidade_cod_id_distinto")] = ("aprovado", "")
            met_status[(d, e, "extensao_km")] = ("alerta", "COMP nulo ou zero em parte dos segmentos") if "COMP_nulo" in mt else ("aprovado", "")
            if r["potencia_kva"] == "": met_status[(d, e, "potencia_kva")] = ("bloqueado", "potencia_kva N/D no fato-base")
            elif any(k in mt for k in ("divergencia_", "POT_NOM_provavel_MVA", "potencia_nula", "kVA (codigo DDA implausivel")):
                met_status[(d, e, "potencia_kva")] = ("alerta", "; ".join(m for m in mot if any(k in m for k in ("divergencia_", "POT_NOM", "potencia")))[:300])
            else: met_status[(d, e, "potencia_kva")] = ("aprovado", "")
        tot = {r["entidade"]: r for r in fatos if r["dist"] == d}
        # totais exatos (DECIMAL) quando disponiveis: mesma regra, sem arredondamento intermediario
        tv2 = pd_ / "totais_v2.json"
        if tv2.exists():
            for e, t in json.loads(tv2.read_text(encoding="utf-8")).items():
                if e not in tot: continue
                assert int(tot[e]["quantidade_registros"]) == t["n"], (d, e)
                if tot[e]["extensao_km"] != "" and t["extensao_km"] is not None: tot[e]["extensao_km"] = t["extensao_km"]
                if tot[e]["potencia_kva"] != "" and t["potencia_kva"] is not None: tot[e]["potencia_kva"] = t["potencia_kva"]
        # facetas: uma metrica por linha. v2 = exatas + cubos conjuntos; senao, facetas de 1 dimensao do processamento
        porfacet = {}
        if (pd_ / "facetas_v2.csv").exists():
            exatas[d] = True
            for r in rd(pd_ / "facetas_v2.csv"):
                porfacet.setdefault((r["entidade"], r["facet_id"]), []).append((json.loads(r["dimensoes_json"]), {
                    "quantidade_registros": r["n"], "quantidade_cod_id_distinto": r["nd"], "extensao_km": r["extensao_km"], "potencia_kva": r["potencia_kva"]}))
        else:
            exatas[d] = False
            for r in rd(pd_ / "facetas.csv"):
                dims = json.loads(r["dimensoes_json"]); (attr, code), = dims.items()
                porfacet.setdefault((r["entidade"], f"{r['entidade']}.{attr}"), []).append(({attr: code if code not in ("", None) else SEM}, r))
        for (e, fid), rows in porfacet.items():
            mets = ["quantidade"] + (["quantidade_registros", "quantidade_cod_id_distinto"] if e in UC else []) + \
                   (["extensao_km"] if e in EXT else []) + (["potencia_kva"] if e in POT else [])
            for m in mets:
                st, mo = met_status.get((d, e, m), ("em_validacao", "sem status"))
                if e in UC and m in ("quantidade", "quantidade_cod_id_distinto"):
                    soma = sum(int(r["quantidade_cod_id_distinto"] or 0) for _, r in rows)
                    total = int(tot[e]["quantidade_cod_id_distinto"] or 0)
                    dj = soma == total
                    disj[(fid, e, m)] = disj.get((fid, e, m), True) and dj
                    if not dj and st == "aprovado": st, mo = "alerta", f"categorias nao disjuntas por COD_ID (soma {soma} > total {total}); nao somar"
                else: disj.setdefault((fid, e, m), True)
                for dims, r in rows:
                    if m == "quantidade": v = (r["quantidade_cod_id_distinto"] if e in UC else r["quantidade_registros"])
                    elif m == "quantidade_registros": v = r["quantidade_registros"]
                    elif m == "quantidade_cod_id_distinto": v = r["quantidade_cod_id_distinto"]
                    elif m == "extensao_km": v = r["extensao_km"]
                    else: v = r["potencia_kva"]
                    s2, mo2 = st, mo
                    if st == "bloqueado": v = ""
                    elif v == "": s2, mo2 = "alerta", (mo + "; " if mo else "") + "valor nulo na categoria"
                    facetas.append({"dist": d, "entidade": e, "data_base": DB, "facet_id": fid,
                                    "dimensoes_json": json.dumps({a_: str(c_) for a_, c_ in sorted(dims.items())}, ensure_ascii=False), "metrica": m, "valor": fmt(v),
                                    "unidade": {"extensao_km": "km", "potencia_kva": "kVA"}.get(m, "itens"), "status_qualidade": s2, "motivo_qualidade": mo2})
        qa += rd(pd_ / "qa_reconciliacao.csv")
        alertas += rd(pd_ / "alertas.csv"); comp += rd(pd_ / "complementares.csv"); vinc += rd(pd_ / "qa_vinculos.csv")
        ddaqa += rd(pd_ / "qa_dda.csv"); filtros += rd(pd_ / "disponibilidade_filtros.csv")
        aq = json.loads((pd_ / "arat_qa.json").read_text(encoding="utf-8")); arat_qa.append(aq)
        if aq["status"] == "ok": shutil.copyfile(pd_ / "arat.geojson", TMP / "geo" / f"arat_2025_{d}.geojson")
        for e, x in v2.items():
            comp.append({"dist": d, "entidade": e, "indicador": "uc_ativadas", "unidade": "COD_ID com SIT_ATIV=AT", "valor": x["cod_id_ativados"],
                         "status": "aprovado" if x["valida"] else "alerta", "motivo": "; ".join(x["motivos"])})

    # ---- fato-base e matriz
    COLS_F = ["dist", "entidade", "data_base", "dimensoes_json", "quantidade", "quantidade_registros", "quantidade_cod_id_distinto", "extensao_km", "potencia_kva", "status_qualidade", "motivo_qualidade"]
    for r in fatos:
        for k in ("quantidade", "quantidade_registros", "quantidade_cod_id_distinto", "extensao_km", "potencia_kva"): r[k] = fmt(r[k])
    fatos.sort(key=lambda r: (int(r["dist"]), r["entidade"]))
    w("ativos_agregados.csv", fatos, COLS_F)
    ents = sorted({r["entidade"] for r in fatos})
    mcols = []
    for e in ents:
        mcols.append(f"{e}__quantidade")
        if e in UC: mcols += [f"{e}__quantidade_registros", f"{e}__quantidade_cod_id_distinto"]
        if e in EXT: mcols.append(f"{e}__extensao_km")
        if e in POT: mcols.append(f"{e}__potencia_kva")
    idx = {(r["dist"], r["entidade"]): r for r in fatos}
    mat = []
    for d in ok:
        row = {"dist": d, "data_base": DB}
        for c in mcols:
            e, m = c.split("__"); f = idx.get((d, e)); row[c] = f[m] if f else ""
        mat.append(row)
    w("matriz_empresas_2025.csv", mat, ["dist", "data_base"] + mcols)

    # ---- facetas + catalogo
    facetas.sort(key=lambda r: (int(r["dist"]), r["facet_id"], r["metrica"], r["dimensoes_json"]))
    w("ativos_facetas.csv", facetas, ["dist", "entidade", "data_base", "facet_id", "dimensoes_json", "metrica", "valor", "unidade", "status_qualidade", "motivo_qualidade"])
    cat = []
    for (fid, e, m), dj in sorted(disj.items()):
        uc_dist = e in UC and m in ("quantidade", "quantidade_cod_id_distinto")
        st = "aprovado" if (dj or not uc_dist) else "alerta"
        part = "sim" if (dj or not uc_dist) else "nao"
        cat.append({"facet_id": fid, "entidade": e, "dimensoes_json": json.dumps(fid.split(".", 1)[1].split("+")), "metrica": m,
                    "unidade": {"extensao_km": "km", "potencia_kva": "kVA"}.get(m, "itens"), "cobertura": "completa", "particao_disjunta": part,
                    "permite_rollup": "sim" if (part == "sim" and st == "aprovado") else "nao", "status_qualidade": st,
                    "regra": ("COUNT(DISTINCT COD_ID) por categoria; " if uc_dist else "") + ("SEM_CODIGO = registro sem codigo DDA informado" )})
    w("facetas_catalogo.csv", cat, ["facet_id", "entidade", "dimensoes_json", "metrica", "unidade", "cobertura", "particao_disjunta", "permite_rollup", "status_qualidade", "regra"])

    # ---- distribuidoras, grupos, cobertura
    aq = {a["dist"]: a for a in arat_qa}
    dists = []
    for d in ok:
        r = inv[d]; g = dist_grp.get(d)
        dists.append({"dist": d, "sigla": r["sigla"], "nome": r["empresa"], "grupo_economico": g["grupo_id"] if g else "nao_confirmado",
                      "data_base": DB, "fonte_url": r["url_item"], "sha256": json.loads((R / "staging_raw" / f"DIST={d}" / f"DATA_BASE={DB}" / "download.json").read_text())["sha256"],
                      "status": "processada", "grupo_nome": g["nome"] if g else "", "grupo_status": "verificado" if g else "nao_confirmado",
                      "arat_area_km2": aq.get(d, {}).get("area_km2_origem", ""), "item_id": r["item_id"], "versao_arquivo": r["versao"]})
    w("distribuidoras.csv", dists, list(dists[0].keys()))
    w("grupos_economicos.csv", [{"grupo_id": g["grupo_id"], "nome": g["nome"], "controlador_final": g["controlador_final"], "status": "verificado",
                                 "n_dists": len(g["dists"]), "fonte_url": " | ".join(g["fontes"]), "tipo_fonte": g["tipo_fonte"],
                                 "consultado_em": gcfg["consultado_em"], "observacao": g["observacao"]} for g in gcfg["grupos"]],
      ["grupo_id", "nome", "controlador_final", "status", "n_dists", "fonte_url", "tipo_fonte", "consultado_em", "observacao"])
    w("dist_grupo.csv", [{"dist": d, "grupo_id": dist_grp[d]["grupo_id"] if d in dist_grp else "nao_confirmado", "status": "verificado" if d in dist_grp else "nao_confirmado",
                          "vigente_em": DB, "fonte_url": dist_grp[d]["fontes"][0] if d in dist_grp else ""} for d in sorted(inv, key=int) if d in alvo],
      ["dist", "grupo_id", "status", "vigente_em", "fonte_url"])
    cob = []
    for d, r in sorted(inv.items(), key=lambda kv: int(kv[0])):
        st = "processada" if d in ok else ("quarentena" if d in falhas else ("em_processamento" if d in alvo else "sem_publicacao_2025"))
        cob.append({"dist": d, "sigla": r["sigla"], "empresa": r["empresa"], "status_2025": st, "data_base_declarada": r["data_base_declarada"],
                    "tamanho_bytes": r["tamanho_bytes"], "item_id": r["item_id"], "motivo": r["motivo"] if st == "sem_publicacao_2025" else ""})
    w("cobertura_distribuidoras.csv", cob, list(cob[0].keys()))

    # ---- entidades e DDA
    ent_rows = []
    for e in ents:
        m = "extensao_km" if e in EXT else ("potencia_kva" if e in POT else "quantidade")
        un = {"extensao_km": "km", "potencia_kva": "kVA"}.get(m, "itens")
        regra = ("quantidade = COUNT(DISTINCT COD_ID) quando a regra UC v2 valida a entidade no DIST; senao N/D" if e in UC else "quantidade = COUNT(*) de registros da camada")
        if e in EXT: regra += "; extensao_km = SUM(COMP em metros)/1000 (comprimento declarado, nao geometrico)"
        if e == "UNTRMT": regra += "; potencia_kva = SUM(POT_NOM) declarado em kVA"
        if e == "UNTRAT": regra += "; potencia_kva = SUM(POT_NOM em MVA) x 1000"
        if e in ("EQTRMT", "EQTRAT", "EQRE"): regra += "; potencia_kva = SUM(TPOTAPRT.POT) via codigo POT_NOM (DDA M10)"
        if e in ("UGBT", "UGMT", "UGAT"): regra += "; potencia de geracao N/D (POT_INST nao homologado)"
        ent_rows.append({"entidade": e, "nome_exibicao": K.desig.get(e, e), "familia": FAMILIAS.get(e, "Outros"), "metrica": m, "unidade": un, "regra": regra,
                         "ativo_fisico": "nao" if e in NAO_ATIVO else "sim", "nao_somar_com": {"UNTRMT": "EQTRMT", "EQTRMT": "UNTRMT", "UNTRAT": "EQTRAT", "EQTRAT": "UNTRAT"}.get(e, "")})
    w("entidades.csv", ent_rows, list(ent_rows[0].keys()))
    pares = {(f["entidade"], a_) for f in cat for a_ in f["facet_id"].split(".", 1)[1].split("+")}
    dd = []
    for x in K.rel["dda_references"]:
        if (x["source_entity"], x["source_field"]) in pares and x["dda_table"] in K.dda:
            for code, (desc, _) in sorted(K.dda[x["dda_table"]].items()):
                dd.append({"versao": DDA_VERSAO, "entidade": x["source_entity"], "atributo": x["source_field"], "codigo_interno": code, "descricao": desc or "", "dominio": x["dda_table"]})
    w("dda_descricoes.csv", dd, ["versao", "entidade", "atributo", "codigo_interno", "descricao", "dominio"])

    # ---- QA e complementares
    w("qa_reconciliacao.csv", qa, ["dist", "entidade", "metrica", "valor_origem", "valor_agregado", "diferenca", "tolerancia", "status"])
    w("qa_alertas.csv", alertas, ["dist", "entidade", "tipo", "detalhe", "acao"])
    w("qa_vinculos.csv", vinc, ["dist", "origem", "destinos", "status", "linhas_origem", "fk_preenchida", "fk_casada", "orfaos", "pct_orfaos", "destino_com_cod_id_repetido"])
    w("qa_dda_cobertura.csv", ddaqa, ["dist", "entidade", "atributo", "tabela_dda", "status", "linhas", "linhas_com_descricao", "pct_cobertura", "codigos_distintos", "codigos_sem_descricao", "observacao"])
    w("qa_uc_regra_v2.csv", ucs, ["dist", "entidade", "registros", "cod_id_nao_nulo", "cod_id_distinto", "registros_ativados", "cod_id_ativados", "sit_ativ_outros", "valida", "historico_at_ds", "motivos"])
    w("disponibilidade_filtros.csv", filtros, ["dist", "entidade", "filtro", "status", "numerador_orfaos", "denominador_fk", "pct_orfaos", "motivo"])
    w("indicadores_complementares.csv", comp, ["dist", "entidade", "indicador", "unidade", "valor", "status", "motivo"])
    w("qa_arat.csv", arat_qa, ["dist", "status", "feicoes_origem", "valida_origem", "crs_origem", "crs_publicacao", "crs_medicao", "tolerancia_m", "area_km2_origem",
                               "area_km2_simplificada", "dif_area_pct", "partes", "buracos", "sobreposicao_entre_feicoes_km2", "vertices_origem", "vertices_saida", "valida_saida", "tipo_saida", "bytes", "sha256"])

    # ---- homologacao por entidade x metrica (reconciliacao com a origem + estado QA em cada DIST)
    rec = {}
    for q in qa:
        rec.setdefault((q["entidade"], q["metrica"]), []).append(q["status"])
    homol = []
    for e in ents:
        mets = ["quantidade", "quantidade_registros", "quantidade_cod_id_distinto"] + (["extensao_km"] if e in EXT else []) + (["potencia_kva"] if e in POT else [])
        for m in mets:
            vals = [idx[(d, e)][m] for d in ok if (d, e) in idx]
            nd_ = sum(v == "" for v in vals); st = [met_status.get((d, e, m), ("", ""))[0] for d in ok if (d, e) in idx]
            rr = rec.get((e, m), [])
            falha = sum(s == "falha" for s in rr)
            if falha: h = "nao_homologada"
            elif m == "quantidade_cod_id_distinto" and e not in UC: h = "informativa"
            elif nd_ == len(vals): h = "nao_homologada"
            elif nd_ or "alerta" in st: h = "homologada_com_ressalvas"
            else: h = "homologada"
            homol.append({"entidade": e, "metrica": m, "status_homologacao": h, "dists_com_valor": len(vals) - nd_, "dists_nd": nd_,
                          "dists_alerta": st.count("alerta"), "reconciliacoes_ok": sum(s == "ok" for s in rr), "reconciliacoes_falha": falha,
                          "criterio": "reconciliacao exata com o GDB 2025 (contagem e soma independentes) + estado QA por DIST"})
        if e in ("UGBT", "UGMT", "UGAT"):
            homol.append({"entidade": e, "metrica": "potencia_instalada_kw", "status_homologacao": "nao_homologada", "dists_com_valor": 0, "dists_nd": len(ok),
                          "dists_alerta": 0, "reconciliacoes_ok": 0, "reconciliacoes_falha": 0, "criterio": "POT_INST sem unidade/semantica comprovada (SIGFI, valores > 75 kW em BT)"})
    w("metricas_homologacao.csv", homol, ["entidade", "metrica", "status_homologacao", "dists_com_valor", "dists_nd", "dists_alerta", "reconciliacoes_ok", "reconciliacoes_falha", "criterio"])

    # ---- manifesto
    completo = len(ok) == len(alvo) and not falhas
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    files = {"distribuidoras": "distribuidoras.csv", "entidades": "entidades.csv", "fatos": "ativos_agregados.csv", "facetas": "ativos_facetas.csv",
             "facetas_catalogo": "facetas_catalogo.csv", "matriz": "matriz_empresas_2025.csv", "arat": sorted(f"geo/{p.name}" for p in (TMP / "geo").glob("*.geojson"))}
    lock = json.load(open(E.K / "KNOWLEDGE_LOCK.json", encoding="utf-8"))
    man = {"schema_version": "1.1.0", "release_id": "", "data_base": DB,
           "status": "parcial", "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
           "dda_version": DDA_VERSAO,
           "sources": [{"dist": int(x["dist"]), "url": x["fonte_url"], "sha256": x["sha256"], "data_base": DB} for x in dists],
           "files": files, "quality": {"status": "em_validacao", "source_reconciliation": all(q["status"] != "falha" for q in qa), "facetas_exatas_decimal": all(exatas.values()), "dists_sem_facetas_exatas": sorted((d for d, v in exatas.items() if not v), key=int)},
           "cobertura": {"distribuidoras_historicas_consideradas": len(inv), "com_gdb_2025": len(alvo), "processadas": len(ok), "quarentena": falhas,
                         "em_processamento": sorted(set(alvo) - set(ok) - set(falhas), key=int), "sem_publicacao_2025": sorted(set(inv) - set(alvo), key=int)},
           "regras": {"uc": "regra UC v2", "potencia_ug": "N/D (POT_INST nao homologado)", "rede": "extensao_km = SUM(COMP)/1000",
                      "transformacao": "UNTRMT e EQTRMT sao visoes da mesma populacao; nunca somar"},
           "conhecimento_ia_builder": {f["file"]: f["sha256_copy"] for f in lock["files"]},
           "licenca": "Dados derivados da BDGD/ANEEL (dados abertos). Atribuicao: Agencia Nacional de Energia Eletrica - ANEEL. Projeto nao oficial.",
           "autoria": "Nucleo de Dados da BDGD - desenvolvido por Arthur Henrique Lima",
           "privacidade": "Somente agregados por DIST/entidade/categoria DDA. Sem COD_ID, sem registros individuais, sem dados de consumidores.",
           "checksums": {}}
    man["release_id"] = f"bdgd-2025-12-31-{'v1' if completo else 'parcial'}-{len(ok)}d-" + hashlib.sha256("".join(sorted(x["sha256"] for x in dists)).encode()).hexdigest()[:10]
    contrato = {"schema_version": "1.1.0", "arquivos": {p.name: next(csv.reader(open(p, encoding="utf-8"))) for p in sorted(TMP.glob("*.csv"))},
                "geo": {"padrao": "geo/arat_2025_<DIST>.geojson", "crs": "EPSG:4326", "propriedades": {"dist": "integer", "data_base": "YYYY-MM-DD", "source_item_id": "string"}},
                "convencoes": {"vazio": "N/D (metrica inexistente, bloqueada ou nao homologada); nunca zero implicito", SEM: "categoria de registros sem codigo DDA informado"}}
    (TMP / "schemas" / "contrato_publicacao.json").write_text(json.dumps(contrato, ensure_ascii=False, indent=1), encoding="utf-8")
    man["checksums"] = {str(p.relative_to(TMP)).replace("\\", "/"): sha(p) for p in sorted(TMP.rglob("*")) if p.is_file()}
    (TMP / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
    shutil.rmtree(OUT, ignore_errors=True); TMP.rename(OUT)
    print(json.dumps({"saida": str(OUT), "processadas": len(ok), "alvo": len(alvo), "fatos": len(fatos), "facetas": len(facetas), "catalogo": len(cat),
                      "uc_invalidas": sum(1 for u in ucs if not u["valida"]), "arat": len(files["arat"]), "release": man["release_id"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
