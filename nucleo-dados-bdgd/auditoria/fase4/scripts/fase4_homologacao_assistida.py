"""FASE 4 — Homologacao assistida BDGD 2022-2025 (SOMENTE LEITURA das fontes; grava apenas em auditoria-fase4/).
Nao altera pipeline, checkpoints, Parquet, serie, pacote 2025 nem status de homologacao. Nao escolhe publicacoes.
Entradas: output-historico/2022-2025 (serie, QA), proc/*/checkpoint.json, conceitos_r3.json, equivalencia_duplicatas.json,
MATRIZ_CONFORMIDADE_BDGD_ORDINARIA.csv e evidencias/investigacao_casos.json (desta fase).
Saidas: MATRIZ_HOMOLOGACAO_2022_2025.csv, DECISOES_DUPLICATAS_13_PARES.csv, RANKING_ANOMALIAS_TEMPORAIS.csv,
PONTES_SUCESSOES_HISTORICAS.csv e evidencias/fase4_resumo.json (base dos .md)."""
import collections, csv, glob, json, math, pathlib
import duckdb

H = pathlib.Path("D:/NUCLEO_BDGD_2022_2024"); R = pathlib.Path("D:/NUCLEO_BDGD_2025")
O = R / "output-historico/2022-2025"; A = R / "auditoria-fase4"; EV = A / "evidencias"
ANOS = (2022, 2023, 2024, 2025)
CHAVE = ("consumidores", "rede_mt", "rede_bt", "trafo_dist", "postes", "medidores")
ENT = {"consumidores": ["UCBT", "UCMT", "UCAT"], "geradores": ["UGBT", "UGMT", "UGAT"], "iluminacao": ["PIP"], "rede_bt": ["SSDBT"], "rede_mt": ["SSDMT"],
       "rede_at": ["SSDAT"], "ramais": ["RAMLIG"], "trafo_dist": ["EQTRMT"], "trafo_forca": ["EQTRAT"], "trafo_medida": ["EQTRM"], "chaves": ["EQSE"],
       "seccionalizadores": ["EQSE"], "disjuntores": ["EQSE"], "religadores": ["EQSE"], "reguladores": ["EQRE"], "bancos_capacitores": ["EQCR"], "reatores": ["EQCR"],
       "medidores": ["EQME"], "postes": ["PONNOT"], "torres": ["PONNOT"], "subestacoes": ["SUB"], "alimentadores": ["CTMT"], "circuitos_at": ["CTAT"],
       "conjuntos": ["CONJ"], "barramentos": ["BAR"]}
rd = lambda p: list(csv.DictReader(open(p, encoding="utf-8-sig")))
fnum = lambda v: None if v in ("", None) else float(v)  # valores de km chegam como texto decimal exato


def grava(nome, linhas, campos=None):
    campos = campos or list(linhas[0])
    with open(A / nome, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, campos, lineterminator="\n"); w.writeheader(); w.writerows(linhas)


S = rd(O / "serie_ativos_original.csv")
nomes = {r["dist"]: r["empresa"] for r in S}
cel = {(int(r["ano"]), r["dist"], r["ativo"]): r for r in S}
ATIVOS = sorted({r["ativo"] for r in S}); MED = {r["ativo"]: (r["medida"], r["unidade"]) for r in S}
CONF = {r["item_id"]: r for r in rd(A / "MATRIZ_CONFORMIDADE_BDGD_ORDINARIA.csv")}
conf_por = collections.defaultdict(list)
for r in CONF.values(): conf_por[(int(r["ano_alvo"]), r["dist"])].append(r)
INV = rd(H / "inventario/inventario_historico_2022_2024.csv")
CASOS = json.loads((EV / "investigacao_casos.json").read_text(encoding="utf-8"))
pop = {}
for r in rd(O / "populacao_conceitos.csv"):
    q, s = fnum(r["quantidade"]), fnum(r["sem_tuc_mcpse"])
    pop[(r["dist"], int(r["ano"]), r["conceito"])] = (q, s)
conceito = {r["ativo"]: r["conceito"] for r in S}
tot_nac = collections.defaultdict(float)
for r in S:
    if r["status"] == "validado" and r["valor"] != "": tot_nac[(int(r["ano"]), r["ativo"])] += float(r["valor"])
eventos = rd(O / "eventos_sucessao.csv")

# ======================= 1) DUPLICATAS (13 pares divergentes) =======================
recon = {(r["ano"], r["dist"]): r for r in rd(O / "qa_duplicatas_reconciliadas.csv")}
pares_inv = collections.defaultdict(list)
for x in INV:
    if x["status"] == "revisao_pendente": pares_inv[(x["ano"], x["dist"])].append(x)


def vizinhos(ano, dist, ativo):
    vs = [fnum(cel[(a, dist, ativo)]["valor"]) for a in (ano - 1, ano + 1) if (a, dist, ativo) in cel and cel[(a, dist, ativo)]["status"] == "validado"]
    return [v for v in vs if v is not None]


