"""Pipeline por DIST (competencia 2025-12-31): download -> validacao BASE -> Parquet (staging) -> agregados + QA + ARAT.
Cada etapa grava checkpoint; DIST com falha vai para quarentena (_FALHA.json) sem interromper o lote."""
import csv, datetime, hashlib, json, os, pathlib, shutil, time, traceback, urllib.request, zipfile
import duckdb, numpy as np, pyarrow as pa, pyarrow.compute as pc, pyarrow.parquet as pq, pyogrio, pyproj, shapely, shapely.geometry

DB = "2025-12-31"
# catalogos IA Builder (relacionamentos, DDA, schema) e raiz de trabalho local; configuraveis por ambiente
K = pathlib.Path(os.environ.get("BDGD_KNOWLEDGE", "C:/GEOIA/GEOIA_DATA_HUB/knowledge"))
R = pathlib.Path(os.environ.get("BDGD_ROOT", "D:/NUCLEO_BDGD_2025"))
NAO_ENTIDADE = {"BASE"}
TABELAS_AUX = {"CRVCRG", "BE", "EP", "PT", "PNT"}          # registros auxiliares, nao sao ativos fisicos
UC = ("UCBT", "UCMT", "UCAT")
EXT = ("SSDAT", "SSDBT", "SSDMT", "RAMLIG")               # COMP em metros
POTCOD = {"EQTRMT": "TPOTAPRT", "EQTRAT": "TPOTAPRT", "EQRE": "TPOTAPRT"}   # codigo DDA -> kVA
POTCOD_KVAR = {"UNCRAT": "TPOTRTV", "UNCRMT": "TPOTRTV", "UNCRBT": "TPOTRTV"}
UG = ("UGBT", "UGMT", "UGAT")                              # POT_INST em kW (nao homologada)
LIMITE_MAPA_ALTO_KVA = 100_000.0                           # codigo DDA de potencia acima disso e sinalizado, nao corrigido
MAX_CARD_FACETA = 500


def now(): return datetime.datetime.now().isoformat(timespec="seconds")
def wcsv(path, rows, cols=None):
    cols = cols or list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, cols); w.writeheader(); w.writerows(rows)


class Conhecimento:
    def __init__(self):
        self.sch = json.load(open(K / "BDGD_ENTITY_SCHEMA_SEMANTIC_REV5.json", encoding="utf-8"))
        self.rel = json.load(open(K / "BDGD_RELATIONSHIPS_AND_DDA_REFS_REV5.json", encoding="utf-8"))
        dda = json.load(open(K / "BDGD_DDA_CATALOG_M10.json", encoding="utf-8"))
        self.dda = {t["table"]: {str(v["COD_ID"]).strip(): (v.get("DESCR"), v.get("POT")) for v in t["values"]} for t in dda["tables"]}
        self.desig = {e["entity"]: e["designation"] for e in self.sch["entities"]}
        self.fam = {e: g for g, es in self.sch["semantic_groups"].items() for e in es}
        self.dims = {}
        self.dims_sem_tabela = []
        for x in self.rel["dda_references"]:
            (self.dims.setdefault(x["source_entity"], []) if x["dda_table"] in self.dda else self.dims_sem_tabela).append(
                (x["source_field"], x["dda_table"]) if x["dda_table"] in self.dda else (x["source_entity"], x["source_field"], x["dda_table"]))
        # vinculos agrupados por (origem, campo): destinos alternativos (polimorficos) formam uma uniao
        g = {}
        for l in self.rel["entity_links"]:
            g.setdefault((l["source_entity"], l["source_field"]), []).append((l["target_entity"], l["target_field"]))
        self.links = g


# ---------------------------------------------------------------- download / inspecao / conversao
def baixar(r, raw):
    d = raw / f"DIST={r['dist']}" / f"DATA_BASE={DB}"; d.mkdir(parents=True, exist_ok=True)
    dest = d / f"{r['item_id']}.gdb.zip"; total = int(r["tamanho_bytes"]); meta = d / "download.json"
    if meta.exists():
        m = json.loads(meta.read_text(encoding="utf-8"))
        if m.get("bytes") == total and m.get("zip_integro") and dest.exists() and dest.stat().st_size == total: return m
    for tent in range(6):
        have = dest.stat().st_size if dest.exists() else 0
        if have > total: dest.unlink(); have = 0
        if have == total: break
        try:
            req = urllib.request.Request(r["url_download"], headers={"Range": f"bytes={have}-"})
            with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "ab" if resp.status == 206 else "wb") as f:
                while chunk := resp.read(1 << 20): f.write(chunk)
        except Exception as e:
            time.sleep(min(60, 2 ** tent))
    if not dest.exists() or dest.stat().st_size != total: raise RuntimeError(f"download incompleto {dest.stat().st_size if dest.exists() else 0}/{total}")
    h = hashlib.sha256()
    with open(dest, "rb") as f:
        while b := f.read(1 << 22): h.update(b)
    ok = zipfile.ZipFile(dest).testzip() is None
    rec = {"dist": r["dist"], "item_id": r["item_id"], "arquivo": str(dest), "bytes": total, "esperado": total, "sha256": h.hexdigest(),
           "zip_integro": ok, "baixado_em": now()}
    meta.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    if not ok: raise RuntimeError("zip corrompido")
    return rec


