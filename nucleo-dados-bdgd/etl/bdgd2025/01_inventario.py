"""Tarefa 1 - inventario completo dos File Geodatabases BDGD do owner aneel_aneel (ArcGIS Online).
Varre todos os anos com paginacao e classifica pela DATA_BASE declarada (tag/titulo)."""
import json, re, sys, time, urllib.parse, urllib.request, datetime, pathlib

OUT = pathlib.Path(sys.argv[1])
BASE = "https://www.arcgis.com/sharing/rest/search"
Q = 'owner:aneel_aneel AND type:"File Geodatabase"'

def get(url):
    for i in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except Exception as e:
            print("retry", i, e); time.sleep(2 ** i)
    raise SystemExit("falha " + url)

items, start = [], 1
while start != -1:
    url = BASE + "?" + urllib.parse.urlencode({"q": Q, "f": "json", "num": 100, "start": start, "sortField": "title"})
    d = get(url)
    items += d["results"]
    print("total", d["total"], "lidos", len(items))
    start = d["nextStart"]
meta = {"consulta": BASE + "?q=" + Q, "executado_em": datetime.datetime.now().isoformat(timespec="seconds"),
        "total_api": d["total"], "itens": items}
(OUT / "arcgis_gdb_raw.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
