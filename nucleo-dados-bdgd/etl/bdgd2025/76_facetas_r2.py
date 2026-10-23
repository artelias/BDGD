"""R2 — dimensoes adicionais com base em campos reais do GDB 2025 (sem juncao espacial):
  * MUN (codigo IBGE do municipio) nas entidades que possuem o campo: consumidores, geradores, unidades UN*, PIP, PONNOT;
  * TUC e A1xTUC (classificacao patrimonial MCPSE) nos equipamentos EQ*, BAR e PONNOT;
  * unidades fisicas distintas vinculadas por TUC (EQ -> UN, deduplicado pela chave de vinculo, orfaos contados).
Somas de potencia em DECIMAL(38,6). Checkpoint por DIST: proc/DIST=*/facetas_r2.csv + vinculos_tuc.json.
Uso: 76_facetas_r2.py [--dists 26,31] [--forcar]"""
import argparse, csv, json, os, pathlib, sys, time
from decimal import Decimal
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import bdgd_etl as E
import duckdb

DB, R = E.DB, E.R
PROC, PQ = R / "proc", R / "staging_parquet"
SEM = "SEM_CODIGO"
MUN_ENTS = ["UCBT", "UCMT", "UCAT", "UGBT", "UGMT", "UGAT", "UNTRMT", "UNTRAT", "UNSEBT", "UNSEMT", "UNSEAT",
            "UNREMT", "UNREAT", "UNCRBT", "UNCRMT", "UNCRAT", "PIP", "PONNOT"]
TUC_ENTS = ["EQTRMT", "EQTRAT", "EQSE", "EQRE", "EQCR", "EQME", "EQTRM", "BAR", "PONNOT"]
# vinculo equipamento -> instalacao (Manual Rev. 5, campos do tipo Vinculado)
LINKS = {"EQTRMT": ("UNI_TR_MT", ["UNTRMT"]), "EQTRAT": ("UNI_TR_AT", ["UNTRAT"]), "EQSE": ("UN_SE", ["UNSEAT", "UNSEMT", "UNSEBT"]),
         "EQRE": ("UN_RE", ["UNREAT", "UNREMT"]), "EQCR": ("UN_CR", ["UNCRAT", "UNCRMT", "UNCRBT"])}
MAX_CARD = 1200   # municipios por DIST (Cemig ~ 774)


def k(col): return f"coalesce(nullif(trim(CAST(s.\"{col}\" AS VARCHAR)), ''), '{SEM}')"


