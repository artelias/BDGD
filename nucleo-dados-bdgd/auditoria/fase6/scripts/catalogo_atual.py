"""Fase 6 — consulta atual do catalogo oficial ANEEL/ArcGIS (somente metadados; nenhum arquivo baixado).
Mesma consulta do inventario historico: owner:aneel_aneel AND type:"File Geodatabase". Paginacao completa."""
import json, pathlib, time, urllib.parse, urllib.request, datetime as dt
OUT = pathlib.Path("D:/NUCLEO_BDGD_2025/auditoria-fase6/evidencias")
q = 'owner:aneel_aneel AND type:"File Geodatabase"'
itens, start = [], 1
while start > 0:
    url = "https://www.arcgis.com/sharing/rest/search?" + urllib.parse.urlencode({"q": q, "num": 100, "start": start, "f": "json", "sortField": "title"})
    with urllib.request.urlopen(url, timeout=60) as r: j = json.loads(r.read().decode("utf-8"))
    itens += j.get("results", []); start = j.get("nextStart", -1); time.sleep(0.3)
doc = {"consulta": q, "obtido_em": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "total": len(itens), "items": itens}
(OUT / "catalogo_arcgis_atual.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
print(len(itens), "itens")
