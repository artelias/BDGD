"""Tarefa 3 - valida vinculos (entity_links) e referencias DDA do IA Builder contra o Parquet de staging.
Uso: 30_valida_vinculos_dda.py <knowledge_dir> <staging_parquet> <saida_dir>"""
import json, sys, pathlib, duckdb, csv
K, S, O = map(pathlib.Path, sys.argv[1:4])
rel = json.load(open(K / "BDGD_RELATIONSHIPS_AND_DDA_REFS_REV5.json", encoding="utf-8"))
dda = json.load(open(K / "BDGD_DDA_CATALOG_M10.json", encoding="utf-8"))
con = duckdb.connect(); con.execute("SET memory_limit='3GB'; SET preserve_insertion_order=false")
dists = sorted(p.name.split("=")[1] for p in S.glob("DIST=*"))
def path(dist, ent): return S / f"DIST={dist}" / "DATA_BASE=2025-12-31" / f"entidade={ent}" / "part-0.parquet"
def cols(p): return [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM '{p.as_posix()}'").fetchall()]
# DDA como tabela (tabela, cod, descr)
rows = [(t["table"], str(v.get("COD_ID")).strip(), str(v.get("DESCR", ""))) for t in dda["tables"] for v in t["values"]]
con.execute("CREATE TABLE dda(tabela VARCHAR, cod VARCHAR, descr VARCHAR)"); con.executemany("INSERT INTO dda VALUES (?,?,?)", rows)
out_l, out_d, out_u = [], [], []
for dist in dists:
    ents = {p.name.split("=")[1] for p in (S / f"DIST={dist}" / "DATA_BASE=2025-12-31").glob("entidade=*")}
    for e in sorted(ents):  # unicidade de COD_ID
        p = path(dist, e)
        if "COD_ID" in cols(p):
            n, u = con.execute(f"SELECT count(*), count(DISTINCT COD_ID) FROM '{p.as_posix()}'").fetchone()
            out_u.append({"dist": dist, "entidade": e, "linhas": n, "cod_id_distintos": u, "duplicados": n - u})
    for l in rel["entity_links"]:
        se, sf, te, tf = l["source_entity"], l["source_field"], l["target_entity"], l["target_field"]
        r = {"dist": dist, "origem": f"{se}.{sf}", "destino": f"{te}.{tf}"}
        if se not in ents or te not in ents: out_l.append({**r, "status": "entidade_ausente"}); continue
        ps, pt = path(dist, se), path(dist, te)
        if sf not in cols(ps) or tf not in cols(pt): out_l.append({**r, "status": "campo_ausente_no_gdb"}); continue
        q = f"""WITH s AS (SELECT trim(CAST("{sf}" AS VARCHAR)) k FROM '{ps.as_posix()}'),
                t AS (SELECT trim(CAST("{tf}" AS VARCHAR)) k, count(*) c FROM '{pt.as_posix()}' GROUP BY 1)
             SELECT (SELECT count(*) FROM s), (SELECT count(*) FROM s WHERE k IS NOT NULL AND k NOT IN ('','0')),
                    (SELECT count(*) FROM s JOIN t USING(k) WHERE k NOT IN ('','0')),
                    (SELECT coalesce(max(c),0) FROM t)"""
        n, nn, m, mx = con.execute(q).fetchone()
        out_l.append({**r, "status": "validado", "linhas_origem": n, "fk_preenchida": nn, "fk_casada": m,
                      "pct_casamento": round(100 * m / nn, 2) if nn else None,
                      "cardinalidade": "N:1" if mx <= 1 else f"N:N (destino repete ate {mx}x)"})
    for x in rel["dda_references"]:
        se, sf, tb = x["source_entity"], x["source_field"], x["dda_table"]
        r = {"dist": dist, "entidade": se, "atributo": sf, "tabela_dda": tb}
        if se not in ents: out_d.append({**r, "status": "entidade_ausente"}); continue
        p = path(dist, se)
        if sf not in cols(p): out_d.append({**r, "status": "campo_ausente_no_gdb"}); continue
        if not con.execute("SELECT count(*) FROM dda WHERE tabela=?", [tb]).fetchone()[0]:
            out_d.append({**r, "status": "tabela_dda_ausente_no_catalogo"}); continue
        q = f"""SELECT count(*), count(*) FILTER (WHERE d.cod IS NOT NULL), count(DISTINCT s.k),
                  list(DISTINCT s.k) FILTER (WHERE d.cod IS NULL)
                FROM (SELECT trim(CAST("{sf}" AS VARCHAR)) k FROM '{p.as_posix()}') s
                LEFT JOIN (SELECT cod FROM dda WHERE tabela='{tb}') d ON d.cod = s.k"""
        n, m, nd, sem = con.execute(q).fetchone()
        out_d.append({**r, "status": "validado", "linhas": n, "linhas_com_descricao": m, "codigos_distintos": nd,
                      "pct_cobertura": round(100 * m / n, 2) if n else None, "codigos_sem_descricao": "|".join(map(str, (sem or [])[:15]))})
def dump(nome, rs):
    ks = list(dict.fromkeys(k for r in rs for k in r))
    with open(O / nome, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ks); w.writeheader(); w.writerows(rs)
dump("qa_vinculos.csv", out_l); dump("qa_dda_cobertura.csv", out_d); dump("qa_unicidade_cod_id.csv", out_u)
v = [r for r in out_l if r["status"] == "validado"]
print("vinculos validados:", len(v), "| status:", {s: sum(r["status"] == s for r in out_l) for s in {r["status"] for r in out_l}})
print("vinculos <95% casamento:"); [print("  ", r["dist"], r["origem"], "->", r["destino"], r["pct_casamento"], r["cardinalidade"]) for r in v if r["pct_casamento"] is not None and r["pct_casamento"] < 95]
print("vinculos N:N:", sorted({(r["origem"], r["destino"]) for r in v if r["cardinalidade"] != "N:1"}))
dv = [r for r in out_d if r["status"] == "validado"]
print("refs DDA validadas:", len(dv), "| status:", {s: sum(r["status"] == s for r in out_d) for s in {r["status"] for r in out_d}})
print("DDA <99% cobertura:"); [print("  ", r["dist"], r["entidade"], r["atributo"], r["tabela_dda"], r["pct_cobertura"], r["codigos_sem_descricao"]) for r in dv if r["pct_cobertura"] is not None and r["pct_cobertura"] < 99]
print("COD_ID duplicado:", [(r["dist"], r["entidade"], r["duplicados"]) for r in out_u if r["duplicados"]])