DUP, dup_resumo = [], []
for (ano, dist), rr in sorted(recon.items()):
    if rr["classificacao"] != "divergente": continue
    its = pares_inv[(ano, dist)]
    info = {}
    for x in its:
        b = H / "proc" / ano / dist / x["item_id"]
        ck = json.loads((b / "checkpoint.json").read_text(encoding="utf-8"))
        cj = json.loads((b / "conceitos_r3.json").read_text(encoding="utf-8"))
        info[x["item_id"]] = dict(inv=x, ck=ck, cj=cj, conf=CONF.get(x["item_id"], {}))
    # A = versao anterior, B = versao posterior (pelo carimbo de versao do titulo no catalogo)
    ordem = sorted(info, key=lambda i: info[i]["conf"].get("versao_titulo", ""))
    ia, ib = ordem[0], ordem[-1]; a_, b_ = info[ia], info[ib]
    eq = json.loads((H / "proc" / ano / dist / "equivalencia_duplicatas.json").read_text(encoding="utf-8"))
    difs = eq.get("diferencas", [])
    tipo = lambda g: sorted({d.split(".")[0] for d in difs if d.endswith(g)})
    cont = []
    for e, v in eq.get("entidades", {}).items():
        na = (v.get(ia) or {}).get("registro"); nb = (v.get(ib) or {}).get("registro")
        na = na[0] if isinstance(na, list) else None; nb = nb[0] if isinstance(nb, list) else None
        if na != nb: cont.append(f"{e}:{na}->{nb}")
    linhas_par, n_dif, n_coer = [], 0, collections.Counter()
    risco_pts = 0
    for at in ATIVOS:
        va = a_["cj"]["ativos"].get(at, {}); vb = b_["cj"]["ativos"].get(at, {})
        xa, xb = fnum(va.get("valor")), fnum(vb.get("valor"))
        dif = None if xa is None or xb is None else xb - xa
        pct = None if dif is None or not xa else 100 * dif / xa
        viz = vizinhos(int(ano), dist, at)
        coer = "nd"
        if dif not in (None, 0) and viz:
            ref = sum(viz) / len(viz)
            da, db = abs((xa or 0) - ref), abs((xb or 0) - ref)
            coer = "A" if da < db else ("B" if db < da else "empate"); n_coer[coer] += 1
        if dif: n_dif += 1
        if dif and (at in CHAVE and abs(pct or 100) > 1 or abs(pct or 100) > 10): risco_pts += 1
        nac = tot_nac.get((int(ano), at)) or None
        linhas_par.append(dict(ativo=at, medida=MED[at][0], unidade=MED[at][1], valor_A=xa if xa is not None else "", status_A=va.get("status", "nao_disponivel"),
                               valor_B=xb if xb is not None else "", status_B=vb.get("status", "nao_disponivel"), dif_abs_B_menos_A="" if dif is None else round(dif, 6),
                               dif_pct="" if pct is None else round(pct, 3), dif_sobre_total_validado_do_ano_pct="" if dif is None or not nac else round(100 * abs(dif) / nac, 5),
                               vizinhos_validados="|".join(f"{v:g}" for v in viz) or "nao_disponivel", mais_coerente_com_vizinhos=coer))
    grupo = "COM_DIFERENCA_TOTAIS" if n_dif else "SEM_DIFERENCA_TOTAIS"
    risco = "BAIXO" if not n_dif else ("ALTO" if risco_pts else "MEDIO")
    fav_b = [f"versao posterior ({b_['conf'].get('versao_titulo')} vs {a_['conf'].get('versao_titulo')}): republicacao mais recente"]
    fav_a = []
    if n_coer["B"] > n_coer["A"]: fav_b.append(f"mais coerente com anos vizinhos em {n_coer['B']} de {sum(n_coer.values())} ativos divergentes")
    elif n_coer["A"] > n_coer["B"]: fav_a.append(f"mais coerente com anos vizinhos em {n_coer['A']} de {sum(n_coer.values())} ativos divergentes")
    for lado, z, lst in (("A", a_, fav_a), ("B", b_, fav_b)):
        if z["conf"].get("classe_intervalo") != "INTERVALO_ANUAL_COMPATIVEL": (fav_b if lado == "A" else fav_a).append(f"{lado} com intervalo da BASE {z['conf'].get('classe_intervalo')}")
        if z["ck"].get("reconciliation_failures"): (fav_b if lado == "A" else fav_a).append(f"{lado} com falhas de reconciliacao")
    if not n_dif:
        rec = "Sem impacto nos 25 totais: qualquer escolha produz o mesmo painel. Tecnicamente sugere-se B (versao posterior); diferencas so em registros/atributos."
    elif n_coer["A"] > n_coer["B"]:
        rec = "Inconclusiva: B e a versao posterior, mas A e mais coerente com os anos vizinhos. Recomenda-se consultar a distribuidora/ANEEL antes de escolher."
    else:
        rec = "Sugere-se B: versao posterior e igual ou mais coerente com os anos vizinhos. Confirmar antes de publicar."
    rep = ("republicacao: as duas publicacoes tem DATA_BASE " + f"31/12/{ano}" + ", intervalo da BASE " + a_["conf"].get("classe_intervalo", "?") + "/" + b_["conf"].get("classe_intervalo", "?")
           + f", tag Extra {a_['conf'].get('tag_extra')}/{b_['conf'].get('tag_extra')}; nao ha evidencia de par ordinaria x extraordinaria"
           + ("; mesmo carimbo de versao: possivel duplicacao de catalogo" if a_["conf"].get("versao_titulo") == b_["conf"].get("versao_titulo") else "; carimbos de versao distintos"))
    impacto = max([abs(fnum(l["dif_sobre_total_validado_do_ano_pct"]) or 0) for l in linhas_par] + [0])
    base = dict(ano=ano, dist=dist, empresa=nomes.get(dist, a_["inv"]["empresa"]), grupo=grupo, risco=risco, impacto_max_sobre_total_validado_pct=round(impacto, 5),
                ativos_com_diferenca=n_dif, tipo_publicacoes=rep,
                item_A=ia, url_A=a_["inv"]["url_item"], versao_A=a_["conf"].get("versao_titulo", ""), publicado_catalogo_A=a_["conf"].get("publicado_em_catalogo", ""),
                competencia_declarada_A=a_["inv"]["data_base"], DAT_INC_A=a_["conf"].get("DAT_INC", ""), DAT_FNL_A=a_["conf"].get("DAT_FNL", ""), DAT_EXT_A=a_["conf"].get("DAT_EXT", ""),
                sha256_A=a_["ck"]["source_sha256"], registros_A=a_["ck"]["rows"],
                item_B=ib, url_B=b_["inv"]["url_item"], versao_B=b_["conf"].get("versao_titulo", ""), publicado_catalogo_B=b_["conf"].get("publicado_em_catalogo", ""),
                competencia_declarada_B=b_["inv"]["data_base"], DAT_INC_B=b_["conf"].get("DAT_INC", ""), DAT_FNL_B=b_["conf"].get("DAT_FNL", ""), DAT_EXT_B=b_["conf"].get("DAT_EXT", ""),
                sha256_B=b_["ck"]["source_sha256"], registros_B=b_["ck"]["rows"],
                entidades_contagem_diferente=";".join(cont) or "nenhuma", dif_esquema=";".join(tipo(".esquema")) or "nenhuma", dif_dda=";".join(tipo(".grupo_dda")) or "nenhuma",
                dif_tuc=";".join(tipo(".grupo_tuc_mcpse")) or "nenhuma", dif_vinculos=";".join(tipo(".grupo_vinculos")) or "nenhuma",
                dif_atributos=";".join(sorted(set(tipo(".grupo_demais")) | set(tipo(".grupo_identidade")))) or "nenhuma", dif_geometria=";".join(tipo(".geometria")) or "nenhuma",
                evidencia_favor_A=" | ".join(fav_a) or "nenhuma identificada", evidencia_favor_B=" | ".join(fav_b) or "nenhuma identificada",
                recomendacao_tecnica=rec, DECISAO_HUMANA="PENDENTE", justificativa_decisao="", decidido_por="", decidido_em="")
    for l in linhas_par: DUP.append({**base, **l})
    dup_resumo.append(base)
