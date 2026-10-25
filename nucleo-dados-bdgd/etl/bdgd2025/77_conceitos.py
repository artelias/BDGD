"""R3 — cubos por CONCEITO de ativo, inventarios por subestacao/alimentador/conjunto e regra UC v3.

Cada conceito (config/conceitos_2025.json) junta as entidades BDGD de origem num cubo conjunto EXATO:
GROUP BY de todas as dimensoes do cubo. Qualquer combinacao de filtros dessas dimensoes e respondida
somando linhas do mesmo cubo (nunca multiplicando percentuais marginais). Dimensao inexistente numa
entidade = 'NA' (nao se aplica). Atributos de instalacao chegam aos equipamentos por juncao com a tabela
de instalacao DEDUPLICADA por codigo (sem multiplicar linhas): codigo ambiguo -> 'AMBIGUO', sem destino -> 'SEM_VINCULO'.

Regra UC v3 (consumidores): COD_ID publicado e anonimizado (SHA-256, 64 hex). Unidade = (COD_ID, PN_CON), unida
entre UCBT/UCMT/UCAT por DIST; situacao 'AT' se qualquer registro da chave estiver ativado (DDA TSITATI).
Registros repetidos da mesma chave (ex.: troca de classe no ano) contam uma vez; mesmo codigo em pontos de
conexao distintos conta como unidades distintas.

Saidas por DIST (checkpoint): proc/DIST=*/conceitos.csv, inventario_{sub,ctmt,conj}.csv, conceitos_qa.json.
Uso: 77_conceitos.py [--dists 26,31] [--forcar]"""
import argparse, csv, json, os, pathlib, sys, time
from decimal import Decimal
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import bdgd_etl as E
import duckdb

DB, R = E.DB, E.R
PROC, PQ = R / "proc", R / "staging_parquet"
SEM, NA, AMB, ORF = "SEM_CODIGO", "NA", "AMBIGUO", "SEM_VINCULO"
CFG = json.loads((pathlib.Path(__file__).parent / "config" / "conceitos_2025.json").read_text(encoding="utf-8"))
UC_CLASSE = ("CASE WHEN {c} = '" + SEM + "' THEN '" + SEM + "' WHEN {c} LIKE 'RE%' THEN 'RE' WHEN {c} LIKE 'IN%' THEN 'IN' WHEN {c} LIKE 'CO%' THEN 'CO' "
             "WHEN {c} LIKE 'RU%' THEN 'RU' WHEN {c} LIKE 'PP%' THEN 'PP' WHEN {c} LIKE 'IP%' THEN 'IP' WHEN {c} LIKE 'SP%' THEN 'SP' "
             "WHEN {c} IN ('CPR', 'CPRVE') THEN 'CP' WHEN {c} = 'CSPS' THEN 'CS' ELSE 'OUTRO' END")


def texto(s):
    """Recupera nomes gravados em UTF-8 e lidos como CP850 no GDB de origem (ex.: 'CAL├çOENE' -> 'CALÇOENE'); se nao recuperar, mantem."""
    s = (s or "").strip()
    if any(0x2500 <= ord(ch) <= 0x257F or ch in "ÃÂ" for ch in s):
        for enc in ("cp850", "cp437"):
            try: return s.encode(enc).decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError): pass
    return s


def nz(expr): return f"coalesce(nullif(trim(CAST({expr} AS VARCHAR)), ''), '{SEM}')"
def lit(v): return "'" + str(v).replace("'", "''") + "'"


class Dist:
    def __init__(self, d, con):
        self.d, self.con = d, con
        self.base = PQ / f"DIST={d}" / f"DATA_BASE={DB}"
        conv = json.loads((self.base / "conversao.json").read_text(encoding="utf-8"))
        self.linhas = {e: v["linhas"] for e, v in conv["entidades"].items()}
        self._cols = {}
        for e, n in self.linhas.items():
            if n: con.execute(f"CREATE OR REPLACE TEMP VIEW v_{e} AS SELECT * FROM read_parquet('{(self.base / f'entidade={e}' / 'part-0.parquet').as_posix()}')")

    def tem(self, e): return bool(self.linhas.get(e))
    def cols(self, e):
        if e not in self._cols:
            self._cols[e] = {r[0] for r in self.con.execute(f"DESCRIBE SELECT * FROM v_{e}").fetchall()} if self.tem(e) else set()
        return self._cols[e]
    def c(self, e, col, alias="s"):
        """codigo normalizado da coluna ou NA quando a entidade nao tem o campo"""
        return nz(f'{alias}."{col}"') if col in self.cols(e) else lit(NA)