def inspecionar(dl, d):
    f = d / "inspecao.json"
    if f.exists():
        c = json.loads(f.read_text(encoding="utf-8")); c.setdefault("dist", c.get("dist_inventario")); return c
    z = zipfile.ZipFile(dl["arquivo"])
    gdb = sorted({n.split("/")[0] for n in z.namelist() if ".gdb" in n.split("/")[0]})
    if len(gdb) != 1: raise RuntimeError(f"esperava 1 .gdb no zip, achei {gdb}")
    src = f"/vsizip/{pathlib.Path(dl['arquivo']).as_posix()}/{gdb[0]}"
    out = {"dist": dl["dist"], "item_id": dl["item_id"], "sha256": dl["sha256"], "gdb": gdb, "src": src, "camadas": {}}
    for nome, geom in pyogrio.list_layers(src):
        info = pyogrio.read_info(src, layer=nome, force_feature_count=True)
        c = {"geometria": geom, "n": int(info["features"]), "crs": info["crs"], "campos": list(info["fields"])}
        if "DIST" in c["campos"] and c["n"]:
            _, t = pyogrio.read_arrow(src, layer=nome, columns=["DIST"], read_geometry=False)
            c["dist_valores"] = {str(r["values"]): int(r["counts"]) for r in t.column("DIST").value_counts().to_pylist()}
        out["camadas"][nome] = c
    out["BASE"] = pyogrio.read_arrow(src, layer="BASE", read_geometry=False)[1].to_pylist() if "BASE" in out["camadas"] else None
    f.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    return out


def validar_base(ins):
    """Falhas que mandam o DIST para quarentena."""
    f = []
    b = (ins.get("BASE") or [None])[0]
    if not b: return ["camada BASE ausente"]
    if str(b.get("DAT_FNL")) != "31/12/2025": f.append(f"BASE.DAT_FNL={b.get('DAT_FNL')} (esperado 31/12/2025)")
    if str(b.get("DIST")) != str(ins["dist"]): f.append(f"BASE.DIST={b.get('DIST')} != {ins['dist']}")
    for n, c in ins["camadas"].items():
        outros = {k for k in (c.get("dist_valores") or {}) if k != str(ins["dist"])}
        if outros: f.append(f"{n}: DIST divergente {sorted(outros)[:5]}")
    return f


def converter(ins, pq_root):
    dist = ins["dist"]; base = pq_root / f"DIST={dist}" / f"DATA_BASE={DB}"
    if (base / "conversao.json").exists(): return json.loads((base / "conversao.json").read_text(encoding="utf-8"))
    log = {}
    for nome, c in ins["camadas"].items():
        ent = nome.removesuffix("_tab"); dest = base / f"entidade={ent}" / "part-0.parquet"
        if (dest.parent / "_OK").exists(): log[ent] = json.loads((dest.parent / "_OK").read_text()); continue
        dest.parent.mkdir(parents=True, exist_ok=True); t0 = time.time(); n = 0; w = None
        with pyogrio.open_arrow(ins["src"], layer=nome, batch_size=65536, use_pyarrow=True) as (meta, reader):
            for b in reader:
                if w is None: w = pq.ParquetWriter(dest, b.schema, compression="zstd")
                w.write_batch(b); n += b.num_rows
            if w is None: w = pq.ParquetWriter(dest, reader.schema, compression="zstd")
        w.close()
        if n != c["n"]: raise RuntimeError(f"{ent}: parquet {n} != gdb {c['n']}")
        rec = {"linhas": n, "linhas_gdb": c["n"], "crs": c["crs"], "layer": nome, "seg": round(time.time() - t0, 1)}
        (dest.parent / "_OK").write_text(json.dumps(rec)); log[ent] = rec
    conv = {"dist": dist, "item_id": ins["item_id"], "sha256_zip": ins["sha256"], "BASE": ins["BASE"][0], "entidades": log}
    (base / "conversao.json").write_text(json.dumps(conv, indent=1, default=str)); return conv


# ---------------------------------------------------------------- helpers de origem (independentes do Parquet)
def src_col(ins, layer, col):
    return pyogrio.read_arrow(ins["src"], layer=layer, columns=[col], read_geometry=False)[1].column(col)


def poligonos(g):
    g = shapely.make_valid(g)
    if g.geom_type in ("Polygon", "MultiPolygon"): return g
    ps = [x for x in getattr(g, "geoms", []) if x.geom_type in ("Polygon", "MultiPolygon")]
    return shapely.union_all(ps) if ps else g