ordem_imp = {(b["ano"], b["dist"]): i + 1 for i, b in enumerate(sorted(dup_resumo, key=lambda b: (b["grupo"] != "COM_DIFERENCA_TOTAIS", -b["impacto_max_sobre_total_validado_pct"], -b["ativos_com_diferenca"])))}
for l in DUP: l["ordem_impacto"] = ordem_imp[(l["ano"], l["dist"])]
DUP.sort(key=lambda l: (l["ordem_impacto"], l["ativo"]))
grava("DECISOES_DUPLICATAS_13_PARES.csv", DUP, ["ordem_impacto"] + [k for k in DUP[0] if k != "ordem_impacto"])

# ======================= 2) SINAIS TEMPORAIS (238) =======================
con = duckdb.connect(); con.execute("SET memory_limit='768MB'; SET threads=2")


def pq(ano, dist, ent):
    if ano == 2025:
        return sorted(p.as_posix() for p in (R / "staging_parquet" / f"DIST={dist}" / "DATA_BASE=2025-12-31" / f"entidade={ent}").glob("*.parquet")) or None
    c = cel.get((ano, dist, "consumidores"), {}).get("item_id")
    p = H / "parquet" / str(ano) / dist / (c or "x") / f"{ent}.parquet"
    return [p.as_posix()] if c and p.exists() else None


def persistencia(ativo, dist, a0, a1):
    """Fracao dos COD_ID da entidade de origem (nivel entidade, sem o filtro do ativo) do ano a0 que reaparecem em a1."""
    tot = com = n1 = 0
    for e in ENT.get(ativo, []):
        f0, f1 = pq(a0, dist, e), pq(a1, dist, e)
        if not f0 or not f1: return None
        x = con.execute(f"WITH a AS (SELECT DISTINCT CAST(COD_ID AS VARCHAR) k FROM read_parquet({f0})), b AS (SELECT DISTINCT CAST(COD_ID AS VARCHAR) k FROM read_parquet({f1})) "
                        f"SELECT (SELECT count(*) FROM a), (SELECT count(*) FROM b), (SELECT count(*) FROM a JOIN b USING (k))").fetchone()
        tot += x[0]; n1 += x[1]; com += x[2]
    return (tot, n1, com)


def contagens(ativo, dist, ano):
    """Registros por entidade de origem no ano (None se o Parquet nao existe)."""
    out = {}
    for e in ENT.get(ativo, []):
        f = pq(ano, dist, e); out[e] = None if not f else con.execute(f"SELECT count(*) FROM read_parquet({f})").fetchone()[0]
    return out