def link(D, nome, alvos, attrs):
    """Tabela de instalacao deduplicada: uma linha por codigo. alvos = {entidade: rotulo_nivel}."""
    partes = []
    for e, niv in alvos.items():
        if not D.tem(e): continue
        sel = ", ".join(f"{D.c(e, a)} AS {a.lower()}" for a in attrs)
        partes.append(f"SELECT trim(CAST(s.COD_ID AS VARCHAR)) k, {lit(niv)} nivel, {sel} FROM v_{e} s")
    if not partes:
        D.con.execute(f"CREATE OR REPLACE TEMP TABLE {nome} AS SELECT NULL::VARCHAR k, NULL::VARCHAR nivel, " + ", ".join(f"NULL::VARCHAR {a.lower()}" for a in attrs) + " WHERE false")
        return
    agg = ", ".join(f"CASE WHEN count(DISTINCT {a.lower()}) = 1 THEN any_value({a.lower()}) ELSE '{AMB}' END {a.lower()}" for a in ["nivel"] + attrs)
    D.con.execute(f"CREATE OR REPLACE TEMP TABLE {nome} AS SELECT k, {agg} FROM ({' UNION ALL '.join(partes)}) GROUP BY k")


def lk(campo):
    """dimensao vinda da instalacao vinculada; sem destino -> SEM_VINCULO"""
    return f"coalesce(u.{campo}, '{ORF}')"