# ---------------------------------------------------------------- processamento de um DIST
def processar(dist, inv_row, K_, out_root, ins, conv, pq_root):
    d = out_root / f"DIST={dist}"; d.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(); con.execute("SET memory_limit='3GB'; SET threads=2; SET preserve_insertion_order=false")
    con.execute(f"SET temp_directory='{(R / 'tmp_duckdb').as_posix()}'")
    pth = lambda e: (pq_root / f"DIST={dist}" / f"DATA_BASE={DB}" / f"entidade={e}" / "part-0.parquet").as_posix()
    ents = sorted(e for e in conv["entidades"] if e not in NAO_ENTIDADE)
    layer = {n.removesuffix("_tab"): n for n in ins["camadas"]}
    cols = {e: {r[0] for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{pth(e)}')").fetchall()} for e in ents}
    fatos, facetas, comp, qa, alertas, ent_info = [], [], [], [], [], {}
    linhas_total = sum(conv["entidades"][e]["linhas"] for e in ents)
    con.execute("CREATE TEMP TABLE pot(tab VARCHAR, cod VARCHAR, pot DOUBLE)")
    con.executemany("INSERT INTO pot VALUES (?,?,?)", [(t, c, v[1]) for t, m in K_.dda.items() if t in ("TPOTAPRT", "TPOTRTV") for c, v in m.items()])
    alerta = lambda ent, tipo, det, acao="": alertas.append({"dist": dist, "entidade": ent, "tipo": tipo, "detalhe": det, "acao": acao})

    # 1) DATA_BASE linha a linha
    db_ruins = {}
    for e in ents:
        if "DATA_BASE" in cols[e]:
            n = con.execute(f"SELECT count(*) FROM read_parquet('{pth(e)}') WHERE CAST(DATA_BASE AS VARCHAR) IS DISTINCT FROM '{DB}'").fetchone()[0]
            if n: db_ruins[e] = n
    if db_ruins: raise RuntimeError(f"registros com DATA_BASE != {DB}: {db_ruins}")

    # 2) totais por entidade
    for e in ents:
        p = pth(e); n_gdb = conv["entidades"][e]["linhas"]; c = cols[e]
        join = ""; potexpr = None; extexpr = None
        if e in POTCOD and "POT_NOM" in c:
            join = f"LEFT JOIN (SELECT cod, pot FROM pot WHERE tab='{POTCOD[e]}') m ON m.cod = trim(CAST(s.POT_NOM AS VARCHAR))"; potexpr = "m.pot"
        elif e == "UNTRMT" and "POT_NOM" in c: potexpr = "TRY_CAST(s.POT_NOM AS DOUBLE)"
        elif e == "UNTRAT" and "POT_NOM" in c: potexpr = "TRY_CAST(s.POT_NOM AS DOUBLE)*1000"
        if e in EXT and "COMP" in c: extexpr = "TRY_CAST(s.COMP AS DOUBLE)/1000"
        sel = "count(*), count(s.COD_ID), count(DISTINCT s.COD_ID)" if "COD_ID" in c else "count(*), 0, 0"
        sel += f", sum({extexpr}), count(*) FILTER (WHERE {extexpr} IS NULL), count(*) FILTER (WHERE {extexpr} <= 0)" if extexpr else ", NULL, 0, 0"
        sel += f", sum({potexpr}), count(*) FILTER (WHERE {potexpr} IS NULL), count(*) FILTER (WHERE {potexpr} = 0), count(*) FILTER (WHERE {potexpr} > {LIMITE_MAPA_ALTO_KVA})" if potexpr else ", NULL, 0, 0, 0"
        n, nn, nd, ext, ext_nul, ext_zero, pot, pot_nul, pot_zero, pot_alto = con.execute(f"SELECT {sel} FROM read_parquet('{p}') s {join}").fetchone()
        assert n == n_gdb, (e, n, n_gdb)
        info = dict(n=n, nn=nn, nd=nd, ext=ext, pot=pot, ext_nul=ext_nul, pot_nul=pot_nul, pot_zero=pot_zero, pot_alto=pot_alto, motivos=[], status="aprovado",
                    quantidade=n, hasid="COD_ID" in c)
        if info["hasid"] and n and nn < n: info["motivos"].append(f"cod_id_nulo:{n - nn}"); info["status"] = "alerta"
        if e in EXT and n and (ext_nul or ext_zero): info["motivos"].append(f"COMP_nulo_ou_zero:{ext_nul + ext_zero}/{n}"); info["status"] = "alerta"
        if potexpr and n and (pot_nul or pot_zero): info["motivos"].append(f"potencia_nula_ou_nao_informada:{pot_nul + pot_zero}/{n}"); info["status"] = "alerta"
        if potexpr and pot_alto: info["motivos"].append(f"{pot_alto}_registros_com_potencia>{int(LIMITE_MAPA_ALTO_KVA)}kVA (codigo DDA implausivel; valor preservado)"); info["status"] = "alerta"
        if info["hasid"] and e not in UC and e != "CRVCRG" and nn and nd < nn:
            info["motivos"].append(f"cod_id_repetido:{nn - nd}"); info["status"] = "alerta"
        ent_info[e] = info

    # 3) validacao das UCs (decisao 2)
    uc_presentes = [e for e in UC if e in ent_info and ent_info[e]["n"]]
    for e in UC:
        if e not in ent_info: continue
        i = ent_info[e]; i["quantidade"] = None
        if not i["n"]: i["quantidade"] = 0; continue
        conf = 0; chaves = [k for k in ("PN_CON", "CLAS_SUB") if k in cols[e]]
        if i["hasid"] and i["nd"] < i["nn"] and chaves:
            cond = " OR ".join(f"count(DISTINCT {k}) > 1" for k in chaves)
            conf = con.execute(f"SELECT count(*) FROM (SELECT COD_ID FROM read_parquet('{pth(e)}') GROUP BY 1 HAVING count(*) > 1 AND ({cond}))").fetchone()[0]
        i["uc_conflitos"] = conf; i["uc_dup"] = i["nn"] - i["nd"]
        ok = i["hasid"] and i["nn"] == i["n"] and conf == 0
        if ok: i["quantidade"] = i["nd"]
        else:
            i["status"] = "alerta"
            i["motivos"].append(f"contagem_distinta_nao_validada: nulos={i['n'] - i['nn']}, COD_ID_repetidos={i['uc_dup']}, repetidos_com_{'/'.join(chaves)}_conflitantes={conf}; quantidade N/D, registros e distintos preservados")
            alerta(e, "uc_cod_id_inconsistente", f"{i['n']} registros, {i['nd']} COD_ID distintos, {conf} COD_ID repetidos com atributos-chave conflitantes", "quantidade vazia; publicar registros e distintos separadamente")
        if i["uc_dup"] and conf == 0 and i["n"]: i["motivos"].append(f"COD_ID_repetido_sem_conflito:{i['uc_dup']}")
    uc_fam = {}
    if uc_presentes:
        uni = " UNION ALL ".join(f"SELECT '{e}' e, COD_ID FROM read_parquet('{pth(e)}') WHERE COD_ID IS NOT NULL" for e in uc_presentes)
        un = con.execute(f"SELECT count(DISTINCT COD_ID) FROM ({uni})").fetchone()[0]
        soma = sum(ent_info[e]["nd"] for e in uc_presentes)
        uc_fam = {"uniao_distinta": un, "soma_distintos_por_entidade": soma, "sobreposicao": soma - un,
                  "soma_registros": sum(ent_info[e]["n"] for e in uc_presentes)}
        if soma != un:
            alerta("UC*", "uc_sobreposicao_entre_entidades", f"{soma - un} COD_ID em mais de uma entidade UC (soma {soma}, uniao {un})", "KPI familia UC usa a uniao distinta; nao somar entidades")
            for e in uc_presentes: ent_info[e]["motivos"].append(f"sobreposicao_UC_entre_entidades:{soma - un}"); ent_info[e]["status"] = "alerta"
    comp.append({"dist": dist, "entidade": "UC*", "indicador": "uc_uniao_distinta", "unidade": "COD_ID", "valor": uc_fam.get("uniao_distinta"), "status": "aprovado" if uc_fam and not uc_fam["sobreposicao"] else ("alerta" if uc_fam else "nao_aplicavel"), "motivo": f"soma_por_entidade={uc_fam.get('soma_distintos_por_entidade')}; sobreposicao={uc_fam.get('sobreposicao')}"})

    # 4) UG*: potencia kW NAO homologada; distribuicao preservada por TIP_SIST
    for e in UG:
        if e not in ent_info: continue
        i = ent_info[e]; c = cols[e]
        i["motivos"].append("potencia_UG_N/D: unidade e semantica de POT_INST nao homologadas (ver complementares/alertas)")
        if i["n"] and "POT_INST" in c:
            ts = "TIP_SIST" if "TIP_SIST" in c else "'?'"
            rs = con.execute(f"""SELECT CAST({ts} AS VARCHAR), count(*), sum(TRY_CAST(POT_INST AS DOUBLE)), max(TRY_CAST(POT_INST AS DOUBLE)),
                  count(*) FILTER (WHERE TRY_CAST(POT_INST AS DOUBLE) > 75), count(*) FILTER (WHERE TRY_CAST(POT_INST AS DOUBLE) IS NULL OR TRY_CAST(POT_INST AS DOUBLE) <= 0)
                  FROM read_parquet('{pth(e)}') GROUP BY 1""").fetchall()
            for tsv, q, soma, mx, acima, invalido in rs:
                comp.append({"dist": dist, "entidade": e, "indicador": f"POT_INST_original_kW[TIP_SIST={tsv}]", "unidade": "kW (original, nao homologado)",
                             "valor": None, "status": "bloqueado", "motivo": f"registros={q}; soma_original={soma:.2f}; max={mx}; >75={acima}; nulos_ou_nao_positivos={invalido}"})
                if acima: alerta(e, "potencia_UG_acima_75kW", f"TIP_SIST={tsv}: {acima}/{q} registros com POT_INST>75 (max {mx})", "valores preservados no staging; potencia publica N/D; sem corte")
        i["ug_status_potencia"] = "bloqueado"
    # potencia em kVAr (UNCR*): fora do contrato (so kVA); fica em complementares
    for e, tab in POTCOD_KVAR.items():
        if e in ent_info and "POT_NOM" in cols[e]:
            v = con.execute(f"SELECT sum(m.pot), count(*) FILTER (WHERE m.pot IS NULL), count(*) FROM read_parquet('{pth(e)}') s LEFT JOIN (SELECT cod,pot FROM pot WHERE tab='{tab}') m ON m.cod=trim(CAST(s.POT_NOM AS VARCHAR))").fetchone()
            comp.append({"dist": dist, "entidade": e, "indicador": "potencia_kvar", "unidade": "kVAr", "valor": round(v[0], 3) if v[0] is not None else None,
                         "status": "alerta" if v[1] else "aprovado", "motivo": f"sem_mapeamento_DDA={v[1]}/{v[2]}"})

    # 5) UNTRMT x EQTRMT (decisao 5): comparacao unidade a unidade, sem somar as visoes
    for un, eq, fk in (("UNTRMT", "EQTRMT", "UNI_TR_MT"), ("UNTRAT", "EQTRAT", "UNI_TR_AT")):
        if un in ent_info and eq in ent_info and ent_info[un]["n"] and fk in cols[eq] and "POT_NOM" in cols[un]:
            m = f"(SELECT cod,pot FROM pot WHERE tab='TPOTAPRT')"; mult = 1000 if un == "UNTRAT" else 1
            r = con.execute(f"""WITH j AS (SELECT TRY_CAST(u.POT_NOM AS DOUBLE)*{mult} un, m.pot eq FROM read_parquet('{pth(un)}') u
                 JOIN read_parquet('{pth(eq)}') e ON e.{fk}=u.COD_ID LEFT JOIN {m} m ON m.cod=trim(CAST(e.POT_NOM AS VARCHAR)))
               SELECT count(*), count(*) FILTER (WHERE abs(un-coalesce(eq,-1))<=0.01*greatest(un,1)),
                 count(*) FILTER (WHERE eq IS NOT NULL AND un > 0 AND abs(eq - un*1000) <= 0.02*eq), count(*) FILTER (WHERE eq IS NULL)
               FROM j""").fetchone()
            jn, iguais, prov_mva, sem = r
            a, b = ent_info[un]["pot"] or 0, ent_info[eq]["pot"] or 0
            rel = (b - a) / a if a else None
            comp.append({"dist": dist, "entidade": f"{un}/{eq}", "indicador": "comparacao_unidade_a_unidade", "unidade": "unidades", "valor": jn,
                         "status": "alerta" if (rel is not None and abs(rel) > 0.05) or prov_mva else "aprovado",
                         "motivo": f"casam_exatamente={iguais}; provavel_POT_NOM_em_MVA_na_unidade={prov_mva}; sem_mapeamento_DDA={sem}; dif_total_kVA={rel * 100 if rel is not None else None:+.1f}%"})
            if prov_mva:
                alerta(un, "POT_NOM_provavel_MVA", f"{prov_mva} unidades com POT_NOM x1000 = potencia do EQ via DDA (valor parece estar em MVA, nao kVA)", "valor preservado; potencia exibida com alerta")
                for x in (un, eq): ent_info[x]["status"] = "alerta"; ent_info[x]["motivos"].append(f"{un}.POT_NOM_provavel_MVA:{prov_mva}_unidades")
            if rel is not None and abs(rel) > 0.05:
                alerta(f"{un}/{eq}", "divergencia_potencia", f"{un} {a:.0f} kVA vs {eq} {b:.0f} kVA ({rel * 100:+.1f}%)", "visoes sobrepostas; nao somar")
                for x in (un, eq): ent_info[x]["status"] = "alerta"; ent_info[x]["motivos"].append(f"divergencia_{un}_{eq}:{rel * 100:+.1f}%")

    # 6) vinculos IA Builder (uniao dos alvos polimorficos) + orfaos
    filtros_ind = []
    for (se, sf), alvos in K_.links.items():
        base = {"dist": dist, "origem": f"{se}.{sf}", "destinos": "|".join(f"{t}.{f}" for t, f in alvos)}
        if se not in ent_info: qa.append({**base, "status": "entidade_origem_ausente"}); continue
        alv = [(t, f) for t, f in alvos if t in ent_info and f in cols[t]]
        if sf not in cols[se] or not alv: qa.append({**base, "status": "campo_ou_destino_ausente_no_gdb"}); continue
        tgt = " UNION ".join(f"SELECT trim(CAST({f} AS VARCHAR)) k FROM read_parquet('{pth(t)}')" for t, f in alv)
        n, nn, m = con.execute(f"""WITH t AS ({tgt}), s AS (SELECT trim(CAST({sf} AS VARCHAR)) k FROM read_parquet('{pth(se)}'))
             SELECT count(*), count(*) FILTER (WHERE k IS NOT NULL AND k NOT IN ('','0')), count(*) FILTER (WHERE k IS NOT NULL AND k NOT IN ('','0') AND k IN (SELECT k FROM t)) FROM s""").fetchone()
        pct = round(100 * (nn - m) / nn, 3) if nn else None
        rep = [f"{t}.{f}" for t, f in alv if f == "COD_ID" and ent_info[t]["hasid"] and ent_info[t]["nd"] < ent_info[t]["nn"]]
        qa.append({**base, "status": "validado", "linhas_origem": n, "fk_preenchida": nn, "fk_casada": m, "orfaos": nn - m, "pct_orfaos": pct,
                   "destino_com_cod_id_repetido": "|".join(rep)})
        if pct is not None and pct > 5 and sf in ("CTMT", "SUB", "CONJ"):
            filtros_ind.append({"dist": dist, "entidade": se, "filtro": sf, "status": "indisponivel_por_qualidade",
                                "numerador_orfaos": nn - m, "denominador_fk": nn, "pct_orfaos": pct, "motivo": f"{pct}% das chaves {se}.{sf} nao existem em {sf}"})
    wcsv(d / "disponibilidade_filtros.csv", filtros_ind, ["dist", "entidade", "filtro", "status", "numerador_orfaos", "denominador_fk", "pct_orfaos", "motivo"])
    if filtros_ind: alerta("*", "filtro_indisponivel", "; ".join(sorted({f"{x['filtro']} ({x['pct_orfaos']}% orfaos)" for x in filtros_ind})), "filtro marcado indisponivel_por_qualidade; contagens independentes mantidas")

    # 7) facetas DDA (1 dimensao) + cobertura DDA
    dda_qa = []
    for e in ents:
        i = ent_info[e]
        if not i["n"]: continue
        p = pth(e); c = cols[e]
        join = ""; potexpr = None; extexpr = None
        if e in POTCOD and "POT_NOM" in c:
            join = f"LEFT JOIN (SELECT cod, pot FROM pot WHERE tab='{POTCOD[e]}') m ON m.cod = trim(CAST(s.POT_NOM AS VARCHAR))"; potexpr = "m.pot"
        elif e == "UNTRMT" and "POT_NOM" in c: potexpr = "TRY_CAST(s.POT_NOM AS DOUBLE)"
        elif e == "UNTRAT" and "POT_NOM" in c: potexpr = "TRY_CAST(s.POT_NOM AS DOUBLE)*1000"
        if e in EXT and "COMP" in c: extexpr = "TRY_CAST(s.COMP AS DOUBLE)/1000"
        for campo, tab in K_.dims.get(e, []):
            if campo not in c: dda_qa.append({"dist": dist, "entidade": e, "atributo": campo, "tabela_dda": tab, "status": "campo_ausente_no_gdb"}); continue
            dist_card = con.execute(f"SELECT count(DISTINCT trim(CAST(\"{campo}\" AS VARCHAR))) FROM read_parquet('{p}')").fetchone()[0]
            if dist_card > MAX_CARD_FACETA: dda_qa.append({"dist": dist, "entidade": e, "atributo": campo, "tabela_dda": tab, "status": "cardinalidade_alta", "codigos_distintos": dist_card}); continue
            selx = f"count(DISTINCT s.COD_ID)" if (e in UC and i["hasid"]) else "NULL"
            rs = con.execute(f"""SELECT trim(CAST(s."{campo}" AS VARCHAR)) k, count(*), {selx}, {('sum(' + extexpr + ')') if extexpr else 'NULL'}, {('sum(' + potexpr + ')') if potexpr else 'NULL'}
                 FROM read_parquet('{p}') s {join} GROUP BY 1 ORDER BY 2 DESC""").fetchall()
            assert sum(r[1] for r in rs) == i["n"], (e, campo)
            mapa = K_.dda[tab]; com = sum(r[1] for r in rs if r[0] in mapa); sem = [r[0] for r in rs if r[0] not in mapa]
            dda_qa.append({"dist": dist, "entidade": e, "atributo": campo, "tabela_dda": tab, "status": "validado", "linhas": i["n"], "linhas_com_descricao": com,
                           "pct_cobertura": round(100 * com / i["n"], 2), "codigos_distintos": len(rs), "codigos_sem_descricao": "|".join(map(str, sem[:15]))})
            for k, q, dc, ex, po in rs:
                uc_ok = e in UC and i["quantidade"] is not None
                facetas.append({"dist": dist, "entidade": e, "data_base": DB, "dimensoes_json": json.dumps({campo: k if k is not None else ""}, ensure_ascii=False),
                                "quantidade": (dc if uc_ok else (None if e in UC else q)), "quantidade_registros": q, "quantidade_cod_id_distinto": dc,
                                "extensao_km": round(ex, 5) if ex is not None else None,
                                "potencia_kva": round(po, 5) if po is not None and e not in UG else None,
                                "status_qualidade": i["status"], "motivo_qualidade": "; ".join(i["motivos"])[:500]})
    for (e, campo, tab) in K_.dims_sem_tabela:
        if e in ent_info and campo in cols[e]: dda_qa.append({"dist": dist, "entidade": e, "atributo": campo, "tabela_dda": tab, "status": "tabela_dda_ausente_no_catalogo", "observacao": "exibir N/D"})

    # 8) linhas de fato (total por entidade) + reconciliacao com a ORIGEM (GDB, leitura independente)
    for e in ents:
        i = ent_info[e]; l = layer[e]
        n_src = conv["entidades"][e]["linhas_gdb"]
        pot_pub = i["pot"] if e not in UG else None
        ext_pub = i["ext"] if e in EXT else None
        if e in EXT and i["n"] == 0: ext_pub = 0.0
        if (e in POTCOD or e in ("UNTRMT", "UNTRAT")) and i["n"] == 0: pot_pub = 0.0
        # potencia parcial/inconsistente nao e publicada (N/D) quando >0,5% dos registros sem valor
        if pot_pub is not None and i["n"] and (i["pot_nul"] + i["pot_zero"]) / i["n"] > 0.005:
            pot_pub = None; i["motivos"].append("potencia_kva_N/D: >0,5% dos registros sem potencia informada/mapeada")
        fatos.append({"dist": dist, "entidade": e, "data_base": DB, "dimensoes_json": "{}", "quantidade": i["quantidade"], "quantidade_registros": i["n"],
                      "quantidade_cod_id_distinto": i["nd"] if i["hasid"] else None, "extensao_km": round(ext_pub, 5) if ext_pub is not None else None,
                      "potencia_kva": round(pot_pub, 5) if pot_pub is not None else None, "status_qualidade": i["status"], "motivo_qualidade": "; ".join(i["motivos"])[:1000]})
        i["ext_pub"], i["pot_pub"] = ext_pub, pot_pub
        # origem independente
        def linha(metrica, vo, va, tol):
            qa_rec = {"dist": dist, "entidade": e, "metrica": metrica, "valor_origem": vo, "valor_agregado": va,
                      "diferenca": (None if vo is None or va is None else round(va - vo, 6)), "tolerancia": tol,
                      "status": "nao_aplicavel" if vo is None or va is None else ("ok" if abs(va - vo) <= tol else "falha")}
            recon.append(qa_rec)
        linha("quantidade_registros", n_src, i["n"], 0)
        if i["hasid"]:
            vo = pc.count_distinct(src_col(ins, l, "COD_ID")).as_py(); linha("quantidade_cod_id_distinto", vo, i["nd"], 0)
        if i["quantidade"] is not None: linha("quantidade", (vo if e in UC else n_src), i["quantidade"], 0)
        if e in EXT and ext_pub is not None and "COMP" in cols[e]:
            vo = (pc.sum(pc.cast(src_col(ins, l, "COMP"), pa.float64())).as_py() or 0.0) / 1000
            linha("extensao_km", round(vo, 5), round(ext_pub, 5), max(1e-5, abs(vo) * 1e-9))
        if pot_pub is not None and e in ("UNTRMT", "UNTRAT"):
            vo = (pc.sum(pc.cast(src_col(ins, l, "POT_NOM"), pa.float64())).as_py() or 0.0) * (1000 if e == "UNTRAT" else 1)
            linha("potencia_kva", round(vo, 5), round(pot_pub, 5), max(1e-5, abs(vo) * 1e-9))
        if pot_pub is not None and e in POTCOD:
            vc = src_col(ins, l, "POT_NOM").value_counts().to_pylist(); mp = K_.dda[POTCOD[e]]
            vo = sum(x["counts"] * (mp.get(str(x["values"]).strip(), (None, 0.0))[1] or 0.0) for x in vc if x["values"] is not None)
            linha("potencia_kva", round(vo, 5), round(pot_pub, 5), max(1e-5, abs(vo) * 1e-9))
    uc_status = None

    # 9) ARAT oficial
    arat = {"dist": dist, "status": "ARAT_ausente"}
    if "ARAT" in ent_info and ent_info["ARAT"]["n"]:
        pa_ = pth("ARAT"); gcol = [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{pa_}')").fetchall() if r[1] == "BLOB"][0]
        geoms = [shapely.from_wkb(r[0]) for r in con.execute(f'SELECT "{gcol}" FROM read_parquet(\'{pa_}\')').fetchall() if r[0] is not None]
        crs_o = conv["entidades"]["ARAT"]["crs"] or "EPSG:4674"
        valida0 = all(g.is_valid for g in geoms); g = poligonos(shapely.union_all(geoms))
        c = g.centroid
        laea = pyproj.CRS.from_proj4(f"+proj=laea +lat_0={c.y:.4f} +lon_0={c.x:.4f} +ellps=GRS80 +units=m +no_defs")
        to_m = pyproj.Transformer.from_crs(crs_o, laea, always_xy=True).transform
        to_ll = pyproj.Transformer.from_crs(laea, 4326, always_xy=True).transform
        tf = lambda fn, geo: shapely.transform(geo, lambda a: np.column_stack(fn(a[:, 0], a[:, 1])))
        gm = tf(to_m, g); a0 = gm.area
        soma_f = sum(tf(to_m, x).area for x in geoms if x.geom_type in ("Polygon", "MultiPolygon"))
        tol = float(np.clip(0.002 * np.sqrt(a0), 10, 100))
        for _ in range(5):
            tol_usada = tol
            gs = poligonos(gm.simplify(tol, preserve_topology=True)); da = abs(gs.area - a0) / a0
            if da <= 0.001: break
            tol /= 2
        gll = poligonos(shapely.set_precision(tf(to_ll, gs), 1e-6))
        gj = {"type": "FeatureCollection", "name": f"arat_2025_{dist}", "features": [{"type": "Feature",
              "properties": {"dist": int(dist), "data_base": DB, "source_item_id": inv_row["item_id"]}, "geometry": shapely.geometry.mapping(gll)}]}
        txt = json.dumps(gj, separators=(",", ":"))
        (d / "arat.geojson").write_text(txt, encoding="utf-8")
        arat = {"dist": dist, "status": "ok", "feicoes_origem": len(geoms), "valida_origem": bool(valida0), "crs_origem": crs_o, "crs_publicacao": "EPSG:4326",
                "crs_medicao": f"LAEA lat_0={c.y:.4f} lon_0={c.x:.4f} (GRS80)", "tolerancia_m": round(tol_usada, 2), "area_km2_origem": round(a0 / 1e6, 3),
                "area_km2_simplificada": round(gs.area / 1e6, 3), "dif_area_pct": round(100 * (gs.area - a0) / a0, 5), "partes": len(getattr(gs, "geoms", [gs])),
                "buracos": int(sum(len(p.interiors) for p in getattr(gs, "geoms", [gs]) if hasattr(p, "interiors"))),
                "sobreposicao_entre_feicoes_km2": round(max(0.0, soma_f - a0) / 1e6, 3), "vertices_origem": int(shapely.get_num_coordinates(g)),
                "vertices_saida": int(shapely.get_num_coordinates(gll)), "valida_saida": bool(gll.is_valid), "tipo_saida": gll.geom_type,
                "bytes": len(txt.encode()), "sha256": hashlib.sha256(txt.encode()).hexdigest()}
        if not arat["valida_saida"] or arat["dif_area_pct"] and abs(arat["dif_area_pct"]) > 0.1:
            alerta("ARAT", "arat_qualidade", json.dumps({k: arat[k] for k in ("valida_saida", "dif_area_pct")}), "revisar")
        if arat["sobreposicao_entre_feicoes_km2"] > 0.01:
            alerta("ARAT", "arat_feicoes_sobrepostas", f"{arat['sobreposicao_entre_feicoes_km2']} km2 de sobreposicao entre as {len(geoms)} feicoes (uniao usada)", "documentar")
    else:
        alerta("ARAT", "arat_ausente", "camada ARAT sem feicoes", "sem poligono; nao inventar")
    (d / "arat_qa.json").write_text(json.dumps(arat, indent=1), encoding="utf-8")
    con.close()

    wcsv(d / "fatos.csv", fatos); wcsv(d / "facetas.csv", facetas); wcsv(d / "complementares.csv", comp)
    wcsv(d / "qa_reconciliacao.csv", recon); wcsv(d / "qa_vinculos.csv", qa); wcsv(d / "qa_dda.csv", dda_qa); wcsv(d / "alertas.csv", alertas, ["dist", "entidade", "tipo", "detalhe", "acao"])
    resumo = {"dist": dist, "linhas_processadas": linhas_total, "entidades": len(ents), "alertas": len(alertas), "reconciliacao_falhas": sum(r["status"] == "falha" for r in recon),
              "reconciliacao_ok": sum(r["status"] == "ok" for r in recon), "arat": arat["status"], "uc_familia": uc_fam, "processado_em": now()}
    (d / "resumo.json").write_text(json.dumps(resumo, indent=1), encoding="utf-8")
    return resumo


recon = []   # preenchido dentro de processar() via escopo de modulo; limpo em executar()


def executar(inv_row, K_, raw, pq_root, out_root, log):
    global recon
    dist = inv_row["dist"]; d = out_root / f"DIST={dist}"
    if (d / "_OK").exists(): return json.loads((d / "resumo.json").read_text(encoding="utf-8"))
    recon = []
    try:
        t0 = time.time()
        dl = baixar(inv_row, raw); log(f"DIST {dist}: download ok {dl['bytes']/1e6:.0f} MB sha256 {dl['sha256'][:12]}")
        ins = inspecionar(dl, raw / f"DIST={dist}" / f"DATA_BASE={DB}")
        falhas = validar_base(ins)
        if falhas:
            d.mkdir(parents=True, exist_ok=True); (d / "_FALHA.json").write_text(json.dumps({"dist": dist, "etapa": "validacao_base", "falhas": falhas}, indent=1))
            log(f"DIST {dist}: QUARENTENA validacao_falhou {falhas}"); return {"dist": dist, "quarentena": falhas}
        conv = converter(ins, pq_root); log(f"DIST {dist}: parquet ok ({sum(v['linhas'] for v in conv['entidades'].values())} linhas)")
        res = processar(dist, inv_row, K_, out_root, ins, conv, pq_root)
        (d / "_OK").write_text(now()); (d / "_FALHA.json").unlink(missing_ok=True)
        log(f"DIST {dist}: OK {res['linhas_processadas']} linhas, {res['alertas']} alertas, recon ok={res['reconciliacao_ok']} falha={res['reconciliacao_falhas']}, ARAT {res['arat']} ({time.time()-t0:.0f}s)")
        return res
    except Exception as e:
        d.mkdir(parents=True, exist_ok=True)
        (d / "_FALHA.json").write_text(json.dumps({"dist": dist, "etapa": "excecao", "erro": repr(e), "trace": traceback.format_exc()[-3000:]}, indent=1))
        log(f"DIST {dist}: FALHA {e!r}"); return {"dist": dist, "falha": repr(e)}
