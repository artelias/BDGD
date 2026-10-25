"""Fase 4 — auditoria SOMENTE LEITURA da regra 'BDGD Ordinaria, DATA_BASE = 31/12 do ano-alvo' (2022-2025).
Para cada publicacao usada (ou candidata) na serie: metadados do catalogo oficial ANEEL/ArcGIS (titulo, tags; a tag
'Extra' e metadado do publicador), BASE (DAT_INC, DAT_FNL, DAT_EXT, DESCR) lida do GDB original (camada de 1 registro;
nenhum GDB reprocessado), DATA_BASE das entidades (Parquet ja gerado ou camada CTMT do GDB) e alternativas publicadas
para a mesma DIST/data-base. Nao altera nenhum arquivo de origem. Saida: auditoria-fase4/CONFORMIDADE_BDGD_ORDINARIA.csv"""
import collections, csv, json, pathlib, re, zipfile
import duckdb, pyogrio
from pyogrio import raw as pr

H = pathlib.Path("D:/NUCLEO_BDGD_2022_2024"); R = pathlib.Path("D:/NUCLEO_BDGD_2025")
A = R / "auditoria-fase4"
con = duckdb.connect(); con.execute("SET memory_limit='512MB'; SET threads=2")
RX = re.compile(r"_(\d{4}-\d{2}-\d{2})_([^_]+)_(\d{8}-\d{4})")

cat = {}
for f in (H / "inventario/catalogo_arcgis.json", R / "inventario/arcgis_gdb_raw.json"):
    j = json.loads(f.read_text(encoding="utf-8"))
    for x in (j["items"] if isinstance(j, dict) and "items" in j else j):
        if isinstance(x, dict) and x.get("id"): cat.setdefault(x["id"], x)
por_dist_data = collections.defaultdict(list)
for x in cat.values():
    m = RX.search(x.get("title") or "")
    dm = re.search(r"_(\d+)_\d{4}-\d{2}-\d{2}_", x.get("title") or "")
    if m and dm: por_dist_data[(dm.group(1), m.group(1))].append(x)


def extra(x): return "Extra" in (x.get("tags") or [])


def gdb_src(z):
    with zipfile.ZipFile(z) as zz:
        raizes = sorted({n[:n.lower().index(".gdb") + 4] for n in zz.namelist() if ".gdb" in n.lower()})
    return [f"/vsizip/{pathlib.Path(z).as_posix()}/{r}" for r in raizes]


def base_do_gdb(src):
    lays = {l[0].upper().removesuffix("_TAB"): l[0] for l in pyogrio.list_layers(src)}
    _, t = pr.read_arrow(src, layer=lays["BASE"], read_geometry=False)
    rec = t.to_pylist()
    # as entidades do GDB original NAO tem campo DATA_BASE (conferido em CTMT/UCBT/SSDMT); a competencia regulatoria
    # da fonte e BASE.DAT_FNL (data final do periodo). DAT_EXT e data de extracao e nao define competencia.
    return rec, None


linhas = []
fontes = []
for r in csv.DictReader(open(H / "inventario/inventario_historico_2022_2024.csv", encoding="utf-8")):
    if r["status"] in ("candidato", "revisao_pendente"): fontes.append(("hist", r["ano"], r["dist"], r["empresa"], r["item_id"], r["status"], r["sha256"]))
for r in csv.DictReader(open(R / "inventario/inventario_2025.csv", encoding="utf-8")):
    if r["item_id"]: fontes.append(("2025", "2025", r["dist"], r["empresa"], r["item_id"], r["status"], r["checksum_sha256"]))

