"""Facetas DDA exatas (1 dimensao) + cubos conjuntos curados (2 dimensoes), a partir do staging Parquet.
Somas de extensao/potencia em DECIMAL(38,6) para que categorias reconciliem exatamente com o total-base.
Checkpoint por DIST em proc/DIST=*/facetas_v2.csv + totais_v2.json. Uso: 75_facetas_exatas.py [--dists 26,31] [--forcar]"""
import argparse, csv, json, pathlib, sys, time
from decimal import Decimal
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import bdgd_etl as E
import duckdb

DB, R = E.DB, E.R
PROC, PQ = R / "proc", R / "staging_parquet"
SEM = "SEM_CODIGO"
JOINT = {
    "UCBT": [("ARE_LOC", "CLAS_SUB"), ("ARE_LOC", "FAS_CON"), ("CLAS_SUB", "SIT_ATIV"), ("ARE_LOC", "GRU_TAR")],
    "UCMT": [("ARE_LOC", "CLAS_SUB"), ("ARE_LOC", "GRU_TAR")],
    "UCAT": [("ARE_LOC", "CLAS_SUB")],
    "SSDMT": [("ARE_LOC", "FAS_CON"), ("ARE_LOC", "TIP_INST")],
    "SSDBT": [("ARE_LOC", "FAS_CON"), ("ARE_LOC", "TIP_INST")],
    "SSDAT": [("FAS_CON", "TIP_INST")],
    "RAMLIG": [("ARE_LOC", "FAS_CON")],
    "UNTRMT": [("ARE_LOC", "TIP_TRAFO"), ("ARE_LOC", "POSTO")],
    "EQTRMT": [("CLAS_TEN", "FAS_CON")],
    "UGBT": [("FAS_CON", "SIT_ATIV")],
    "PIP": [("ARE_LOC", "FAS_CON")],
    "PONNOT": [("ARE_LOC", "ESTR"), ("ESTR", "MAT")],
    "UNSEMT": [("ARE_LOC", "TIP_UNID")],
}


def k(col): return f"coalesce(nullif(trim(CAST(s.\"{col}\" AS VARCHAR)), ''), '{SEM}')"


def processa(d, K, con):
    base = PQ / f"DIST={d}" / f"DATA_BASE={DB}"
    conv = json.loads((base / "conversao.json").read_text(encoding="utf-8"))
    out, totais = [], {}
    con.execute("CREATE OR REPLACE TEMP TABLE pot AS SELECT * FROM (VALUES ('x','x',0.0::DOUBLE)) t(tab,cod,pot) WHERE false")
    con.executemany("INSERT INTO pot VALUES (?,?,?)", [(t, c, v[1]) for t, m in K.dda.items() if t == "TPOTAPRT" for c, v in m.items()])
    for e in sorted(conv["entidades"]):
        if e in E.NAO_ENTIDADE or not conv["entidades"][e]["linhas"]: continue
        p = (base / f"entidade={e}" / "part-0.parquet").as_posix()
        cols = {r[0] for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{p}')").fetchall()}
        join, sel = "", ["count(*)"]
        sel.append("count(DISTINCT s.COD_ID)" if (e in E.UC and "COD_ID" in cols) else "NULL")
        sel.append("sum(CAST(s.COMP AS DECIMAL(38,6)))" if (e in E.EXT and "COMP" in cols) else "NULL")
        if e in E.POTCOD and "POT_NOM" in cols:
            join = "LEFT JOIN pot m ON m.tab='TPOTAPRT' AND m.cod = trim(CAST(s.POT_NOM AS VARCHAR))"; sel.append("sum(CAST(m.pot AS DECIMAL(38,6)))")
        elif e == "UNTRMT" and "POT_NOM" in cols: sel.append("sum(CAST(s.POT_NOM AS DECIMAL(38,6)))")
        elif e == "UNTRAT" and "POT_NOM" in cols: sel.append("sum(CAST(s.POT_NOM AS DECIMAL(38,6)) * 1000)")
        else: sel.append("NULL")
        n, nd, ext_m, pot = con.execute(f"SELECT {', '.join(sel)} FROM read_parquet('{p}') s {join}").fetchone()
        totais[e] = {"n": n, "nd": nd, "extensao_km": str(Decimal(ext_m) / 1000) if ext_m is not None else None, "potencia_kva": str(pot) if pot is not None else None}
        grupos = [(f,) for f, _ in K.dims.get(e, []) if f in cols] + [g for g in JOINT.get(e, []) if all(f in cols for f in g)]
        for g in grupos:
            keys = ", ".join(k(f) for f in g)
            card = con.execute(f"SELECT count(*) FROM (SELECT DISTINCT {keys} FROM read_parquet('{p}') s)").fetchone()[0]
            if card > E.MAX_CARD_FACETA: continue
            rs = con.execute(f"SELECT {keys}, {', '.join(sel)} FROM read_parquet('{p}') s {join} GROUP BY ALL").fetchall()
            assert sum(r[len(g)] for r in rs) == n, (d, e, g)
            for r in rs:
                codes, (cn, cnd, cext, cpot) = r[:len(g)], r[len(g):]
                out.append({"entidade": e, "facet_id": f"{e}.{'+'.join(sorted(g))}", "dimensoes_json": json.dumps(dict(sorted(zip(g, codes))), ensure_ascii=False),
                            "n": cn, "nd": "" if cnd is None else cnd, "extensao_km": "" if cext is None else str(Decimal(cext) / 1000),
                            "potencia_kva": "" if cpot is None else str(cpot)})
    return out, totais


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dists", default=""); ap.add_argument("--forcar", action="store_true"); a = ap.parse_args()
    K = E.Conhecimento()
    ds = sorted((p.parent.name.split("=")[1] for p in PROC.glob("DIST=*/_OK")), key=int)
    if a.dists: ds = [d for d in ds if d in a.dists.split(",")]
    con = duckdb.connect(); con.execute(f"SET threads=2; SET memory_limit='2GB'; SET temp_directory='{(R / 'tmp_duckdb').as_posix()}'")
    for d in ds:
        dst = PROC / f"DIST={d}" / "facetas_v2.csv"
        if dst.exists() and not a.forcar: continue
        t0 = time.time(); out, tot = processa(d, K, con)
        tmp = dst.with_suffix(".tmp")
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, ["entidade", "facet_id", "dimensoes_json", "n", "nd", "extensao_km", "potencia_kva"], lineterminator="\n"); w.writeheader(); w.writerows(out)
        (PROC / f"DIST={d}" / "totais_v2.json").write_text(json.dumps(tot, indent=1), encoding="utf-8")
        tmp.replace(dst)
        print(f"{E.now()} DIST {d}: {len(out)} linhas de faceta ({time.time() - t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
