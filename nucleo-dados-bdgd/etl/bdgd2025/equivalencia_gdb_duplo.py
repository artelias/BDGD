"""Equivalencia integral entre dois GDBs publicados no MESMO ZIP (caso 2022/6072 Equatorial GO: Enel_GO_* e Equatorial_GO_*).
Leitura em lotes direto do ZIP (pyogrio/GDAL, sem DuckDB, memoria baixa). Por camada: esquema (nome, tipo), contagem e
impressao (n, soma mod 2^64, xor) de blake2b-64 sobre todos os atributos (exceto OBJECTID) + WKB da geometria.
Equivalente apenas se TODAS as camadas coincidirem; qualquer diferenca -> decisao humana. Somente leitura.
Uso: equivalencia_gdb_duplo.py <zip> <saida.json>"""
import hashlib, json, pathlib, sys, time, zipfile
import pyogrio
from pyogrio import raw as pr

M64 = 2 ** 64


def impressao(src, layer):
    n = s = x = 0
    with pr.open_arrow(src, layer=layer, batch_size=20000, use_pyarrow=True) as (meta, rdr):
        campos = [f for f in meta["fields"] if f.upper() != "OBJECTID"]
        gname = meta.get("geometry_name") or "wkb_geometry"
        esquema = list(zip(meta["fields"].tolist(), meta["dtypes"].tolist()))
        for b in rdr:
            cols = [b.column(b.schema.get_field_index(c)).to_pylist() for c in campos if c in b.schema.names]
            g = b.column(b.schema.get_field_index(gname)).to_pylist() if gname in b.schema.names else [None] * b.num_rows
            for i in range(b.num_rows):
                h = hashlib.blake2b(digest_size=8)
                for c in cols: h.update(repr(c[i]).encode("utf-8", "surrogatepass")); h.update(b"\x1f")
                h.update(g[i] or b"")
                v = int.from_bytes(h.digest(), "little"); n += 1; s = (s + v) % M64; x ^= v
    return {"esquema": [e for e in esquema if e[0].upper() != "OBJECTID"], "geometria": meta.get("geometry_type"), "n": n, "soma": str(s), "xor": str(x)}


def main():
    zp, saida = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    gdbs = sorted({n[:n.lower().index(".gdb") + 4] for n in zipfile.ZipFile(zp).namelist() if ".gdb" in n.lower()})
    res = {"zip": zp.name, "gdbs": gdbs, "camadas": {}, "diferencas": []}
    srcs = {g: f"/vsizip/{zp.as_posix()}/{g}" for g in gdbs}
    camadas = {g: {l[0]: l[1] for l in pyogrio.list_layers(srcs[g])} for g in gdbs}
    todas = sorted(set().union(*[set(c) for c in camadas.values()]))
    for lay in todas:
        t0 = time.time(); r = {}
        for g in gdbs:
            if lay not in camadas[g]: r[g] = None; continue
            try: r[g] = impressao(srcs[g], lay)
            except Exception as e: r[g] = {"erro": str(e)}
        res["camadas"][lay] = r
        if len({json.dumps(v, sort_keys=True) for v in r.values()}) > 1: res["diferencas"].append(lay)
        print(f"{lay}: {'DIFERENTE' if lay in res['diferencas'] else 'igual'} n={[v.get('n') if v else None for v in r.values()]} {time.time() - t0:.0f}s", flush=True)
    res["equivalente"] = not res["diferencas"]
    res["criterio"] = "todas as camadas com esquema, contagem, atributos e geometria identicos" if res["equivalente"] else "nao comprovado: decisao humana"
    saida.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("EQUIVALENTE" if res["equivalente"] else f"DIVERGENTE em {len(res['diferencas'])} camada(s): {res['diferencas']}", flush=True)


if __name__ == "__main__":
    main()
