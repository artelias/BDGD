"""Inspeciona um GDB zipado (equivalente ogrinfo -so): camadas, contagem, geometria, EPSG, campos,
conteudo da entidade BASE e distribuicao de DIST. Uso: 11_inspeciona_gdb.py <dir DIST=...>"""
import json, sys, pathlib, zipfile, pyogrio
d = pathlib.Path(sys.argv[1])
dl = json.load(open(d / "download.json", encoding="utf-8"))
z = zipfile.ZipFile(dl["arquivo"])
gdbdir = sorted({n.split("/")[0] for n in z.namelist() if ".gdb" in n.split("/")[0]})
src = f"/vsizip/{pathlib.Path(dl['arquivo']).as_posix()}/{gdbdir[0]}"
out = {"dist_inventario": dl["dist"], "item_id": dl["item_id"], "sha256": dl["sha256"], "gdb": gdbdir, "camadas": {}}
for nome, geom in pyogrio.list_layers(src):
    info = pyogrio.read_info(src, layer=nome, force_feature_count=True)
    c = {"geometria": geom, "n": int(info["features"]), "crs": info["crs"], "campos": list(info["fields"])}
    if "DIST" in c["campos"] and c["n"]:
        _, t = pyogrio.read_arrow(src, layer=nome, columns=["DIST"], read_geometry=False)
        c["dist_valores"] = {str(r["values"]): int(r["counts"]) for r in t.column("DIST").value_counts().to_pylist()}
    out["camadas"][nome] = c
out["BASE"] = pyogrio.read_arrow(src, layer="BASE", read_geometry=False)[1].to_pylist() if "BASE" in out["camadas"] else None
out["src"] = src
(d / "inspecao.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print(dl["dist"], gdbdir, "camadas:", len(out["camadas"]), "BASE:", out["BASE"])
for k, c in out["camadas"].items():
    print(f"  {k:8} {str(c['geometria']):18} {c['n']:>9} {str(c['crs'])[:12]:12} DIST={c.get('dist_valores')}")