bloq_dyn = {}
SIG = rd(O / "qa_sinais_temporais_classificados.csv")
ev_ano = {e["evento_id"]: (e["dist_destino_2025"], e["dist_origem"], int(e["data_efetivacao"][:4])) for e in eventos}
cz = CASOS
RAN = []
for r in SIG:
    d, at, a0, a1 = r["dist"], r["ativo"], int(r["de"]), int(r["para"]); x0, x1 = float(r["valor_de"]), float(r["valor_para"])
    p0, p1 = pop.get((d, a0, conceito.get(at, at))), pop.get((d, a1, conceito.get(at, at)))
    sh = lambda p: None if not p or not p[0] or p[1] is None else p[1] / p[0]
    s0, s1 = sh(p0), sh(p1)
    nac = tot_nac.get((a1, at)) or None
    imp = None if not nac else abs(x1 - x0) / nac
    cat, causa, evid, conf, acao = None, "", [], "SEM_EXPLICACAO", "investigar com a distribuidora antes de homologar"
    suc = [k for k, (dd, do, ae) in ev_ano.items() if d in (dd, do) and a0 < ae <= a1]
    # casos investigados nesta fase
    if d == "39" and at == "consumidores" and (a0, a1) == (2024, 2025):
        t = {f"{x[0]}->{x[1]}": x[2] for x in cz.get("enel_ce_transicao_ucbt_2024_2025", [])}
        cat, conf = "alteracao_cadastral", "EXPLICACAO_PLAUSIVEL"
        causa = "recadastramento em 2025: COD_ID das UCBT totalmente recodificados e saneamento de SIT_ATIV (registros DS caem de ~1,68 mi para ~174 mil)"
        evid = [f"UCBT 2024 AT={cz['sit_ativ_39']['2024_UCBT'].get('AT')} DS={cz['sit_ativ_39']['2024_UCBT'].get('DS')}; 2025 AT={cz['sit_ativ_39']['2025_UCBT'].get('AT')} DS={cz['sit_ativ_39']['2025_UCBT'].get('DS')}",
                f"COD_ID UCBT 2024 presentes em 2025: {t.get('AT->AT', 0) + t.get('DS->AT', 0) + t.get('DS->DS', 0)} de {t.get('AT->AUSENTE_2025', 0) + t.get('DS->AUSENTE_2025', 0) + t.get('DS->AT', 0) + t.get('DS->DS', 0)}",
                "2022 tinha 3,23 mi AT: os valores 2023-2024 (~2,4 mi) podem estar subestimados pela marcacao DS"]
        acao = "marcar quebra de comparabilidade 2024->2025 e ressalva 2023-2024; confirmar com a distribuidora qual cadastro de SIT_ATIV reflete o parque real"
    elif d == "6072" and at == "consumidores" and a1 == 2025:
        cat, conf = "anomalia_fonte", "CAUSA_COMPROVADA (marcacao na fonte) / HIPOTESE (erro de cadastro)"
        causa = "GDB 2025 marca 3.449.443 UCBT como DS (desativada); em 2024 havia 3.462.456 UCBT AT"
        evid = [f"SIT_ATIV 2024 UCBT {cz['sit_ativ_6072']['2024_UCBT']}; 2025 UCBT {cz['sit_ativ_6072']['2025_UCBT']}"]
        acao = "manter valor com ressalva destacada ou bloquear o indicador 2025; consultar ANEEL/distribuidora"
    elif d == "5370" and at == "consumidores" and a1 == 2025:
        cat, conf = "anomalia_fonte", "CAUSA_COMPROVADA"
        causa = "entidade UCBT sem registros no GDB 2025 (consumidores de baixa tensao ausentes da publicacao)"
        evid = [f"UCBT 2024={sum(cz['sit_ativ_5370']['2024_UCBT'].values())} registros; UCBT 2025={sum(cz['sit_ativ_5370']['2025_UCBT'].values())}; UCMT 2025={cz['sit_ativ_5370']['2025_UCMT']}"]
        acao = "bloquear consumidores 2025 da Coopera ate republicacao; nao converter em zero"
    elif d == "5374" and at == "iluminacao" and 2024 in (a0, a1):
        p = cz["cooperzem_pip_persistencia"]; n = cz["cooperzem_pip_registros"]
        cat, conf = "anomalia_fonte", "CAUSA_COMPROVADA"
        causa = "PIP 2024 incompleto: a publicacao 2024 contem so parte dos pontos, que reaparecem em 2025"
        evid = [f"PIP registros 2023={n['2023'][0]}, 2024={n['2024'][0]}, 2025={n['2025'][0]}", f"COD_ID 2024 presentes em 2023: {p['2023_2024']}; em 2025: {p['2024_2025']}; de 2023 presentes em 2025: {p['2023_2025']}"]
        acao = "bloquear iluminacao 2024 da Cooperzem (valor incompleto); nao interpolar"
    elif d == "385" and at == "rede_at" and (a0, a1) == (2022, 2023):
        e = cz["elektro_SSDAT"]; m = cz["elektro_SSDMT"]
        cat, conf = "alteracao_cadastral", "HIPOTESE"
        causa = "2022 inclui ~22 mil segmentos AT (~8.300 km, ~208 circuitos) que deixam de existir a partir de 2023, sem migrar para MT; possivel saneamento de perimetro (linhas de outro agente/DIT)"
        evid = [f"SSDAT 2022 {e['2022'][0]:.0f} seg/{e['2022'][1]:.0f} km; 2023 {e['2023'][0]:.0f}/{e['2023'][1]:.0f} km; 2024 {e['2024'][0]:.0f}/{e['2024'][1]:.0f} km",
                f"segmentos 2023 ja presentes em 2022: {cz['elektro_ssdat_persistencia']['2022_2023']}; circuitos 2022={cz['elektro_ssdat_tensao_2022'][0][0]} 2023={cz['elektro_ssdat_tensao_2023'][0][0]}",
                f"SSDMT 2022 {m['2022'][1]:.0f} km -> 2023 {m['2023'][1]:.0f} km (+{m['2023'][1] - m['2022'][1]:.0f} km): nao absorve a reducao"]
        acao = "tratar rede AT Elektro 2022 como quebra de serie; confirmar com a distribuidora"
    elif x0 >= 50 and x1 < 0.1 * x0 and any(v == 0 for v in contagens(at, d, a1).values()) and all((v or 0) > 0 for v in contagens(at, d, a0).values()):
        c0, c1 = contagens(at, d, a0), contagens(at, d, a1)
        cat, conf = "anomalia_fonte", "CAUSA_COMPROVADA"
        causa = "entidade de origem sem registros na publicacao de " + str(a1) + ": " + ",".join(e for e, v in c1.items() if v == 0)
        evid = [f"registros {a0}: {c0}; {a1}: {c1}"]
        acao = f"bloquear o indicador {a1} ate republicacao; nao converter em zero"; bloq_dyn[(a1, d, at)] = causa + " (causa comprovada)"
    elif suc:
        cat, conf, causa = "sucessao_societaria", "EXPLICACAO_PLAUSIVEL", f"evento {suc[0]} efetivado entre {a0} e {a1}"
        acao = "usar a serie de perimetro comparavel (PONTES_SUCESSOES_HISTORICAS.csv)"
    elif r["comparabilidade"].startswith("quebra") or (s0 is not None and s1 is not None and abs(s1 - s0) > 0.05):
        cat, conf = "alteracao_classificacao", "EXPLICACAO_PLAUSIVEL"
        causa = "mudanca na codificacao TUC/MCPSE (parcela sem TUC alterada), nao crescimento fisico"
        evid = [f"comparabilidade={r['comparabilidade']}", f"parcela sem TUC {'' if s0 is None else round(100 * s0, 1)}% -> {'' if s1 is None else round(100 * s1, 1)}%"]
        acao = "sinalizar quebra de classificacao na variacao; nao tratar como crescimento"
    elif at == "geradores" and x1 > x0:
        cat, conf, causa = "variacao_real_plausivel", "EXPLICACAO_PLAUSIVEL", "expansao da geracao distribuida (consistente com a tendencia setorial)"
        acao = "publicar; variacao real esperada"
    elif max(x0, x1) < 50:
        cat, conf, causa = "base_pequena", "SEM_EXPLICACAO", "base inferior a 50 unidades: variacao relativa pouco informativa"
        acao = "publicar com nota de base pequena; baixa prioridade"
    else:
        cat = "sem_evidencia_suficiente"
    if cat in ("sem_evidencia_suficiente", "alteracao_classificacao", "base_pequena") and not causa.startswith("recad"):
        try:
            p = persistencia(at, d, a0, a1)
        except Exception as ex:
            p = None; evid.append(f"persistencia nao calculada: {str(ex)[:60]}")
        if p:
            t0, t1, cm = p; fr = cm / t0 if t0 else None
            evid.append(f"identidade COD_ID (nivel entidade {'/'.join(ENT[at])}): {cm} de {t0} registros de {a0} reaparecem em {a1} ({'' if fr is None else round(100 * fr, 1)}%); {t1} registros em {a1}")
            if cat == "sem_evidencia_suficiente" and fr is not None:
                if fr < 0.5:
                    cat, conf, causa = "alteracao_cadastral", "EXPLICACAO_PLAUSIVEL", "baixa persistencia de COD_ID: recadastramento/recodificacao, nao variacao fisica"
                    acao = "sinalizar quebra de comparabilidade; confirmar com a distribuidora"
                elif fr >= 0.9 and x1 > x0:
                    cat, conf, causa = "variacao_real_plausivel", "HIPOTESE", "registros anteriores persistem e ha inclusao de novos: expansao ou complemento de cadastro"
                    acao = "publicar com ressalva; confirmar se ha obra/expansao ou cadastramento tardio"
                elif fr >= 0.9 and x1 < x0:
                    cat, conf, causa = "alteracao_cadastral", "HIPOTESE", "registros persistem mas o ativo filtrado diminui: provavel reclassificacao de atributo (TUC/tipo)"
                    acao = "sinalizar; verificar codificacao do ativo"
    score = (imp or 0) * 1000 + min(abs(fnum(r["variacao_pct"]) or 100), 1000) / 100
    RAN.append(dict(dist=d, empresa=r["empresa"], ativo=at, medida=r["medida"], conceito=conceito.get(at, at), ano_de=a0, ano_para=a1, valor_de=x0, valor_para=x1,
                    variacao_abs=round(x1 - x0, 6), variacao_pct=r["variacao_pct"], sem_tuc_pct_de="" if s0 is None else round(100 * s0, 2), sem_tuc_pct_para="" if s1 is None else round(100 * s1, 2),
                    impacto_sobre_total_validado_pct="" if imp is None else round(100 * imp, 5), comparabilidade_serie=r["comparabilidade"], categoria_fase3=r["categoria"],
                    categoria=cat, possivel_causa=causa or "nao identificada", evidencias=" | ".join(evid) or "nenhuma alem da variacao", grau_confianca=conf,
                    acao_recomendada=acao, score_prioridade=round(score, 4), DECISAO_HUMANA="PENDENTE"))
