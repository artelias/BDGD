"""Tarefas 4-5: agregados por entidade (total + faceta DDA de 1 dimensao), ARAT simplificada, matriz e comparativos.
Nunca exporta COD_ID nem linhas individuais. Uso: 40_agrega_arat_matriz.py <knowledge> <staging_parquet> <inventario.csv> <saida>"""
import csv, json, sys, pathlib, hashlib, duckdb, numpy as np, shapely, shapely.geometry, pyproj


def transform(fn, g):
    return shapely.transform(g, lambda c: np.column_stack(fn(c[:, 0], c[:, 1])))

K, S, INV, O = map(pathlib.Path, sys.argv[1:5])
O.mkdir(parents=True, exist_ok=True); (O / "geo").mkdir(exist_ok=True)
DB = "2025-12-31"
sch = json.load(open(K / "BDGD_ENTITY_SCHEMA_SEMANTIC_REV5.json", encoding="utf-8"))
rel = json.load(open(K / "BDGD_RELATIONSHIPS_AND_DDA_REFS_REV5.json", encoding="utf-8"))
dda = json.load(open(K / "BDGD_DDA_CATALOG_M10.json", encoding="utf-8"))
inv = {r["dist"]: r for r in csv.DictReader(open(INV, encoding="utf-8"))}
con = duckdb.connect(); con.execute("SET memory_limit='3GB'")
con.execute("CREATE TABLE dda(tabela VARCHAR, cod VARCHAR, descr VARCHAR, pot DOUBLE)")
con.executemany("INSERT INTO dda VALUES (?,?,?,?)",
                [(t["table"], str(v["COD_ID"]).strip(), v.get("DESCR"), v.get("POT")) for t in dda["tables"] for v in t["values"]])
ddatabs = {t["table"] for t in dda["tables"]}
# metadado, poligono, curvas e balancos/perdas: nao sao ativos contaveis
NAO_AGREGAR = {"BASE", "ARAT", "CRVCRG", "BE", "EP", "PT", "PNT"}
# regra de metrica por entidade: (coluna, expressao SQL sobre alias s/p, unidade, regra)
MET = {**{e: ("extensao_km", "sum(TRY_CAST(s.COMP AS DOUBLE))/1000", "km", "soma COMP (m)/1000") for e in ("SSDAT", "SSDBT", "SSDMT", "RAMLIG")},
       "UNTRMT": ("potencia_kva", "sum(TRY_CAST(s.POT_NOM AS DOUBLE))", "kVA", "soma POT_NOM (kVA)"),
       "UNTRAT": ("potencia_kva", "sum(TRY_CAST(s.POT_NOM AS DOUBLE))*1000", "kVA", "soma POT_NOM (MVA)*1000"),
       **{e: ("potencia_kva", "sum(p.pot)", "kVA", "soma TPOTAPRT.POT via codigo POT_NOM") for e in ("EQTRMT", "EQTRAT", "EQRE")},
       **{e: ("potencia_kvar", "sum(p.pot)", "kVAr", "soma TPOTRTV.POT via codigo POT_NOM") for e in ("UNCRAT", "UNCRMT", "UNCRBT")},
}
# UG*.POT_INST suspenso: piloto achou UGBT > 75 kW em massa (DIST 26: 6.807 registros; DIST 69: 80.055 kW) -> regra nao validada
METRICA_SUSPENSA = {e: "POT_INST (kW) suspensa: valores implausiveis em BT no piloto; ver qa_alertas.csv" for e in ("UGAT", "UGMT", "UGBT")}
POTTAB = {**{e: "TPOTAPRT" for e in ("EQTRMT", "EQTRAT", "EQRE")}, **{e: "TPOTRTV" for e in ("UNCRAT", "UNCRMT", "UNCRBT")}}
FAM = {e: g for g, es in sch["semantic_groups"].items() for e in es}
dims = {}
for x in rel["dda_references"]:
    if x["dda_table"] in ddatabs:
        dims.setdefault(x["source_entity"], []).append((x["source_field"], x["dda_table"]))