# ------------------------------------------------------------------ fontes por conceito
def fontes(D):
    """Para cada conceito: lista de (entidade, from_sql, where, {dim: expr}, {medida: expr})."""
    c = D.c
    pot = "sum(CAST(p.pot AS DECIMAL(38,6)))"
    km = "sum(CAST(s.COMP AS DECIMAL(38,6)))"   # metros em DECIMAL; km = metros / 1000 em Decimal do Python (exato)
    F = {}
    F["consumidores"] = [("UC*", "ucu s", None, {
        "nivel": "s.nivel", "situacao": "s.situacao", "classe": UC_CLASSE.format(c="s.clas_sub"), "subclasse": "s.clas_sub", "grupo_tensao": "s.gru_ten",
        "grupo_tarifario": "s.gru_tar", "fases": "s.fas_con", "area": "s.are_loc", "municipio": "s.mun"}, {"quantidade": "count(*)"})] if D.con.execute("SELECT count(*) FROM ucu").fetchone()[0] else []
    F["geradores"] = [(e, f"v_{e} s", None, {"nivel": lit(n), "situacao": c(e, "SIT_ATIV"), "grupo_tensao": c(e, "GRU_TEN"), "fases": c(e, "FAS_CON"), "municipio": c(e, "MUN")},
                       {"quantidade": "count(*)"}) for e, n in (("UGBT", "BT"), ("UGMT", "MT"), ("UGAT", "AT")) if D.tem(e)]
    F["iluminacao"] = [("PIP", "v_PIP s", None, {"lampada": c("PIP", "TIPO_LAMP"), "situacao": c("PIP", "SIT_ATIV"), "area": c("PIP", "ARE_LOC"), "fases": c("PIP", "FAS_CON"),
                        "municipio": c("PIP", "MUN")}, {"quantidade": "count(*)"})] if D.tem("PIP") else []
    def rede(e, n, circ, lkc):
        j = f"v_{e} s"
        j += f" LEFT JOIN lk_seg g ON g.k = trim(CAST(s.TIP_CND AS VARCHAR))" if "TIP_CND" in D.cols(e) else " LEFT JOIN (SELECT NULL k, NULL mat_fas_1) g ON false"
        j += f" LEFT JOIN {lkc} t ON t.k = trim(CAST(s.\"{circ}\" AS VARCHAR))" if circ and circ in D.cols(e) else " LEFT JOIN (SELECT NULL k, NULL ten_nom) t ON false"
        ten = f"coalesce(t.ten_nom, '{ORF}')" if circ and circ in D.cols(e) else lit(NA)
        return (e, j, None, {"nivel": lit(n), "fases": c(e, "FAS_CON"), "area": c(e, "ARE_LOC"), "instalacao": c(e, "TIP_INST"), "propriedade": c(e, "POS"),
                             "situacao_contabil": c(e, "SITCONT"), "material_condutor": f"coalesce(g.mat_fas_1, '{ORF}')" if "TIP_CND" in D.cols(e) else lit(NA),
                             "tensao_nominal": ten}, {"extensao_km": km})
    F["redes"] = [rede(e, n, circ, lkc) for e, n, circ, lkc in (("SSDBT", "BT", None, None), ("SSDMT", "MT", "CTMT", "lk_ctmt"), ("SSDAT", "AT", "CTAT", "lk_ctat")) if D.tem(e)]
    F["ramais"] = [("RAMLIG", "v_RAMLIG s", None, {"fases": c("RAMLIG", "FAS_CON"), "area": c("RAMLIG", "ARE_LOC"), "instalacao": c("RAMLIG", "TIP_INST"),
                    "propriedade": c("RAMLIG", "POS"), "situacao_contabil": c("RAMLIG", "SITCONT")}, {"extensao_km": km})] if D.tem("RAMLIG") else []
    tr = []
    for e, n, fk, ln in (("EQTRMT", "MT", "UNI_TR_MT", "lk_trmt"), ("EQTRAT", "AT", "UNI_TR_AT", "lk_trat"), ("EQTRM", "ME", None, None)):
        if not D.tem(e): continue
        j = f"v_{e} s LEFT JOIN {ln} u ON u.k = trim(CAST(s.\"{fk}\" AS VARCHAR))" if fk and fk in D.cols(e) else f"v_{e} s"
        has_u = j != f"v_{e} s"
        if "POT_NOM" in D.cols(e): j += " LEFT JOIN pot p ON p.cod = trim(CAST(s.POT_NOM AS VARCHAR))"
        tr.append((e, j, None, {"tipo": c(e, "TUC"), "a1": c(e, "A1"), "nivel": lit(n), "fases": c(e, "FAS_CON"), "classe_tensao": c(e, "CLAS_TEN"),
                                "potencia_nominal": c(e, "POT_NOM"), "area": lk("are_loc") if has_u else lit(NA), "instalacao": c(e, "TIP_INST"),
                                "situacao_contabil": c(e, "SITCONT"), "municipio": lk("mun") if has_u else lit(NA)},
                   {"quantidade": "count(*)", "potencia_kva": pot if "POT_NOM" in D.cols(e) else "NULL"}))
    F["transformadores"] = tr
    F["seccionamento"] = [("EQSE", "v_EQSE s LEFT JOIN lk_se u ON u.k = trim(CAST(s.UN_SE AS VARCHAR))" if "UN_SE" in D.cols("EQSE") else "v_EQSE s", None,
                           {"tipo": c("EQSE", "TUC"), "a1": c("EQSE", "A1"), "nivel": lk("nivel"), "fases": c("EQSE", "FAS_CON"), "classe_tensao": c("EQSE", "CLAS_TEN"),
                            "area": lk("are_loc"), "meio_isolante": c("EQSE", "MEI_ISO"), "situacao_contabil": c("EQSE", "SITCONT"), "municipio": lk("mun")},
                           {"quantidade": "count(*)"})] if D.tem("EQSE") else []
    F["reguladores"] = [("EQRE", "v_EQRE s LEFT JOIN lk_re u ON u.k = trim(CAST(s.UN_RE AS VARCHAR)) LEFT JOIN pot p ON p.cod = trim(CAST(s.POT_NOM AS VARCHAR))", None,
                         {"tipo": c("EQRE", "TUC"), "nivel": lk("nivel"), "tipo_regulador": lk("tip_regu"), "fases": c("EQRE", "LIG_FAS_P"), "potencia_nominal": c("EQRE", "POT_NOM"),
                          "situacao_contabil": c("EQRE", "SITCONT"), "municipio": lk("mun")},
                         {"quantidade": "count(*)", "potencia_kva": pot})] if D.tem("EQRE") else []
    F["compensacao"] = [("EQCR", "v_EQCR s LEFT JOIN lk_cr u ON u.k = trim(CAST(s.UN_CR AS VARCHAR))", None,
                         {"tipo": c("EQCR", "TUC"), "a1": c("EQCR", "A1"), "nivel": lk("nivel"), "fases": lk("fas_con"), "area": lk("are_loc"), "potencia_reativa": lk("pot_nom"),
                          "situacao_contabil": c("EQCR", "SITCONT"), "municipio": lk("mun")}, {"quantidade": "count(*)"})] if D.tem("EQCR") else []
    F["medidores"] = [("EQME", "v_EQME s", None, {"tipo": c("EQME", "TUC"), "a1": c("EQME", "A1"), "tecnologia": c("EQME", "TIP_UNID"), "fases": c("EQME", "FAS_CON"),
                       "situacao_contabil": c("EQME", "SITCONT")}, {"quantidade": "count(*)"})] if D.tem("EQME") else []
    F["estruturas"] = [("PONNOT", "v_PONNOT s", None, {"tipo_estrutura": c("PONNOT", "TIP_PN"), "tipo": c("PONNOT", "TUC"), "a1": c("PONNOT", "A1"), "material": c("PONNOT", "MAT"), "estrutura": c("PONNOT", "ESTR"),
                        "altura": c("PONNOT", "ALT"), "esforco": c("PONNOT", "ESF"), "area": c("PONNOT", "ARE_LOC"), "propriedade": c("PONNOT", "POS"),
                        "situacao_contabil": c("PONNOT", "SITCONT"), "municipio": c("PONNOT", "MUN")}, {"quantidade": "count(*)"})] if D.tem("PONNOT") else []
    F["subestacoes"] = [("SUB", "v_SUB s", None, {"propriedade": c("SUB", "POS")}, {"quantidade": "count(*)"})] if D.tem("SUB") else []
    F["alimentadores"] = [("CTMT", "v_CTMT s", None, {"tensao_nominal": c("CTMT", "TEN_NOM")}, {"quantidade": "count(*)"})] if D.tem("CTMT") else []
    F["circuitos_at"] = [("CTAT", "v_CTAT s", None, {"tensao_nominal": c("CTAT", "TEN_NOM")}, {"quantidade": "count(*)"})] if D.tem("CTAT") else []
    F["conjuntos"] = [("CONJ", "v_CONJ s", None, {}, {"quantidade": "count(*)"})] if D.tem("CONJ") else []
    F["barramentos"] = [("BAR", "v_BAR s", None, {"tensao_nominal": c("BAR", "TEN_NOM"), "tipo": c("BAR", "TUC"), "instalacao": c("BAR", "TIP_INST")}, {"quantidade": "count(*)"})] if D.tem("BAR") else []
    F["bays"] = [("BAY", "v_BAY s", None, {"tipo_bay": c("BAY", "SUB_GRP"), "propriedade": c("BAY", "POS")}, {"quantidade": "count(*)"})] if D.tem("BAY") else []
    return F