def processa(d, K, con):
    base = PQ / f"DIST={d}" / f"DATA_BASE={DB}"
    conv = json.loads((base / "conversao.json").read_text(encoding="utf-8"))
    pth = lambda e: (base / f"entidade={e}" / "part-0.parquet").as_posix()
    present = {e for e, v in conv["entidades"].items() if v["linhas"]}
    cols = lambda e: {r[0] for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{pth(e)}')").fetchall()}
    out, vinc = [], {}

    def sel_for(e, cs):
        join, sel = "", ["count(*)"]
        sel.append("count(DISTINCT s.COD_ID)" if (e in E.UC and "COD_ID" in cs) else "NULL")
        if e in E.POTCOD and "POT_NOM" in cs:
            join = "LEFT JOIN pot m ON m.cod = trim(CAST(s.POT_NOM AS VARCHAR))"; sel.append("sum(CAST(m.pot AS DECIMAL(38,6)))")
        elif e == "UNTRMT" and "POT_NOM" in cs: sel.append("sum(CAST(s.POT_NOM AS DECIMAL(38,6)))")
        elif e == "UNTRAT" and "POT_NOM" in cs: sel.append("sum(CAST(s.POT_NOM AS DECIMAL(38,6)) * 1000)")
        else: sel.append("NULL")
        return join, sel

    def cubo(e, dims):
        cs = cols(e)
        if not all(f in cs for f in dims): return
        keys = ", ".join(k(f) for f in dims)
        if con.execute(f"SELECT count(*) FROM (SELECT DISTINCT {keys} FROM read_parquet('{pth(e)}') s)").fetchone()[0] > MAX_CARD: return
        join, sel = sel_for(e, cs)
        n_tot = conv["entidades"][e]["linhas"]
        rs = con.execute(f"SELECT {keys}, {', '.join(sel)} FROM read_parquet('{pth(e)}') s {join} GROUP BY ALL").fetchall()
        assert sum(r[len(dims)] for r in rs) == n_tot, (d, e, dims)
        for r in rs:
            codes, (cn, cnd, cpot) = r[:len(dims)], r[len(dims):]
            out.append({"entidade": e, "facet_id": f"{e}.{'+'.join(sorted(dims))}", "dimensoes_json": json.dumps(dict(sorted(zip(dims, codes))), ensure_ascii=False),
                        "n": cn, "nd": "" if cnd is None else cnd, "extensao_km": "", "potencia_kva": "" if cpot is None else str(cpot)})

    con.execute("CREATE OR REPLACE TEMP TABLE pot AS SELECT * FROM (VALUES ('x', 0.0::DOUBLE)) t(cod, pot) WHERE false")
    con.executemany("INSERT INTO pot VALUES (?,?)", [(c, v[1]) for c, v in K.dda["TPOTAPRT"].items()])
    for e in MUN_ENTS:
        if e in present: cubo(e, ["MUN"])
    for e in TUC_ENTS:
        if e in present:
            cubo(e, ["TUC"])
            cubo(e, ["A1", "TUC"])
    for e, (fk, alvos) in LINKS.items():
        if e not in present or fk not in cols(e) or "TUC" not in cols(e): continue
        tg = [t for t in alvos if t in present]
        tgt = " UNION ".join(f"SELECT trim(CAST(COD_ID AS VARCHAR)) k FROM read_parquet('{pth(t)}')" for t in tg) if tg else "SELECT NULL::VARCHAR k WHERE false"
        rs = con.execute(f"""WITH t AS ({tgt}), s AS (SELECT {k('TUC')} tuc, nullif(trim(CAST(s.{fk} AS VARCHAR)), '') f FROM read_parquet('{pth(e)}') s)
            SELECT tuc, count(*), count(*) FILTER (WHERE f IS NOT NULL AND f <> '0'),
                   count(*) FILTER (WHERE f IN (SELECT k FROM t)), count(DISTINCT f) FILTER (WHERE f IN (SELECT k FROM t))
            FROM s GROUP BY 1""").fetchall()
        vinc[e] = {"campo_vinculo": fk, "destinos": tg, "por_tuc": {r[0]: {"equipamentos": r[1], "com_vinculo": r[2], "vinculados": r[3], "unidades_distintas": r[4]} for r in rs}}
    return out, vinc


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dists", default=""); ap.add_argument("--forcar", action="store_true"); a = ap.parse_args()
    K = E.Conhecimento()
    ds = sorted((p.parent.name.split("=")[1] for p in PROC.glob("DIST=*/_OK")), key=int)
    if a.dists: ds = [d for d in ds if d in a.dists.split(",")]
    th, mem = os.environ.get("BDGD_DUCKDB_THREADS", "2"), os.environ.get("BDGD_DUCKDB_MEM", "2GB")
    con = duckdb.connect(); con.execute(f"SET threads={th}; SET memory_limit='{mem}'; SET temp_directory='{(R / 'tmp_duckdb').as_posix()}'")
    for d in ds:
        dst = PROC / f"DIST={d}" / "facetas_r2.csv"
        if dst.exists() and not a.forcar: continue
        t0 = time.time(); out, vinc = processa(d, K, con)
        tmp = dst.with_suffix(".tmp")
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, ["entidade", "facet_id", "dimensoes_json", "n", "nd", "extensao_km", "potencia_kva"], lineterminator="\n"); w.writeheader(); w.writerows(out)
        (PROC / f"DIST={d}" / "vinculos_tuc.json").write_text(json.dumps(vinc, indent=1, ensure_ascii=False), encoding="utf-8")
        tmp.replace(dst)
        print(f"{E.now()} DIST {d}: {len(out)} linhas R2, vinculos {list(vinc)} ({time.time() - t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