dists = sorted((p.name.split("=")[1] for p in S.glob("DIST=*")), key=int)
agg, recon, arat_qa, ent_present = [], [], [], {}
for dist in dists:
    root = S / f"DIST={dist}" / f"DATA_BASE={DB}"
    conv = json.load(open(root / "conversao.json", encoding="utf-8"))
    ent_present[dist] = {e: v["linhas"] for e, v in conv["entidades"].items()}
    for ent in sorted(ent_present[dist]):
        if ent in NAO_AGREGAR:
            continue
        p = (root / f"entidade={ent}" / "part-0.parquet").as_posix()
        cols = {r[0] for r in con.execute(f"DESCRIBE SELECT * FROM '{p}'").fetchall()}
        m = MET.get(ent)
        join = ""
        if ent in POTTAB:
            join = f"LEFT JOIN (SELECT cod, pot FROM dda WHERE tabela='{POTTAB[ent]}') p ON p.cod = trim(CAST(s.POT_NOM AS VARCHAR))"
        mexpr = f", {m[1]} AS v" if m else ", NULL AS v"
        n, ndist, v = con.execute(f"SELECT count(*), count(DISTINCT s.COD_ID) {mexpr} FROM '{p}' s {join}").fetchone()
        agg.append({"data_base": DB, "dist": dist, "entidade": ent, "dimensao": "__total__", "codigo": "", "descricao": "Total",
                    "quantidade": n, "quantidade_cod_id_distinto": ndist, "metrica": m[0] if m else "",
                    "valor": round(v, 3) if v is not None else "", "unidade": m[2] if m else ""})
        recon.append({"dist": dist, "entidade": ent, "linhas_gdb": ent_present[dist][ent], "quantidade_agregada": n,
                      "ok": n == ent_present[dist][ent]})
        for campo, tab in dims.get(ent, []):
            if campo not in cols:
                continue
            rs = con.execute(f"""SELECT trim(CAST(s."{campo}" AS VARCHAR)) k, any_value(d.descr), count(*) {mexpr}
                 FROM '{p}' s {join}
                 LEFT JOIN (SELECT cod, descr FROM dda WHERE tabela='{tab}') d ON d.cod = trim(CAST(s."{campo}" AS VARCHAR))
                 GROUP BY 1 ORDER BY 3 DESC""").fetchall()
            assert sum(r[2] for r in rs) == n, (dist, ent, campo)
            for k, desc, q, vv in rs:
                agg.append({"data_base": DB, "dist": dist, "entidade": ent, "dimensao": campo, "codigo": k if k is not None else "",
                            "descricao": desc if desc is not None else "Codigo sem descricao no DDA M10",
                            "quantidade": q, "quantidade_cod_id_distinto": "", "metrica": m[0] if m else "",
                            "valor": round(vv, 3) if vv is not None else "", "unidade": m[2] if m else ""})
    # ARAT oficial do GDB 2025 -> medicao em LAEA local, simplificacao topologica, saida EPSG:4326
    if ent_present[dist].get("ARAT", 0) == 0:
        arat_qa.append({"dist": dist, "status": "ARAT_ausente"})
        continue
    pa = (root / "entidade=ARAT" / "part-0.parquet").as_posix()
    gcol = [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM '{pa}'").fetchall() if r[1] == "BLOB"][0]
    geoms = [shapely.from_wkb(r[0]) for r in con.execute(f'SELECT "{gcol}" FROM read_parquet(\'{pa}\')').fetchall()]
    g = shapely.union_all(geoms); valida0 = bool(g.is_valid); g = shapely.make_valid(g)
    # Lambert Azimutal Equivalente centrada na ARAT: metrica (tolerancia em m) e equivalente (area fiel)
    c = g.centroid
    laea = pyproj.CRS.from_proj4(f"+proj=laea +lat_0={c.y:.4f} +lon_0={c.x:.4f} +ellps=GRS80 +units=m +no_defs")
    to_m = pyproj.Transformer.from_crs(4674, laea, always_xy=True).transform
    to_ll = pyproj.Transformer.from_crs(laea, 4326, always_xy=True).transform
    gm = transform(to_m, g); a0 = gm.area
    tol = 100.0
    gs = shapely.make_valid(gm.simplify(tol, preserve_topology=True)); a1 = gs.area
    gll = shapely.set_precision(transform(to_ll, gs), 1e-5)
    gj = {"type": "FeatureCollection", "name": f"arat_2025_{dist}",
          "features": [{"type": "Feature", "properties": {"dist": int(dist), "data_base": DB, "source_item_id": inv[dist]["item_id"]},
                        "geometry": shapely.geometry.mapping(gll)}]}
    f = O / "geo" / f"arat_2025_{dist}.geojson"
    f.write_text(json.dumps(gj, separators=(",", ":")), encoding="utf-8")
    arat_qa.append({"dist": dist, "status": "ok", "feicoes_origem": len(geoms), "valida_origem": valida0, "crs_origem": "EPSG:4674",
                    "crs_medicao": f"LAEA lat_0={c.y:.4f} lon_0={c.x:.4f} (GRS80)", "crs_saida": "EPSG:4326", "tolerancia_m": tol,
                    "area_km2_origem": round(a0 / 1e6, 2), "area_km2_simplificada": round(a1 / 1e6, 2),
                    "dif_area_pct": round(100 * (a1 - a0) / a0, 4), "partes": len(getattr(gs, "geoms", [gs])),
                    "vertices_origem": int(shapely.get_num_coordinates(g)), "vertices_saida": int(shapely.get_num_coordinates(gll)),
                    "valida_saida": bool(gll.is_valid), "bytes": f.stat().st_size, "sha256": hashlib.sha256(f.read_bytes()).hexdigest()})


def dump(nome, rs):
    ks = list(dict.fromkeys(k for r in rs for k in r))
    with open(O / nome, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, ks); w.writeheader(); w.writerows(rs)


dump("ativos_agregados.csv", agg); dump("qa_reconciliacao.csv", recon); dump("qa_arat.csv", arat_qa)
desig = {e["entity"]: e["designation"] for e in sch["entities"]}
ents = [{"entidade": e, "nome_exibido": desig[e], "familia": FAM.get(e, "OUTROS"),
         "tipo_metrica": "quantidade" + (f"+{MET[e][0]}" if e in MET else ""),
         "unidade": "itens" + (f"; {MET[e][2]}" if e in MET else ""),
         "regra": "count(*) de registros; COD_ID distinto em coluna separada" + (f"; {MET[e][3]}" if e in MET else ""),
         "status": "nao_agregada" if e in NAO_AGREGAR else ("agregada_metrica_suspensa" if e in METRICA_SUSPENSA else "agregada"),
         "observacao": METRICA_SUSPENSA.get(e, "")} for e in sorted(desig)]
dump("entidades.csv", ents)
# matriz: 1 linha por DIST, 1 coluna por entidade; N/D se a camada nao existe no GDB, 0 auditado se existe vazia
tot = {(r["dist"], r["entidade"]): r for r in agg if r["dimensao"] == "__total__"}
cols_e = [e["entidade"] for e in ents if e["status"].startswith("agregada")]
mat = []
for dist in dists:
    row = {"data_base": DB, "dist": dist, "sigla": inv[dist]["sigla"]}
    for e in cols_e:
        row[e] = tot[(dist, e)]["quantidade"] if (dist, e) in tot else "N/D"
    for e in cols_e:
        if e in MET:
            row[f"{e}_{MET[e][0]}"] = tot[(dist, e)]["valor"] if (dist, e) in tot else "N/D"
    mat.append(row)
dump("matriz_empresas_2025.csv", mat)
# comparativo por grupo CANDIDATO (nao verificado); cada DIST em exatamente 1 grupo -> sem dupla contagem
grp = {}
for r in agg:
    if r["dimensao"] != "__total__":
        continue
    g = inv[r["dist"]]["grupo_economico_candidato"]
    x = grp.setdefault((g, r["entidade"]), {"grupo_candidato": g, "status_grupo": "nao_confirmado", "entidade": r["entidade"],
                                            "dists": set(), "quantidade": 0, "valor": 0.0, "metrica": r["metrica"], "unidade": r["unidade"]})
    assert r["dist"] not in x["dists"]
    x["dists"].add(r["dist"]); x["quantidade"] += r["quantidade"]; x["valor"] += r["valor"] or 0
dump("comparativo_grupos_piloto.csv", [{**v, "dists": "|".join(sorted(v["dists"], key=int)), "n_dists": len(v["dists"]),
                                        "valor": round(v["valor"], 3) if v["metrica"] else ""} for v in grp.values()])
print("linhas agregadas:", len(agg), "| reconciliacao ok:", all(r["ok"] for r in recon), len(recon))
for a in arat_qa:
    print("ARAT", a)