RAN.sort(key=lambda x: -x["score_prioridade"])
for i, x in enumerate(RAN): x["prioridade"] = i + 1
grava("RANKING_ANOMALIAS_TEMPORAIS.csv", RAN, ["prioridade"] + [k for k in RAN[0] if k != "prioridade"])
sinal_cel = collections.defaultdict(list)
for x in RAN:
    if x["categoria"] in ("variacao_real_plausivel",) and x["grau_confianca"] == "EXPLICACAO_PLAUSIVEL": continue
    for a in (x["ano_de"], x["ano_para"]): sinal_cel[(a, x["dist"], x["ativo"])].append(f"{x['categoria']}#{x['prioridade']}")
bloq_rec = {(2025, "5370", "consumidores"): "UCBT sem registros no GDB 2025 (causa comprovada)", (2024, "5374", "iluminacao"): "PIP 2024 incompleto (causa comprovada por identidade de COD_ID)", **bloq_dyn}

# ======================= 3) PONTES DE SUCESSAO =======================
PON = []
for e in eventos:
    dd, do, ef = e["dist_destino_2025"], e["dist_origem"], e["data_efetivacao"]
    qs = {r["evento_id"]: r for r in rd(O / "qa_sucessao.csv")}.get(e["evento_id"], {})
    for at in ATIVOS:
        for ano in ANOS:
            co, cd = cel.get((ano, do, at)), cel.get((ano, dd, at))
            vo = fnum(co["valor"]) if co and co["status"] == "validado" else None
            vd = fnum(cd["valor"]) if cd and cd["status"] == "validado" else None
            if co is None and cd is None: continue
            st_o = co["status"] if co else "sem_publicacao"; st_d = cd["status"] if cd else "sem_publicacao"
            if e["evento_id"] == "EMR_ENF_2022":
                regra = "origem ja contida no destino (5/5 conjuntos da ENF na EMR em 2022): NAO somar"
                vp = vd; stp = "validado" if vd is not None else st_d
            else:
                regra = "areas disjuntas (8 x 67 conjuntos, intersecao 0); absorcao em 2023 nao verificada (EPB 2023 com par pendente): ponte PENDENTE, nao somada"
                vp = None if ano == 2022 else vd; stp = "pendente_ponte" if ano == 2022 else (st_d if vd is None else "validado")
            PON.append(dict(evento_id=e["evento_id"], tipo_evento=e["tipo_evento"], dist_destino_2025=dd, empresa_destino=nomes.get(dd, ""), dist_origem=do, empresa_origem=nomes.get(do, ""),
                            data_efetivacao=ef, fonte_oficial=e["fonte_oficial"], status_ponte=qs.get("status", ""), prova=f"CONJ origem={qs.get('conj_origem')} destino={qs.get('conj_destino')} intersecao={qs.get('intersecao')}",
                            ano=ano, ativo=at, medida=MED[at][0], valor_origem="" if vo is None else vo, status_origem=st_o, valor_destino_original="" if vd is None else vd, status_destino=st_d,
                            valor_perimetro_comparavel="" if vp is None else vp, status_perimetro=stp,
                            valor_se_somado_indevidamente="" if vo is None or vd is None else vo + vd,
                            impacto_da_ponte_pct="" if vo is None or not vd else round(100 * vo / vd, 3), regra_aplicada=regra))