for origem, ano, dist, emp, it, st_inv, sha in fontes:
    x = cat.get(it, {}); titulo = x.get("title", "")
    m = RX.search(titulo); db_tit = m.group(1) if m else ""
    rec, db_ent, fonte_base = [], None, ""
    try:
        if origem == "2025":
            b = R / "staging_parquet" / f"DIST={dist}" / "DATA_BASE=2025-12-31" / "entidade=BASE"
            fs = sorted(p.as_posix() for p in b.glob("*.parquet"))
            if fs:
                rec = con.execute(f"SELECT DAT_INC, DAT_FNL, DAT_EXT, DESCR, CAST(DATA_BASE AS VARCHAR) FROM read_parquet({fs})").fetchall()
                rec = [dict(DAT_INC=a, DAT_FNL=bb, DAT_EXT=c, DESCR=d) for a, bb, c, d, _ in rec]; fonte_base = "staging_parquet BASE (pacote 2025)"
            ct = sorted(p.as_posix() for p in (R / "staging_parquet" / f"DIST={dist}" / "DATA_BASE=2025-12-31" / "entidade=CTMT").glob("*.parquet"))
            if ct: db_ent = ["ETL:" + v[0][:10] for v in con.execute(f"SELECT DISTINCT CAST(DATA_BASE AS VARCHAR) FROM read_parquet({ct}) LIMIT 5").fetchall()]
        else:
            z = next((H / "raw" / ano / dist / it).glob("*.zip"), None)
            if z:
                srcs = gdb_src(z); rec, db_ent = [], []
                for s in srcs:
                    rr, dd = base_do_gdb(s); rec += rr; db_ent += (dd or [])
                fonte_base = f"GDB original ({len(srcs)} GDB no ZIP)"
    except Exception as e:
        fonte_base = f"erro de leitura: {str(e)[:80]}"
    bases = rec or [{}]
    di = ";".join(str(b.get("DAT_INC")) for b in bases); df = ";".join(str(b.get("DAT_FNL")) for b in bases)
    de = ";".join(str(b.get("DAT_EXT")) for b in bases); ds = ";".join(str(b.get("DESCR")) for b in bases)
    alvo_br = f"31/12/{ano}"
    periodo_anual = bool(rec) and all(str(b.get("DAT_INC")) == f"01/01/{ano}" and str(b.get("DAT_FNL")) == alvo_br for b in rec)
    fnl_ok = bool(rec) and all(str(b.get("DAT_FNL")) == alvo_br for b in rec)
    alternativas = [a for a in por_dist_data.get((dist, f"{ano}-12-31"), []) if a["id"] != it]
    # estado do item na serie
    ck = (H / "proc" / ano / dist / it / "checkpoint.json") if origem == "hist" else None
    fl = (H / "proc" / ano / dist / it / "failure.json") if origem == "hist" else None
    if origem == "2025": uso = "pacote_2025" if st_inv.startswith("homologad") or st_inv in ("processada", "homologada_piloto") else st_inv
    elif ck.exists(): uso = "na_serie" if st_inv == "candidato" else "par_duplicado_processado"
    elif fl.exists(): uso = "excluido_competencia" if "DAT_FNL" in fl.read_text(encoding="utf-8") else "falha"
    else: uso = "nao_processado"
    # classificacao do tipo (sem usar so o nome do arquivo)
    if not x: tipo, fonte_tipo = "TIPO_NAO_COMPROVADO", "item ausente do catalogo baixado"
    elif extra(x): tipo, fonte_tipo = "EXTRAORDINARIA_INDICADA", "tag oficial 'Extra' no catalogo ANEEL/ArcGIS (significado a confirmar documentalmente)"
    else: tipo, fonte_tipo = "TIPO_NAO_COMPROVADO", "sem tag 'Extra'; nenhum campo oficial declara 'ordinaria' (BASE so tem DAT_INC/DAT_FNL/DAT_EXT/DESCR)"
    if db_tit != f"{ano}-12-31" or not fnl_ok:
        eleg = "NAO_ELEGIVEL_DATA_BASE"
    elif tipo == "EXTRAORDINARIA_INDICADA":
        eleg = "NAO_ELEGIVEL_AUTOMATICAMENTE_EXTRA" + ("_COM_ALTERNATIVA_SEM_TAG" if any(not extra(a) for a in alternativas) else "_SEM_ALTERNATIVA")
    else:
        eleg = "PENDENTE_COMPROVACAO_TIPO" + ("_INDICIOS_ORDINARIA" if periodo_anual else "_PERIODO_NAO_ANUAL")
    linhas.append(dict(ano_alvo=ano, dist=dist, empresa=emp, item_id=it, url_item=f"https://www.arcgis.com/home/item.html?id={it}", titulo_catalogo=titulo,
                       versao_titulo=(m.group(2) + "_" + m.group(3)) if m else "", tag_extra="sim" if extra(x) else ("nao" if x else "desconhecido"),
                       tags=";".join(x.get("tags") or []), data_base_titulo=db_tit, DAT_INC=di, DAT_FNL=df, DAT_EXT=de, DESCR=ds,
                       DATA_BASE_entidades=";".join(db_ent or []) or "campo_inexistente_no_GDB_original", periodo_anual_01jan_31dez="sim" if periodo_anual else ("nao" if rec else "desconhecido"),
                       fonte_BASE=fonte_base, sha256_fonte=sha or "nao_disponivel", status_inventario=st_inv, uso_atual=uso,
                       tipo_base=tipo, fonte_classificacao_tipo=fonte_tipo,
                       alternativas_mesma_DIST_data=";".join(f"{a['id']}[{'Extra' if extra(a) else 'sem_tag'}]{(RX.search(a['title']) or [None,None,None,''])[3] if RX.search(a['title']) else ''}" for a in alternativas),
                       elegibilidade=eleg))
    print(ano, dist, it[:8], tipo[:12], eleg, flush=True)
with open(A / "CONFORMIDADE_BDGD_ORDINARIA.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, list(linhas[0]), lineterminator="\n"); w.writeheader(); w.writerows(linhas)
c = collections.Counter((l["ano_alvo"], l["uso_atual"], l["tipo_base"]) for l in linhas)
for k in sorted(c): print(k, c[k])