def prepara(D, K):
    con = D.con
    con.execute("CREATE OR REPLACE TEMP TABLE pot AS SELECT * FROM (VALUES ('x', 0.0::DOUBLE)) t(cod, pot) WHERE false")
    con.executemany("INSERT INTO pot VALUES (?,?)", [(cd, v[1]) for cd, v in K.dda["TPOTAPRT"].items() if v[1] is not None])
    # instalacoes deduplicadas por codigo (atributos de localizacao e vinculos topologicos)
    link(D, "lk_trmt", {"UNTRMT": "MT"}, ["ARE_LOC", "MUN", "CTMT", "SUB", "CONJ"])
    link(D, "lk_trat", {"UNTRAT": "AT"}, ["ARE_LOC", "MUN", "SUB", "CONJ"])
    link(D, "lk_se", {"UNSEAT": "AT", "UNSEMT": "MT", "UNSEBT": "BT"}, ["ARE_LOC", "MUN", "CTMT", "SUB", "CONJ"])
    link(D, "lk_re", {"UNREAT": "AT", "UNREMT": "MT"}, ["TIP_REGU", "MUN", "CTMT", "SUB", "CONJ"])
    link(D, "lk_cr", {"UNCRAT": "AT", "UNCRMT": "MT", "UNCRBT": "BT"}, ["FAS_CON", "ARE_LOC", "POT_NOM", "MUN", "CTMT", "SUB", "CONJ"])
    link(D, "lk_seg", {"SEGCON": "-"}, ["MAT_FAS_1"])
    link(D, "lk_ctmt", {"CTMT": "MT"}, ["TEN_NOM"])
    link(D, "lk_ctat", {"CTAT": "AT"}, ["TEN_NOM"])
    # consumidores: regra UC v3
    partes = []
    for e, n in (("UCBT", "BT"), ("UCMT", "MT"), ("UCAT", "AT")):
        if not D.tem(e): continue
        cs = D.cols(e)
        ene = " + ".join(f"coalesce(TRY_CAST(s.ENE_{m:02d} AS DOUBLE), 0)" for m in range(1, 13) if f"ENE_{m:02d}" in cs) or "0"
        partes.append(f"""SELECT trim(CAST(s.COD_ID AS VARCHAR)) cod, coalesce(nullif(trim(CAST(s.PN_CON AS VARCHAR)), ''), '') pn, {lit(n)} nivel, {D.c(e, 'SIT_ATIV')} sit,
            {D.c(e, 'CLAS_SUB')} clas_sub, {D.c(e, 'GRU_TEN')} gru_ten, {D.c(e, 'GRU_TAR')} gru_tar, {D.c(e, 'FAS_CON')} fas_con, {D.c(e, 'ARE_LOC')} are_loc,
            {D.c(e, 'MUN')} mun, {D.c(e, 'CTMT')} ctmt, {D.c(e, 'CTAT')} ctat, {D.c(e, 'SUB')} sub, {D.c(e, 'CONJ')} conj, ({ene}) ene FROM v_{e} s""")
    if partes:
        con.execute(f"CREATE OR REPLACE TEMP TABLE ucr AS {' UNION ALL '.join(partes)}")
        con.execute("""CREATE OR REPLACE TEMP TABLE ucu AS
            SELECT cod, pn, nivel, CASE WHEN sit = 'AT' THEN 'AT' ELSE sit END situacao, clas_sub, gru_ten, gru_tar, fas_con, are_loc, mun, ctmt, ctat, sub, conj
            FROM ucr WHERE cod IS NOT NULL AND cod <> ''
            QUALIFY row_number() OVER (PARTITION BY cod, pn ORDER BY (sit = 'AT') DESC, ene DESC, nivel, clas_sub, fas_con, are_loc, mun, ctmt, sub, conj, gru_tar, gru_ten) = 1""")
    else:
        con.execute("CREATE OR REPLACE TEMP TABLE ucr AS SELECT NULL::VARCHAR cod WHERE false")
        con.execute("CREATE OR REPLACE TEMP TABLE ucu AS SELECT NULL::VARCHAR cod, NULL::VARCHAR pn, NULL::VARCHAR nivel, NULL::VARCHAR situacao, NULL::VARCHAR clas_sub, NULL::VARCHAR gru_ten, "
                    "NULL::VARCHAR gru_tar, NULL::VARCHAR fas_con, NULL::VARCHAR are_loc, NULL::VARCHAR mun, NULL::VARCHAR ctmt, NULL::VARCHAR ctat, NULL::VARCHAR sub, NULL::VARCHAR conj WHERE false")


