"""Sonda HEAD em /data de cada item 2025-12-31: tamanho real, nome do arquivo, ranges."""
import json, re, sys, time, urllib.request, concurrent.futures as cf, pathlib
P = pathlib.Path(sys.argv[1])
d = json.load(open(P / "arcgis_gdb_raw.json", encoding="utf-8"))
items = [x for x in d["itens"] if "_2025-12-31_" in x["title"]]
def head(x):
    url = f"https://www.arcgis.com/sharing/rest/content/items/{x['id']}/data"
    for i in range(3):
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=60) as r:
                h = r.headers
                return x["id"], {"http": r.status, "url_download": r.geturl(), "tamanho_bytes": int(h.get("Content-Length") or -1),
                        "content_type": h.get("Content-Type"), "ranges": h.get("Accept-Ranges"),
                        "filename": re.search(r'filename="([^"]+)"', h.get("Content-Disposition") or "") and re.search(r'filename="([^"]+)"', h.get("Content-Disposition")).group(1)}
        except Exception as e:
            err = repr(e); time.sleep(2 ** i)
    return x["id"], {"http": None, "erro": err}
with cf.ThreadPoolExecutor(4) as ex:
    res = dict(ex.map(head, items))
(P / "sonda_download_2025.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
ok = [v for v in res.values() if v.get("http") == 200]
print("ok", len(ok), "falhas", len(res) - len(ok), "total GB", round(sum(v["tamanho_bytes"] for v in ok) / 1e9, 2))
