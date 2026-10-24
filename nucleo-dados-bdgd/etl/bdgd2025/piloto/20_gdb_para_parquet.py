"""GDB -> Parquet de STAGING LOCAL (nunca publicar). Streaming em lotes; particao DIST/DATA_BASE/entidade.
Uso: 20_gdb_para_parquet.py <dir_raw DIST=..> <dir_parquet>"""
import json, sys, pathlib, time, pyogrio, pyarrow.parquet as pq
d, outroot = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
ins = json.load(open(d / "inspecao.json", encoding="utf-8"))
base = ins["BASE"][0]
assert base["DAT_FNL"] == "31/12/2025", f"DATA_BASE invalida {base}"
dist = ins["dist_inventario"]; log = {}
for nome, c in ins["camadas"].items():
    ent = nome.removesuffix("_tab")
    dest = outroot / f"DIST={dist}" / "DATA_BASE=2025-12-31" / f"entidade={ent}" / "part-0.parquet"
    if (dest.parent / "_OK").exists(): log[ent] = json.loads((dest.parent / "_OK").read_text()); continue
    dest.parent.mkdir(parents=True, exist_ok=True); t0 = time.time(); n = 0; w = None
    with pyogrio.open_arrow(ins["src"], layer=nome, batch_size=100_000, use_pyarrow=True) as (meta, reader):
        for b in reader:
            if w is None: w = pq.ParquetWriter(dest, b.schema, compression="zstd")
            w.write_batch(b); n += b.num_rows
        if w is None: w = pq.ParquetWriter(dest, reader.schema, compression="zstd")
    w.close()
    assert n == c["n"], f"{ent}: {n} != {c['n']}"
    rec = {"linhas": n, "linhas_gdb": c["n"], "crs": c["crs"], "seg": round(time.time() - t0, 1)}
    (dest.parent / "_OK").write_text(json.dumps(rec)); log[ent] = rec
(outroot / f"DIST={dist}" / "DATA_BASE=2025-12-31" / "conversao.json").write_text(json.dumps(
    {"dist": dist, "item_id": ins["item_id"], "sha256_zip": ins["sha256"], "BASE": base, "entidades": log}, indent=1, default=str))
print(dist, "entidades:", len(log), "linhas:", sum(v["linhas"] for v in log.values()))