# renomeacoes (mesmo codigo DIST): nao exigem ponte
for dist, antigo in (("6585", "EMG (Energisa Minas Gerais)"), ("6072", "Enel GO")):
    PON.append(dict(evento_id=f"RENOMEACAO_{dist}", tipo_evento="renomeacao (mesmo codigo DIST)", dist_destino_2025=dist, empresa_destino=nomes.get(dist, ""), dist_origem=dist, empresa_origem=antigo,
                    data_efetivacao="nao_disponivel", fonte_oficial="catalogo ANEEL (EMG_6585_2020-12-31; GDB Enel_GO_6072 e Equatorial_GO_6072 equivalentes em 2022)", status_ponte="nao_requer_ponte",
                    prova="mesmo codigo DIST em todos os anos", ano="", ativo="todos", medida="", valor_origem="", status_origem="", valor_destino_original="", status_destino="",
                    valor_perimetro_comparavel="", status_perimetro="serie_continua", valor_se_somado_indevidamente="", impacto_da_ponte_pct="", regra_aplicada="sem soma; serie da mesma DIST"))
grava("PONTES_SUCESSOES_HISTORICAS.csv", PON)
# teste de absorcao EPB 2023 (dois itens do par) contra EPB 2022 + EBO 2022
absorcao = []
for x in pares_inv[("2023", "6600")]:
    cj = json.loads((H / "proc/2023/6600" / x["item_id"] / "conceitos_r3.json").read_text(encoding="utf-8"))
    for at in CHAVE:
        v23 = fnum(cj["ativos"][at]["valor"]); v22 = fnum(cel[(2022, "6600", at)]["valor"]); vo = fnum(cel[(2022, "6611", at)]["valor"]) if (2022, "6611", at) in cel else None
        absorcao.append(dict(item_2023=x["item_id"], ativo=at, epb_2023=v23, epb_2022=v22, ebo_2022=vo, soma_2022=(v22 or 0) + (vo or 0),
                             razao_2023_sobre_epb2022=None if not v22 else round(v23 / v22, 4), razao_2023_sobre_soma=None if not v22 else round(v23 / ((v22 or 0) + (vo or 0)), 4)))

