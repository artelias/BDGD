"""Gera os assets estaticos da aplicacao web a partir do pacote publico validado (output-publicavel/2025-12-31).
Somente agregados ja presentes no pacote; nenhum acesso ao staging. Saida: <web>/public/data/2025-12-31/.
Uso: 85_assets_web.py <pacote> <web_public_data> <natural_earth_dir>"""
import csv, json, pathlib, shutil, sys, hashlib
import numpy as np, pyproj, shapely, shapely.geometry

PKG, OUT, NE = map(pathlib.Path, sys.argv[1:4])
DB = "2025-12-31"
OUT = OUT / DB
shutil.rmtree(OUT, ignore_errors=True); (OUT / "facetas").mkdir(parents=True); (OUT / "geo" / "arat").mkdir(parents=True)
rd = lambda n: list(csv.DictReader(open(PKG / n, encoding="utf-8")))
num = lambda v: None if v in ("", None) else (int(v) if v.lstrip("-").isdigit() else float(v))
ST = {"aprovado": "a", "alerta": "l", "bloqueado": "b", "em_validacao": "e", "nao_aplicavel": "n"}
def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return path.stat().st_size

man = json.load(open(PKG / "manifest.json", encoding="utf-8"))
dists = rd("distribuidoras.csv"); grupos = rd("grupos_economicos.csv"); ents = rd("entidades.csv")
fatos = rd("ativos_agregados.csv"); comp = rd("indicadores_complementares.csv"); cob = rd("cobertura_distribuidoras.csv")
alert = rd("qa_alertas.csv"); filtros = rd("disponibilidade_filtros.csv"); homol = rd("metricas_homologacao.csv")
araq = {r["dist"]: r for r in rd("qa_arat.csv")}; ucv2 = rd("qa_uc_regra_v2.csv")

# --- UF aproximada por intersecao de area (Natural Earth 1:50m, dominio publico)
ufs_ne = [f for f in json.load(open(NE / "ne_50m_admin_1_states_provinces.geojson", encoding="utf-8"))["features"] if f["properties"].get("adm0_a3") == "BRA"]
uf_geom = [(f["properties"]["postal"], shapely.geometry.shape(f["geometry"]).buffer(0)) for f in ufs_ne]
eq = pyproj.Transformer.from_crs(4326, 5880, always_xy=True).transform   # so para razao de areas (mesma projecao dos dois lados)
tf = lambda fn, g: shapely.transform(g, lambda a: np.column_stack(fn(a[:, 0], a[:, 1])))
uf_m = [(u, tf(eq, g)) for u, g in uf_geom]

gcolor = {g["grupo_id"]: g["nome"] for g in grupos}
feats, arat_idx = [], {}
for d in dists:
    p = PKG / "geo" / f"arat_2025_{d['dist']}.geojson"
    if not p.exists(): continue
    gj = json.load(open(p, encoding="utf-8"))
    g = shapely.geometry.shape(gj["features"][0]["geometry"])
    shutil.copyfile(p, OUT / "geo" / "arat" / f"{d['dist']}.json")
    gm = tf(eq, g); a = gm.area or 1
    shares = sorted(((u, gm.intersection(um).area / a) for u, um in uf_m if gm.intersects(um)), key=lambda x: -x[1])
    d["ufs"] = [u for u, s in shares if s >= 0.02] or ([shares[0][0]] if shares else [])
    # versao de visualizacao nacional: simplificacao adicional (~0,008 grau ~ 900 m) preservando topologia
    lo = shapely.make_valid(g.simplify(0.008, preserve_topology=True))
    if lo.geom_type not in ("Polygon", "MultiPolygon"):
        lo = shapely.union_all([x for x in getattr(lo, "geoms", []) if x.geom_type in ("Polygon", "MultiPolygon")])
    lo = shapely.set_precision(lo, 1e-4)
    b = g.bounds
    feats.append({"type": "Feature", "properties": {"d": int(d["dist"]), "g": d["grupo_economico"], "a": float(d["arat_area_km2"] or 0)},
                  "geometry": shapely.geometry.mapping(lo), "_area": float(d["arat_area_km2"] or 0)})
    arat_idx[d["dist"]] = {"bbox": [round(x, 4) for x in b], "centro": [round(g.representative_point().x, 4), round(g.representative_point().y, 4)]}
feats.sort(key=lambda f: -f.pop("_area"))   # maiores primeiro: permissionarias internas ficam visiveis por cima
size_br = dump(OUT / "geo" / "brasil.json", {"type": "FeatureCollection", "features": feats})
# contexto: UFs (linhas) e paises vizinhos
dump(OUT / "geo" / "ufs.json", {"type": "FeatureCollection", "features": [
    {"type": "Feature", "properties": {"uf": u}, "geometry": shapely.geometry.mapping(shapely.set_precision(g.simplify(0.02, preserve_topology=True), 1e-3))} for u, g in uf_geom]})