def uc_qa(D):
    """estatisticas da regra UC v3 por tabela e para a uniao (somente contagens)"""
    out = {}
    for e in ("UCBT", "UCMT", "UCAT"):
        if not D.tem(e): continue
        r = D.con.execute(f"""SELECT count(*), count(*) FILTER (WHERE s.SIT_ATIV = 'AT'), count(DISTINCT s.COD_ID) FILTER (WHERE s.SIT_ATIV = 'AT'),
            count(DISTINCT (s.COD_ID, coalesce(nullif(trim(CAST(s.PN_CON AS VARCHAR)), ''), ''))) FILTER (WHERE s.SIT_ATIV = 'AT'), count(*) FILTER (WHERE s.COD_ID IS NULL),
            count(*) FILTER (WHERE length(trim(CAST(s.COD_ID AS VARCHAR))) = 64) FROM v_{e} s""").fetchone()
        out[e] = dict(zip(["registros", "registros_ativados", "codigos_ativados", "unidades_ativas_v3", "cod_id_nulo", "cod_id_sha256"], r))
    u = D.con.execute("SELECT count(*), count(*) FILTER (WHERE situacao = 'AT') FROM ucu").fetchone()
    out["uniao"] = {"unidades_v3": u[0], "unidades_ativas_v3": u[1]}
    return out


