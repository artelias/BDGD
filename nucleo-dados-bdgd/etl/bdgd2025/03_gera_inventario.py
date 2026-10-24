"""Gera inventario_2025.csv e cobertura_2025.json a partir do catalogo ArcGIS + sonda HEAD.
Grupo economico aqui e apenas CANDIDATO por nome do item; verificacao formal fica para a Tarefa 3."""
import csv, json, re, sys, datetime, pathlib, collections
P = pathlib.Path(sys.argv[1])
raw = json.load(open(P / "arcgis_gdb_raw.json", encoding="utf-8"))
sonda = json.load(open(P / "sonda_download_2025.json", encoding="utf-8"))
rx = re.compile(r"^(?P<emp>.+?)_(?P<dist>\d+)_(?P<db>\d{4}-\d{2}-\d{2})_(?P<ver>[^_]+)_(?P<stamp>\d{8}-\d{4})")
GRUPO = [("Energisa", "Energisa"), ("Equatorial", "Equatorial"), ("CEA_Equatorial", "Equatorial"), ("CEEE_Equatorial", "Equatorial"),
         ("Neoenergia", "Neoenergia"), ("CPFL", "CPFL Energia"), ("RGE", "CPFL Energia"), ("Enel", "Enel"), ("EDP", "EDP"),
         ("Light", "Light"), ("Cemig", "Cemig"), ("Copel", "Copel"), ("Celesc", "Celesc")]
def grupo(emp):
    for p, g in GRUPO:
        if emp.startswith(p): return g
    return "nao_confirmado"
ts = lambda ms: datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc).isoformat(timespec="seconds") if ms and ms > 0 else ""
cols = "dist,sigla,empresa,grupo_economico_candidato,data_base_declarada,data_base_validada,item_id,url_item,url_download,formato,versao,publicado_em,atualizado_em,tamanho_bytes,status,motivo,checksum_sha256".split(",")
hist = collections.defaultdict(list); rows = []; rejeitados = []
for x in raw["itens"]:
    m = rx.match(x["title"])
    if not m:
        rejeitados.append({"item_id": x["id"], "titulo": x["title"], "motivo": "titulo fora do padrao, sem DIST/DATA_BASE"}); continue
    hist[int(m["dist"])].append((m["db"], m["emp"]))
    if m["db"] != "2025-12-31": continue
    s = sonda[x["id"]]
    rows.append({"dist": int(m["dist"]), "sigla": m["emp"], "empresa": m["emp"].replace("_", " "), "grupo_economico_candidato": grupo(m["emp"]),
        "data_base_declarada": m["db"], "data_base_validada": "", "item_id": x["id"],
        "url_item": f"https://www.arcgis.com/home/item.html?id={x['id']}", "url_download": s.get("url_download", ""),
        "formato": "File Geodatabase (.gdb.zip)", "versao": f"{m['ver']}_{m['stamp']}", "publicado_em": ts(x["created"]),
        "atualizado_em": ts(x["modified"]), "tamanho_bytes": s.get("tamanho_bytes", ""),
        "status": "encontrada_download_disponivel" if s.get("http") == 200 else "download_indisponivel",
        "motivo": "DATA_BASE declarada em titulo e tag; pendente validacao no conteudo do GDB", "checksum_sha256": ""})
d25 = {r["dist"] for r in rows}
for dist, h in sorted(hist.items()):
    if dist in d25: continue
    ult = max(h)
    rows.append({"dist": dist, "sigla": ult[1], "empresa": ult[1].replace("_", " "), "grupo_economico_candidato": grupo(ult[1]),
        "data_base_declarada": "", "data_base_validada": "", "item_id": "", "url_item": "", "url_download": "", "formato": "",
        "versao": "", "publicado_em": "", "atualizado_em": "", "tamanho_bytes": "", "status": "sem_publicacao_2025",
        "motivo": f"nenhum GDB 2025-12-31 no catalogo; ultima DATA_BASE publicada {ult[0]} (nao usada como substituta)", "checksum_sha256": ""})
rows.sort(key=lambda r: r["dist"])
with open(P / "inventario_2025.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, cols); w.writeheader(); w.writerows(rows)
enc = [r for r in rows if r["data_base_declarada"] == "2025-12-31"]
cob = {"data_base": "2025-12-31", "gerado_em": datetime.datetime.now().isoformat(timespec="seconds"),
  "metodologia": {"fonte": "ArcGIS Online REST (org ANEEL, owner aneel_aneel) - catalogo dadosabertos-aneel.opendata.arcgis.com",
     "consulta": raw["consulta"], "executada_em": raw["executado_em"], "itens_gdb_varridos_todas_competencias": raw["total_api"],
     "criterio": "DATA_BASE 2025-12-31 no titulo E na tag; download verificado por HTTP HEAD em /sharing/rest/content/items/<id>/data",
     "universo": "toda DIST que ja publicou GDB BDGD no catalogo (2016-2025); lista oficial de agentes nao obtida (CKAN ANEEL inacessivel desta rede)",
     "data_base_validada": "pendente - exige leitura do conteudo de cada GDB (Tarefa 2)"},
  "total_distribuidoras_consideradas": len(rows),
  "encontradas_2025": len(enc),
  "download_disponivel_2025": sum(r["status"] == "encontrada_download_disponivel" for r in enc),
  "volume_total_bytes_2025": sum(int(r["tamanho_bytes"]) for r in enc if r["tamanho_bytes"] != ""),
  "baixadas": 0, "homologadas": 0, "sem_acesso": sum(r["status"] == "download_indisponivel" for r in enc),
  "ausentes_sem_publicacao_2025": [{"dist": r["dist"], "sigla": r["sigla"], "motivo": r["motivo"]} for r in rows if r["status"] == "sem_publicacao_2025"],
  "rejeitadas": rejeitados, "duplicatas_2025": []}
(P / "cobertura_2025.json").write_text(json.dumps(cob, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in cob.items() if not isinstance(v, (list, dict))}, indent=1))
sz = sorted(enc, key=lambda r: -int(r["tamanho_bytes"]))
print("maiores:", [(r["sigla"], round(int(r["tamanho_bytes"]) / 1e9, 2)) for r in sz[:8]])
print("menores:", [(r["sigla"], round(int(r["tamanho_bytes"]) / 1e6, 1)) for r in sz[-5:]])
print(collections.Counter(r["grupo_economico_candidato"] for r in enc))