paises = json.load(open(NE / "ne_50m_admin_0_countries.geojson", encoding="utf-8"))["features"]
sa = [f for f in paises if f["properties"].get("CONTINENT") == "South America" or f["properties"].get("ADM0_A3") in ("BRA",)]
dump(OUT / "geo" / "paises.json", {"type": "FeatureCollection", "features": [
    {"type": "Feature", "properties": {"n": f["properties"].get("NAME_PT") or f["properties"].get("NAME"), "br": f["properties"].get("ADM0_A3") == "BRA"},
     "geometry": shapely.geometry.mapping(shapely.set_precision(shapely.geometry.shape(f["geometry"]).simplify(0.03, preserve_topology=True), 1e-3))} for f in sa]})

# --- indice principal
alcount = {}
for a in alert:
    alcount.setdefault(a["dist"], {}); alcount[a["dist"]][a["tipo"]] = alcount[a["dist"]].get(a["tipo"], 0) + 1
compl = {}
for c in comp:
    compl.setdefault(c["indicador"], {}).setdefault(c["dist"], {})[c["entidade"]] = [num(c["valor"]), ST.get(c["status"], c["status"]), c["motivo"]]
index = {
    "release": {k: man[k] for k in ("schema_version", "release_id", "data_base", "status", "generated_at", "dda_version", "quality", "cobertura", "regras", "licenca", "autoria", "privacidade")},
    "distribuidoras": [{"dist": int(d["dist"]), "sigla": d["sigla"], "nome": d["nome"], "grupo": d["grupo_economico"], "grupo_status": d["grupo_status"],
                        "area_km2": num(d["arat_area_km2"]), "ufs": d.get("ufs", []), "fonte": d["fonte_url"], "sha256": d["sha256"], "versao": d["versao_arquivo"],
                        "alertas": alcount.get(d["dist"], {}), "arat": arat_idx.get(d["dist"])} for d in dists],
    "grupos": [{"id": g["grupo_id"], "nome": g["nome"], "controlador": g["controlador_final"], "fontes": g["fonte_url"].split(" | "),
                "tipo_fonte": g["tipo_fonte"], "consultado_em": g["consultado_em"], "observacao": g["observacao"]} for g in grupos],
    "entidades": [{"id": e["entidade"], "nome": e["nome_exibicao"], "familia": e["familia"], "metrica": e["metrica"], "unidade": e["unidade"],
                   "regra": e["regra"], "ativo": e["ativo_fisico"] == "sim", "naoSomarCom": e["nao_somar_com"] or None} for e in ents],
    "fatos": {"cols": ["dist", "entidade", "quantidade", "quantidade_registros", "quantidade_cod_id_distinto", "extensao_km", "potencia_kva", "status", "motivo"],
              "rows": [[int(f["dist"]), f["entidade"], num(f["quantidade"]), num(f["quantidade_registros"]), num(f["quantidade_cod_id_distinto"]),
                        num(f["extensao_km"]), num(f["potencia_kva"]), ST[f["status_qualidade"]], f["motivo_qualidade"]] for f in fatos]},
    "complementares": compl,
    "cobertura": [{"dist": int(c["dist"]), "sigla": c["sigla"], "empresa": c["empresa"], "status": c["status_2025"], "motivo": c["motivo"]} for c in cob],
    "filtrosIndisponiveis": [{"dist": int(f["dist"]), "entidade": f["entidade"], "filtro": f["filtro"], "pct": num(f["pct_orfaos"]), "motivo": f["motivo"]} for f in filtros],
    "homologacao": [{"entidade": h["entidade"], "metrica": h["metrica"], "status": h["status_homologacao"], "comValor": int(h["dists_com_valor"]),
                     "nd": int(h["dists_nd"]), "alerta": int(h["dists_alerta"]), "recOk": int(h["reconciliacoes_ok"]), "criterio": h["criterio"]} for h in homol],
}
s_idx = dump(OUT / "index.json", index)

