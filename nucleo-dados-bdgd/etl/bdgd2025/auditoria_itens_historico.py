"""Auditoria por ano/DIST/item do ETL historico 2022-2024 (somente leitura).
Saida: output-historico/2022-2025/qa_itens_auditoria.csv com status do item, registros, versao do pipeline (hash),
origem (item ArcGIS + SHA-256 da fonte), estado da DIST/ano na serie e motivo de exclusao ou falha."""
import csv, glob, hashlib, json, os, pathlib

H = pathlib.Path("D:/NUCLEO_BDGD_2022_2024"); R = pathlib.Path("D:/NUCLEO_BDGD_2025")
HP = H / "repo/nucleo-dados-bdgd/historico"
sha = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
VERS = {sha(HP / "pipeline.py"): "pipeline.py (original)", sha(HP / "pipeline_antijoin.py"): "pipeline_antijoin.py"}
OUT = R / "output-historico/2022-2025"

serie = {}
for r in csv.DictReader(open(OUT / "serie_ativos_original.csv", encoding="utf-8-sig")):
    k = (r["ano"], r["dist"]); serie.setdefault(k, {}); serie[k][r["status"]] = serie[k].get(r["status"], 0) + 1
    if r["status"] != "validado" and r["motivo"]: serie[k]["_motivo"] = r["motivo"]
    if r["item_id"]: serie[k]["_item"] = r["item_id"]
eq = {}
for f in glob.glob(str(H / "proc/*/*/equivalencia_duplicatas.json")):
    j = json.load(open(f, encoding="utf-8")); eq[(str(j["ano"]), str(j["dist"]))] = j

linhas = []
for x in csv.DictReader(open(H / "inventario/inventario_historico_2022_2024.csv", encoding="utf-8")):
    a, d, it = x["ano"], x["dist"], x["item_id"]
    base = H / "proc" / a / d / it
    ck, fl = base / "checkpoint.json", base / "failure.json"
    reg, versao, estado, motivo = "", "", "", ""
    if x["status"] == "ausente_catalogo":
        estado, motivo = "ausente_catalogo", "sem publicacao no catalogo ArcGIS para o ano"
    elif ck.exists():
        c = json.load(open(ck, encoding="utf-8")); reg = c.get("rows", ""); versao = VERS.get(c.get("pipeline_sha256"), "outro:" + str(c.get("pipeline_sha256"))[:12])
        estado = "processado"
    elif fl.exists():
        f = json.load(open(fl, encoding="utf-8")); estado = "falha"
        motivo = f"{f['error_type']}: {f['error'].splitlines()[0][:110]}"
        if "DAT_FNL" in f["error"]: estado = "competencia_divergente"
    else:
        estado, motivo = "nao_processado", "sem checkpoint nem registro de falha"
    if x["status"] == "revisao_pendente":
        e = eq.get((a, d))
        dup = "publicacao multipla: " + (("equivalente (" + e["criterio"] + ")") if e and e.get("equivalente") else ("sem equivalencia integral: decisao humana" if e else "comparacao nao executada"))
        motivo = (motivo + "; " if motivo else "") + dup
    s = serie.get((a, d), {})
    est_serie = "validado" if s.get("validado") and s.get("_item") == it else ",".join(sorted(k for k in s if not k.startswith("_")))
    if s.get("_motivo") and estado == "processado": motivo = (motivo + "; " if motivo else "") + "serie: " + s["_motivo"]
    linhas.append(dict(ano=a, dist=d, empresa=x["empresa"], item_id=it, status_inventario=x["status"], estado_item=estado, registros=reg,
                       pipeline=versao, origem_arcgis=x["url_item"], sha256_fonte=x["sha256"], tamanho_mb=int(x["tamanho_bytes"] or 0) // 2 ** 20 if x["tamanho_bytes"] else "",
                       estado_na_serie=est_serie, motivo=motivo))
linhas.sort(key=lambda r: (r["ano"], int(r["dist"]), r["item_id"]))
with open(OUT / "qa_itens_auditoria.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, list(linhas[0]), lineterminator="\n"); w.writeheader(); w.writerows(linhas)
import collections
c = collections.Counter((r["ano"], r["estado_item"]) for r in linhas)
for k in sorted(c): print(k, c[k])