def cubos(D, F):
    out, qa = [], []
    for cid, cfg in CFG["conceitos"].items():
        fs = F.get(cid, [])
        for cubo, dims in cfg["cubos"].items():
            for (ent, frm, where, dmap, meds) in fs:
                if cubo == "municipio" and dmap.get("municipio", lit(NA)) == lit(NA): continue
                sel = [dmap.get(dm, lit(NA)) for dm in dims]
                mcols = [meds.get(m, "NULL") for m in ("quantidade", "extensao_km", "potencia_kva")]
                q = f"SELECT {', '.join(sel + mcols) if sel else ', '.join(mcols)} FROM {frm} {('WHERE ' + where) if where else ''} {'GROUP BY ALL' if sel else ''}"
                for r in D.con.execute(q).fetchall():
                    k, (qt, ext, pw) = list(r[:len(dims)]), r[len(dims):]
                    out.append({"conceito": cid, "cubo": cubo, "entidade": ent, "chave": json.dumps(k, ensure_ascii=False), "quantidade": "" if qt is None else int(qt),
                                "extensao_km": "" if ext is None else str(Decimal(ext) / 1000), "potencia_kva": "" if pw is None else str(pw)})
    # reconciliacao: cada cubo de cada fonte soma o mesmo total da fonte (sem perda nem multiplicacao)
    tot = {}
    for r in out:
        t = tot.setdefault((r["conceito"], r["cubo"], r["entidade"]), [0, Decimal(0), Decimal(0)])
        t[0] += int(r["quantidade"] or 0); t[1] += Decimal(r["extensao_km"] or 0); t[2] += Decimal(r["potencia_kva"] or 0)
    ref = {}
    for cid, fs in F.items():
        for (ent, frm, where, dmap, meds) in fs:
            mcols = [meds.get(m, "NULL") for m in ("quantidade", "extensao_km", "potencia_kva")]
            r = D.con.execute(f"SELECT {', '.join(mcols)} FROM {frm} {('WHERE ' + where) if where else ''}").fetchone()
            ref[(cid, ent)] = [int(r[0] or 0), Decimal(str(r[1] or 0)) / 1000, Decimal(str(r[2] or 0))]
    for (cid, cubo, ent), t in tot.items():
        rf = ref[(cid, ent)]
        ok = t[0] == rf[0] and abs(t[1] - rf[1]) <= Decimal("0.000001") and abs(t[2] - rf[2]) <= Decimal("0.000001")
        qa.append({"conceito": cid, "cubo": cubo, "entidade": ent, "quantidade": t[0], "ref_quantidade": rf[0], "ok": ok})
        assert ok or cubo == "municipio", (D.d, cid, cubo, ent, t, rf)
    return out, qa, ref