# ======================= 4) MATRIZ DE HOMOLOGACAO =======================
cob = {int(r["ano"]): r for r in rd(O / "cobertura_por_ano.csv")}
MAT = []
for (ano, dist, at), c in sorted(cel.items(), key=lambda k: (k[0][0], int(k[0][1]), k[0][2])):
    st = c["status"]; it = c["item_id"]
    cfs = conf_por.get((ano, dist), [])
    cf = CONF.get(it) or (cfs[0] if len(cfs) == 1 else None)  # 2025: a serie usa o marcador 'pacote-2025'; associa pela DIST/ano
    if not cf and st == "revisao_pendente" and cfs: cf = cfs[0]
    if it == "pacote-2025" and cf: it = cf["item_id"]
    integ = {"validado": "OK", "ausente": "OK", "campo_ausente": "OK", "bloqueado": "OK", "revisao_pendente": "OK_PAR_PENDENTE", "competencia_divergente": "EXCLUIDO_COMPETENCIA",
             "sem_publicacao": "SEM_PUBLICACAO", "nao_processado": "NAO_PROCESSADO"}.get(st, st)
    qual = {"validado": "validado", "ausente": "ativo_inexistente_na_BDGD_da_DIST", "campo_ausente": "campo_ausente_no_layout", "bloqueado": "bloqueado_pela_regra"}.get(st, "sem_valor")
    sinais = sinal_cel.get((ano, dist, at), [])
    flags = []
    if c["comparabilidade"].startswith("quebra"): flags.append("quebra_classificacao")
    if sinais: flags.append("sinal_temporal:" + ",".join(sinais[:3]))
    classe = cf.get("classe_intervalo", "SEM_EVIDENCIA_SUFICIENTE") if cf else ""
    tagx = cf.get("tag_extra", "") if cf else ""
    ressalvas = []
    if st in ("sem_publicacao", "ausente", "campo_ausente"): est, mot = "NAO_DISPONIVEL", {"sem_publicacao": "DIST sem publicacao no ano (N/D, nunca zero)", "ausente": "ativo inexistente na BDGD da DIST (N/D)", "campo_ausente": "campo ausente no layout do ano (N/D)"}[st]
    elif st in ("competencia_divergente", "bloqueado"): est, mot = "BLOQUEADO", "arquivo com BASE.DAT_FNL de outra competencia" if st == "competencia_divergente" else (c["motivo"] or "valor nao homologavel pela regra")
    elif st in ("revisao_pendente", "nao_processado"): est, mot = "PENDENTE_DECISAO", "publicacoes multiplas divergentes: escolha humana (DECISOES_DUPLICATAS_13_PARES.csv)" if st == "revisao_pendente" else "nao processado"
    elif (ano, dist, at) in bloq_rec: est, mot = "PENDENTE_DECISAO", "recomenda-se BLOQUEAR: " + bloq_rec[(ano, dist, at)]
    elif classe == "INCONSISTENTE": est, mot = "PENDENTE_DECISAO", "BASE inconsistente no item em uso: " + cf.get("detalhe_intervalo", "")
    else:
        if classe == "INTERVALO_NAO_ANUAL": ressalvas.append("intervalo BASE nao anual: " + cf.get("detalhe_intervalo", ""))
        if tagx == "sim": ressalvas.append("tag Extra no catalogo (significado nao documentado" + ("; presente em 100% do ciclo 2025" if ano == 2025 else "") + ")")
        if "quebra_classificacao" in flags: ressalvas.append("quebra de classificacao: " + (c["motivo_comparabilidade"] or ""))
        if sinais: ressalvas.append("sinal temporal (RANKING_ANOMALIAS_TEMPORAIS.csv #" + ",".join(s.split("#")[1] for s in sinais[:3]) + ")")
        if (ano, dist, at) == (2025, "6072", "consumidores"): ressalvas.insert(0, "Equatorial GO 2025: 3.449.443 UCBT marcadas DS na fonte; valor segue a regra UC v3 mas provavelmente subestima o parque")
        if (ano, dist) == (2022, "6612"): ressalvas.insert(0, "NAO SOMAR ao Brasil/painel: conjuntos da ENF (6612) ja contidos na EMR (6585) em 2022 (EMR_ENF_2022, ja_incluida)")
        if dist == "39" and at == "consumidores" and ano in (2023, 2024): ressalvas.insert(0, "Enel CE: ~1,6-1,7 mi UCBT marcadas DS em 2023-2024 e saneadas em 2025; valor pode estar subestimado")
        ress_tag_2025 = ano == 2025 and ressalvas == ["tag Extra no catalogo (significado nao documentado; presente em 100% do ciclo 2025)"]
        if ano == 2025 and (not ressalvas or ress_tag_2025): est, mot = "HOMOLOGADO", "pacote 2025 homologado; intervalo BASE 01/01-31/12 compativel" + ("; tag Extra registrada como observacao" if ress_tag_2025 else "")
        elif ressalvas: est, mot = "APTO_COM_RESSALVAS", "; ".join(ressalvas)
        else: est, mot = "COMPLETO_TECNICO", "validado pelas regras automaticas; sem sinal, quebra ou ressalva de BASE"
    pub = est in ("HOMOLOGADO", "COMPLETO_TECNICO", "APTO_COM_RESSALVAS")
    MAT.append(dict(ano=ano, dist=dist, empresa=c["empresa"], ativo=at, medida=c["medida"], unidade=c["unidade"], nivel="DIST",
                    valor=c["valor"] if pub and c["valor"] != "" else "", valor_nd="sim" if not (pub and c["valor"] != "") else "nao",
                    estado_publicacao=est, motivo=mot, status_serie=st, status_homologacao_vigente=cob[ano]["status_ano"],
                    integridade_processamento=integ, qualidade_indicador=qual, flags=";".join(flags), conformidade_base_intervalo=classe, tag_extra_catalogo=tagx,
                    cobertura="publicada" if st != "sem_publicacao" else "sem_publicacao", autorizacao_publicacao=("AUTORIZADO (homologacao 2025 vigente)" if est == "HOMOLOGADO" else "AGUARDA_DECISAO_HUMANA"),
                    item_id=it, sha256_fonte=c["source_sha256"], n_dist_incluidas="", n_dist_excluidas="", dists_excluidas="", universo=""))