# --- qualidade (pagina de metodologia)
qa = {"alertasPorTipo": {}, "arat": [{"dist": int(k), **{c: num(v) if c not in ("status", "crs_origem", "crs_publicacao", "crs_medicao", "tipo_saida", "sha256", "valida_origem", "valida_saida") else v
                                                         for c, v in r.items() if c != "dist"}} for k, r in araq.items()],
      "ucRegraV2": [{"dist": int(u["dist"]), "entidade": u["entidade"], "registros": int(u["registros"]), "distintos": int(u["cod_id_distinto"]),
                     "ativados": int(u["cod_id_ativados"]), "valida": u["valida"] == "True", "motivos": u["motivos"]} for u in ucv2],
      "alertas": [{"dist": int(a["dist"]), "entidade": a["entidade"], "tipo": a["tipo"], "detalhe": a["detalhe"]} for a in alert],
      "reconciliacao": {}}
for a in alert: qa["alertasPorTipo"][a["tipo"]] = qa["alertasPorTipo"].get(a["tipo"], 0) + 1
for r in rd("qa_reconciliacao.csv"): qa["reconciliacao"][r["status"]] = qa["reconciliacao"].get(r["status"], 0) + 1
dump(OUT / "qualidade.json", qa)

# --- facetas por entidade (compacto)
import re
import os
SCH = json.load(open(pathlib.Path(os.environ.get("BDGD_KNOWLEDGE", "C:/GEOIA/GEOIA_DATA_HUB/knowledge")) / "BDGD_ENTITY_SCHEMA_SEMANTIC_REV5.json", encoding="utf-8"))
campo_desc = {(e["entity"], f["name"]): f["description"] for e in SCH["entities"] for f in e["fields"]}
def rotulo(desc, attr):
    if not desc: return attr
    t = re.sub(r"^C[oó]digo de refer[eê]ncia (d[aoe]s? )?", "", desc.strip(), flags=re.I)
    t = re.sub(r"^(a |o |as |os )", "", t)
    t = re.sub(r" em que (o|a) .* est[aá] localizad[oa]$", " de localização", t)
    return (t[:1].upper() + t[1:]) if t else attr
cat = rd("facetas_catalogo.csv"); dda = rd("dda_descricoes.csv")
desc = {}
for r in dda: desc.setdefault(r["entidade"], {}).setdefault(r["atributo"], {})[r["codigo_interno"]] = r["descricao"]
porent = {}
for c in cat:
    e = porent.setdefault(c["entidade"], {"facets": {}, "rows": {}, "motivos": {}})
    f = e["facets"].setdefault(c["facet_id"], {"id": c["facet_id"], "dims": json.loads(c["dimensoes_json"]), "metricas": {}})
    f["metricas"][c["metrica"]] = {"unidade": c["unidade"], "rollup": c["permite_rollup"] == "sim", "disjunta": c["particao_disjunta"] == "sim",
                                   "cobertura": c["cobertura"], "status": ST[c["status_qualidade"]]}
with open(PKG / "ativos_facetas.csv", encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        e = porent[r["entidade"]]; f = e["facets"][r["facet_id"]]
        dims = json.loads(r["dimensoes_json"]); codes = [dims[k] for k in f["dims"]]
        key = r["dist"] + "|" + "|".join(codes)
        rows = e["rows"].setdefault(r["facet_id"], {})
        row = rows.setdefault(key, [int(r["dist"]), codes, {}, {}])
        row[2][r["metrica"]] = num(r["valor"]); row[3][r["metrica"]] = ST[r["status_qualidade"]]
        if r["motivo_qualidade"]: e["motivos"][f"{r['dist']}|{r['metrica']}"] = r["motivo_qualidade"]
tam = {}
for ent, e in porent.items():
    attrs = sorted({a for f in e["facets"].values() for a in f["dims"]})
    obj = {"entidade": ent, "facets": list(e["facets"].values()), "descricoes": {a: desc.get(ent, {}).get(a, {}) for a in attrs},
           "atributos": {a: {"rotulo": rotulo(campo_desc.get((ent, a), ""), a), "descricao": campo_desc.get((ent, a), "")} for a in attrs},
           "rows": {fid: list(v.values()) for fid, v in e["rows"].items()}, "motivos": e["motivos"]}
    tam[ent] = dump(OUT / "facetas" / f"{ent}.json", obj)
listing = {"arquivos": sorted(p.relative_to(OUT).as_posix() for p in OUT.rglob("*.json"))}
dump(OUT / "assets.json", {**listing, "release_id": man["release_id"], "geo_visualizacao": "ARAT oficial 2025 com simplificacao adicional de 0,008 grau para a vista nacional; detalhe por DIST usa o arquivo do pacote"})
print(json.dumps({"index_kb": s_idx // 1024, "brasil_kb": size_br // 1024, "facetas_mb": round(sum(tam.values()) / 1e6, 2), "maior_faceta": max(tam.items(), key=lambda x: x[1])}, ensure_ascii=False))