# ------------------------------------------------------------------ inventarios
def inventarios(D):
    con, out = D.con, {}
    def g(sql):
        try: return con.execute(sql).fetchall()
        except duckdb.Error as x: raise RuntimeError(f"{D.d}: {x}\n{sql}")
    def add(tab, rows, campo):
        for k, v in rows:
            tab.setdefault(k if k is not None else SEM, {})[campo] = v
    def sum_km(e, chave):
        if not (D.tem(e) and chave in D.cols(e)): return []
        return [(k, None if m is None else Decimal(m) / 1000) for k, m in g(f"SELECT {D.c(e, chave)}, sum(CAST(s.COMP AS DECIMAL(38,6))) FROM v_{e} s GROUP BY 1")]
    def cnt(e, chave, where=None): return g(f"SELECT {D.c(e, chave)}, count(*) FROM v_{e} s {('WHERE ' + where) if where else ''} GROUP BY 1") if D.tem(e) and chave in D.cols(e) else []
    def via(e, fk, lkt, campo, where=None, medida="count(*)", extra=""):
        if not D.tem(e) or fk not in D.cols(e): return []
        return g(f"SELECT coalesce(u.{campo}, '{ORF}'), {medida} FROM v_{e} s LEFT JOIN {lkt} u ON u.k = trim(CAST(s.\"{fk}\" AS VARCHAR)) {extra} {('WHERE ' + where) if where else ''} GROUP BY 1")
    tuc = lambda t: f"trim(CAST(s.TUC AS VARCHAR)) = '{t}'"
    potj = "LEFT JOIN pot p ON p.cod = trim(CAST(s.POT_NOM AS VARCHAR))"
    for chave, campo_uc in (("ctmt", "ctmt"), ("ctat", "ctat"), ("sub", "sub"), ("conj", "conj")):
        t = {}
        if chave == "ctat":   # circuitos de alta tensao: rede AT, consumidores e geradores AT ligados ao circuito
            add(t, g("SELECT ctat, count(*) FROM ucu WHERE situacao = 'AT' AND nivel = 'AT' GROUP BY 1"), "consumidores")
            add(t, cnt("UGAT", "CTAT", "s.SIT_ATIV = 'AT'"), "geradores")
            add(t, sum_km("SSDAT", "CTAT"), "rede_at_km")
        else:
            add(t, g(f"SELECT {campo_uc}, count(*) FROM ucu WHERE situacao = 'AT' GROUP BY 1"), "consumidores")
            for e in ("UGBT", "UGMT", "UGAT"):
                for k, v in cnt(e, chave.upper(), "s.SIT_ATIV = 'AT'"): t.setdefault(k, {})["geradores"] = t.get(k, {}).get("geradores", 0) + v
            add(t, sum_km("SSDMT", chave.upper()), "rede_mt_km"); add(t, sum_km("SSDBT", chave.upper()), "rede_bt_km")
            if chave != "sub": add(t, sum_km("RAMLIG", chave.upper()), "ramais_km")
            if chave == "conj": add(t, sum_km("SSDAT", "CONJ"), "rede_at_km")
            add(t, via("EQTRMT", "UNI_TR_MT", "lk_trmt", chave, tuc("565")), "trafo_dist")
            add(t, via("EQTRMT", "UNI_TR_MT", "lk_trmt", chave, tuc("565"), "sum(CAST(p.pot AS DECIMAL(38,6)))", potj), "trafo_dist_kva")
            if chave != "ctmt":
                f1 = dict(via("EQTRAT", "UNI_TR_AT", "lk_trat", chave, tuc("570"))); f2 = dict(via("EQTRMT", "UNI_TR_MT", "lk_trmt", chave, tuc("570")))
                add(t, [(k, f1.get(k, 0) + f2.get(k, 0)) for k in set(f1) | set(f2)], "trafo_forca")
            for nome, tc in (("chaves", "160"), ("religadores", "345"), ("disjuntores", "210")):
                add(t, via("EQSE", "UN_SE", "lk_se", chave, tuc(tc)), nome)
            add(t, via("EQRE", "UN_RE", "lk_re", chave), "reguladores")
            add(t, via("EQCR", "UN_CR", "lk_cr", chave, tuc("125")), "bancos_capacitores")
            add(t, cnt("PIP", chave.upper(), "s.SIT_ATIV = 'AT'"), "iluminacao")
            if chave == "sub":
                add(t, cnt("CTMT", "SUB"), "alimentadores"); add(t, cnt("BAR", "SUB"), "barramentos"); add(t, cnt("BAY", "SUB"), "bays")
            if chave == "conj":
                add(t, g("SELECT conj, count(DISTINCT sub) FILTER (WHERE sub NOT IN ('SEM_CODIGO', 'NA')) FROM ucu WHERE situacao = 'AT' GROUP BY 1"), "subestacoes")
                add(t, g("SELECT conj, count(DISTINCT ctmt) FILTER (WHERE ctmt NOT IN ('SEM_CODIGO', 'NA')) FROM ucu WHERE situacao = 'AT' GROUP BY 1"), "alimentadores")
        # cadastro da entidade-chave: nome e atributos; chaves sem cadastro viram um balde SEM_VINCULO
        ent = {"ctmt": "CTMT", "ctat": "CTAT", "sub": "SUB", "conj": "CONJ"}[chave]
        cad = {}
        if D.tem(ent):
            cs = D.cols(ent)
            nome = "NOME" if "NOME" in cs else ("DESCR" if "DESCR" in cs else None)
            extra = {"ctmt": ["SUB", "TEN_NOM"], "ctat": ["TEN_NOM"], "sub": ["POS"], "conj": []}[chave]
            for r in g(f"SELECT {nz('s.COD_ID')}, {('s.' + nome) if nome else 'NULL'}, {', '.join(D.c(ent, x) for x in extra) or 'NULL'} FROM v_{ent} s"):
                cad[r[0]] = {"nome": texto(r[1]), **({x.lower(): r[2 + i] for i, x in enumerate(extra)})}
        linhas = []
        for k, v in t.items():
            kk = k if (k in cad) else (k if k in (SEM, NA) else ORF)
            linhas.append((kk, v))
        merged = {}
        for k, v in linhas:
            m = merged.setdefault(k, {})
            for f, x in v.items(): m[f] = (m.get(f) or 0) + (x or 0)
        for k in cad:
            merged.setdefault(k, {})
        out[chave] = [{"chave": k, **cad.get(k, {"nome": ""}), **{f: (str(x) if isinstance(x, Decimal) else x) for f, x in v.items()}} for k, v in sorted(merged.items())]
    return out