# agregados BR e painel balanceado (somente celulas publicaveis; pendentes/bloqueadas identificadas)
PUB = ("HOMOLOGADO", "COMPLETO_TECNICO", "APTO_COM_RESSALVAS")
NAO_SOMAR = {(2022, "6612")}  # predecessora ja contida no destino: excluida de qualquer agregado (evita dupla contagem)
idx = collections.defaultdict(dict)
for m in MAT: idx[(m["ativo"], m["ano"])][m["dist"]] = m
for at in ATIVOS:
    painel = None
    for ano in ANOS:
        ms = idx[(at, ano)]
        inc = [m for m in ms.values() if m["estado_publicacao"] in PUB and m["valor"] != "" and (ano, m["dist"]) not in NAO_SOMAR]
        exc = [m for m in ms.values() if m["estado_publicacao"] in ("PENDENTE_DECISAO", "BLOQUEADO")]
        ress = any(m["estado_publicacao"] == "APTO_COM_RESSALVAS" for m in inc)
        if ano in (2022, 2023): est, mot, val = "BLOQUEADO", f"nao e total nacional completo: {len(exc)} DIST pendentes/bloqueadas; use o painel balanceado" + ("; ENF 6612 fora da soma (ja contida na EMR)" if ano == 2022 else ""), ""
        elif exc or ress: est, mot, val = "APTO_COM_RESSALVAS", f"soma de {len(inc)} DIST publicaveis; {len(exc)} pendentes/bloqueadas fora da soma" + ("; inclui celulas com ressalva" if ress else ""), round(sum(float(m["valor"]) for m in inc), 6)
        else: est, mot, val = ("HOMOLOGADO" if ano == 2025 else "COMPLETO_TECNICO"), f"soma de {len(inc)} DIST", round(sum(float(m["valor"]) for m in inc), 6)
        MAT.append(dict(ano=ano, dist="BR", empresa="Brasil (soma das DIST publicaveis)", ativo=at, medida=MED[at][0], unidade=MED[at][1], nivel="BRASIL", valor=val, valor_nd="sim" if val == "" else "nao",
                        estado_publicacao=est, motivo=mot, status_serie="", status_homologacao_vigente=cob[ano]["status_ano"], integridade_processamento="", qualidade_indicador="",
                        flags="", conformidade_base_intervalo="", tag_extra_catalogo="", cobertura=f"{len(inc)} DIST com valor", autorizacao_publicacao="AGUARDA_DECISAO_HUMANA" if est != "HOMOLOGADO" else "AUTORIZADO (homologacao 2025 vigente)",
                        item_id="", sha256_fonte="", n_dist_incluidas=len(inc), n_dist_excluidas=len(exc), dists_excluidas=";".join(sorted((m["dist"] for m in exc), key=int)),
                        universo="DIST publicaveis do ano", valor_soma_parcial_nao_publicar=round(sum(float(m["valor"]) for m in inc), 6) if ano in (2022, 2023) else ""))
    univ = [d for d in idx[(at, 2022)] if all(idx[(at, a)].get(d, {}).get("estado_publicacao") in PUB and idx[(at, a)].get(d, {}).get("valor") not in ("", None) for a in ANOS)]
    for ano in ANOS:
        val = round(sum(float(idx[(at, ano)][d]["valor"]) for d in univ), 6)
        MAT.append(dict(ano=ano, dist="PAINEL_BALANCEADO", empresa=f"Painel balanceado ({len(univ)} DIST com os 4 anos publicaveis)", ativo=at, medida=MED[at][0], unidade=MED[at][1], nivel="PAINEL",
                        valor=val, valor_nd="nao", estado_publicacao="APTO_COM_RESSALVAS", motivo="universo fixo nos 4 anos; nao representa o total nacional", status_serie="",
                        status_homologacao_vigente="", integridade_processamento="", qualidade_indicador="", flags="", conformidade_base_intervalo="", tag_extra_catalogo="",
                        cobertura=f"{len(univ)} DIST", autorizacao_publicacao="AGUARDA_DECISAO_HUMANA", item_id="", sha256_fonte="", n_dist_incluidas=len(univ), n_dist_excluidas="",
                        dists_excluidas="", universo=";".join(sorted(univ, key=int)), valor_soma_parcial_nao_publicar=""))
campos = list(MAT[0]) + ["valor_soma_parcial_nao_publicar"]
for m in MAT: m.setdefault("valor_soma_parcial_nao_publicar", "")
grava("MATRIZ_HOMOLOGACAO_2022_2025.csv", MAT, campos)

resumo = dict(
    celulas_dist=collections.Counter(m["estado_publicacao"] for m in MAT if m["nivel"] == "DIST"),
    celulas_dist_por_ano={a: collections.Counter(m["estado_publicacao"] for m in MAT if m["nivel"] == "DIST" and m["ano"] == a) for a in ANOS},
    brasil={f"{m['ano']}|{m['ativo']}": [m["estado_publicacao"], m["valor"], m["n_dist_incluidas"], m["n_dist_excluidas"]] for m in MAT if m["nivel"] == "BRASIL" and m["ativo"] in CHAVE},
    pares=[{k: b[k] for k in ("ano", "dist", "empresa", "grupo", "risco", "impacto_max_sobre_total_validado_pct", "ativos_com_diferenca", "versao_A", "versao_B", "recomendacao_tecnica")} | {"ordem": ordem_imp[(b["ano"], b["dist"])]} for b in dup_resumo],
    top20=[{k: x[k] for k in ("prioridade", "dist", "empresa", "ativo", "ano_de", "ano_para", "valor_de", "valor_para", "variacao_pct", "impacto_sobre_total_validado_pct", "categoria", "grau_confianca", "possivel_causa")} for x in RAN[:20]],
    sinais_por_categoria=collections.Counter(x["categoria"] for x in RAN), sinais_por_confianca=collections.Counter(x["grau_confianca"] for x in RAN),
    absorcao_epb=absorcao)
(EV / "fase4_resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print(json.dumps({k: resumo[k] for k in ("celulas_dist", "sinais_por_categoria", "sinais_por_confianca")}, default=str))

# evidencia quantitativa da ponte EPB <- EBO (ambos os itens do par EPB 2023)
with open(EV / "absorcao_epb_ebo_2023.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, list(absorcao[0]), lineterminator="\n"); w.writeheader(); w.writerows(absorcao)