def processa(d, K, con):
    D = Dist(d, con)
    prepara(D, K)
    F = fontes(D)
    rows, qa, ref = cubos(D, F)
    inv = inventarios(D)
    return rows, {"cubos": qa, "uc_v3": uc_qa(D), "fontes": {f"{c}|{e}": [v[0], str(v[1]), str(v[2])] for (c, e), v in ref.items()}}, inv


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dists", default=""); ap.add_argument("--forcar", action="store_true"); a = ap.parse_args()
    K = E.Conhecimento()
    ds = sorted((p.parent.name.split("=")[1] for p in PROC.glob("DIST=*/_OK")), key=int)
    if a.dists: ds = [d for d in ds if d in a.dists.split(",")]
    th, mem = os.environ.get("BDGD_DUCKDB_THREADS", "2"), os.environ.get("BDGD_DUCKDB_MEM", "2GB")
    con = duckdb.connect(); con.execute(f"SET threads={th}; SET memory_limit='{mem}'; SET temp_directory='{(R / 'tmp_duckdb').as_posix()}'; SET preserve_insertion_order=false")
    for d in ds:
        dst = PROC / f"DIST={d}" / "conceitos.csv"
        if dst.exists() and not a.forcar: continue
        t0 = time.time()
        rows, qa, inv = processa(d, K, con)
        tmp = dst.with_suffix(".tmp")
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, ["conceito", "cubo", "entidade", "chave", "quantidade", "extensao_km", "potencia_kva"], lineterminator="\n"); w.writeheader(); w.writerows(rows)
        for chave, linhas in inv.items():
            cols = sorted({c for r in linhas for c in r}, key=lambda c: (c not in ("chave", "nome"), c))
            with open(PROC / f"DIST={d}" / f"inventario_{chave}.csv", "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, cols, lineterminator="\n"); w.writeheader(); w.writerows(linhas)
        (PROC / f"DIST={d}" / "conceitos_qa.json").write_text(json.dumps(qa, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
        tmp.replace(dst)
        print(f"{E.now()} DIST {d}: {len(rows)} linhas de cubo, inventarios {[(k, len(v)) for k, v in inv.items()]} ({time.time() - t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
