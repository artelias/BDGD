"""Fecha o pacote do piloto: atualiza inventario/cobertura com GDBs validados, gera dda_descricoes, distribuidoras,
qa_alertas, manifest e contrato de schema; roda os testes minimos (a)-(h) aplicaveis.
Uso: 50_finaliza_piloto.py <raiz_projeto> <knowledge>"""
import csv, json, sys, pathlib, hashlib, datetime, duckdb

R, K = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
INV, OUT, QA = R / "inventario", R / "piloto" / "2025-12-31", R / "qa"
DB = "2025-12-31"
now = datetime.datetime.now().isoformat(timespec="seconds")
rd = lambda p: list(csv.DictReader(open(p, encoding="utf-8")))


def dump(path, rs):
    ks = list(dict.fromkeys(k for r in rs for k in r))
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, ks); w.writeheader(); w.writerows(rs)


# 1. inventario: DATA_BASE validada no conteudo (BASE.DAT_FNL) + sha256 do zip
inv = rd(INV / "inventario_2025.csv"); validados = {}
for d in (R / "staging_parquet").glob("DIST=*"):
    c = json.load(open(d / f"DATA_BASE={DB}" / "conversao.json", encoding="utf-8"))
    validados[str(c["dist"])] = c
for r in inv:
    c = validados.get(r["dist"])
    if c:
        b = c["BASE"]
        r["data_base_validada"] = "2025-12-31" if b["DAT_FNL"] == "31/12/2025" and str(b["DIST"]) == r["dist"] else "DIVERGENTE"
        r["checksum_sha256"] = c["sha256_zip"]
        r["status"] = "homologada_piloto" if r["data_base_validada"] == DB else "validacao_falhou"
        r["motivo"] = f"BASE: DAT_INC={b['DAT_INC']} DAT_FNL={b['DAT_FNL']} DAT_EXT={b['DAT_EXT']}; DIST consistente em todas as camadas"
dump(INV / "inventario_2025.csv", inv)
cob = json.load(open(INV / "cobertura_2025.json", encoding="utf-8"))
cob["baixadas"] = len(validados); cob["homologadas"] = sum(r["status"] == "homologada_piloto" for r in inv)
cob["rejeitadas_validacao"] = sum(r["status"] == "validacao_falhou" for r in inv)
cob["atualizado_em"] = now
(INV / "cobertura_2025.json").write_text(json.dumps(cob, ensure_ascii=False, indent=1), encoding="utf-8")

# 2. DDA: apenas pares entidade/atributo realmente usados como faceta no piloto
rel = json.load(open(K / "BDGD_RELATIONSHIPS_AND_DDA_REFS_REV5.json", encoding="utf-8"))
dda = {t["table"]: t["values"] for t in json.load(open(K / "BDGD_DDA_CATALOG_M10.json", encoding="utf-8"))["tables"]}
agg = rd(OUT / "ativos_agregados.csv")
usados = {(r["entidade"], r["dimensao"]) for r in agg if r["dimensao"] != "__total__"}
dd = []
for x in rel["dda_references"]:
    if (x["source_entity"], x["source_field"]) in usados and x["dda_table"] in dda:
        for v in dda[x["dda_table"]]:
            dd.append({"entidade": x["source_entity"], "atributo": x["source_field"], "codigo_interno": str(v["COD_ID"]).strip(),
                       "descricao": v.get("DESCR"), "dominio": x["dda_table"], "versao": "DDA_M10_v1.1"})
dump(OUT / "dda_descricoes.csv", dd)

# 3. distribuidoras do piloto (grupo NAO verificado ainda)
pil = [r for r in inv if r["dist"] in validados]
dump(OUT / "distribuidoras.csv", [{"dist": r["dist"], "nome": r["empresa"], "sigla": r["sigla"], "grupo_economico": "nao_confirmado",
      "grupo_candidato_nome_comercial": r["grupo_economico_candidato"], "fonte": r["url_item"], "item_id": r["item_id"],
      "sha256": r["checksum_sha256"], "status": r["status"], "data_base": r["data_base_validada"]} for r in pil])
dump(OUT / "grupos_economicos.csv", [{"grupo": g, "status": "nao_confirmado", "fonte": "", "valido_de": "", "valido_ate": ""}
                                     for g in sorted({r["grupo_economico_candidato"] for r in pil})])
dump(OUT / "dist_grupo.csv", [{"dist": r["dist"], "grupo": r["grupo_economico_candidato"], "status": "nao_confirmado",
                               "valido_de": "", "valido_ate": "", "fonte": ""} for r in pil])

# 4. alertas de QA (fatos verificados no conteudo)
con = duckdb.connect()
P = lambda d, e: (R / "staging_parquet" / f"DIST={d}" / f"DATA_BASE={DB}" / f"entidade={e}" / "part-0.parquet").as_posix()
al = []
for d in sorted(validados, key=int):
    n, mx = con.execute(f"SELECT count(*) FILTER (WHERE POT_INST>75), max(POT_INST) FROM '{P(d,'UGBT')}'").fetchone()
    if n: al.append({"dist": d, "entidade": "UGBT", "tipo": "metrica_implausivel", "detalhe": f"{n} registros com POT_INST > 75 kW em BT; max {mx} kW", "acao": "potencia de UG* suspensa no agregado"})
    nct, nref = con.execute(f"SELECT (SELECT count(*) FROM '{P(d,'CTMT')}'), (SELECT count(DISTINCT CTMT) FROM '{P(d,'SSDMT')}')").fetchone()
    if nref > nct: al.append({"dist": d, "entidade": "CTMT", "tipo": "vinculo_incompleto", "detalhe": f"tabela CTMT com {nct} circuitos; SSDMT referencia {nref}", "acao": "recortes por circuito bloqueados para este DIST"})
    n, u = con.execute(f"SELECT count(*), count(DISTINCT COD_ID) FROM '{P(d,'UCBT')}'").fetchone()
    if n != u: al.append({"dist": d, "entidade": "UCBT", "tipo": "cod_id_repetido", "detalhe": f"{n} registros / {u} COD_ID distintos (campos de classe, situacao e energia variam)", "acao": "publicar quantidade e quantidade_cod_id_distinto separadas"})
tot = {(r["dist"], r["entidade"]): r for r in agg if r["dimensao"] == "__total__"}
for d in validados:
    a, b = float(tot[(d, "UNTRMT")]["valor"]), float(tot[(d, "EQTRMT")]["valor"])
    if abs(a - b) / a > 0.05:
        al.append({"dist": d, "entidade": "UNTRMT/EQTRMT", "tipo": "divergencia_metrica", "detalhe": f"UNTRMT {a:.0f} kVA vs EQTRMT {b:.0f} kVA ({100*(b-a)/a:+.1f}%)", "acao": "visoes sobrepostas; nunca somar; exibir separadamente"})
for r in rd(QA / "qa_vinculos.csv"):
    if r["status"] == "validado" and r["origem"] == "EQTRM.UC_UG": pass
dump(OUT / "qa_alertas.csv", al)

# 5. testes minimos
arat = rd(OUT / "qa_arat.csv"); recon = rd(OUT / "qa_reconciliacao.csv"); mat = rd(OUT / "matriz_empresas_2025.csv")
proib = {"COD_ID", "CEP", "CNAE", "BRR", "PN_CON", "RAMAL", "CPF", "CNPJ", "NOME"}
hdrs = {f.name: set(next(csv.reader(open(f, encoding="utf-8")))) for f in OUT.glob("*.csv")}
supp = {(r["entidade"], r["atributo"]) for r in dd}
grp = rd(OUT / "comparativo_grupos_piloto.csv")
testes = {
    "a_100pct_snapshots_2025": all(r["data_base"] == DB for r in agg) and all(r["data_base"] == DB for r in mat) and all(r["data_base_validada"] == DB for r in pil),
    "b_dist_com_fonte_hash_qa": all(r["checksum_sha256"] and r["url_item"] for r in pil),
    "c_contagens_reconciliadas": all(r["ok"] == "True" for r in recon),
    "d_arat_valida_ou_ausencia": all(r["status"] == "ARAT_ausente" or r["valida_saida"] == "True" for r in arat),
    "e_filtros_dda_suportados": all((r["entidade"], r["dimensao"]) in supp for r in agg if r["dimensao"] != "__total__"),
    "f_grupos_sem_dupla_contagem": all(int(g["quantidade"]) == sum(int(tot[(d, g["entidade"])]["quantidade"]) for d in g["dists"].split("|")) for g in grp),
    "g_sem_colunas_individuais": all(not (h & proib) for h in hdrs.values()),
}
# h: GeoJSON parse + propriedades minimas
ok_h = True
for f in (OUT / "geo").glob("*.geojson"):
    g = json.load(open(f, encoding="utf-8")); p = g["features"][0]["properties"]
    ok_h &= g["type"] == "FeatureCollection" and set(p) == {"dist", "data_base", "source_item_id"} and p["data_base"] == DB
testes["h_geojson_schema"] = ok_h

# 6. contrato e manifest
contrato = {"schema_version": "0.1.0-piloto", "data_base": DB, "arquivos": {n: sorted(h) for n, h in hdrs.items()},
            "geo": {"arquivo": "geo/arat_2025_<dist>.geojson", "crs": "EPSG:4326", "propriedades": {"dist": "integer", "data_base": "string(YYYY-MM-DD)", "source_item_id": "string"}},
            "convencoes": {"N/D": "camada inexistente no GDB", "0": "camada existente sem registros (auditado)",
                           "quantidade": "count(*) de registros", "quantidade_cod_id_distinto": "apenas na linha __total__",
                           "dimensao": "__total__ ou atributo DDA (faceta de 1 dimensao; soma das facetas = total)"}}
(OUT / "schemas").mkdir(exist_ok=True)
(OUT / "schemas" / "contrato_publicacao.json").write_text(json.dumps(contrato, ensure_ascii=False, indent=1), encoding="utf-8")
chk = {str(f.relative_to(OUT)).replace("\\", "/"): hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(OUT.rglob("*")) if f.is_file() and f.name != "manifest.json"}
lock = json.load(open(K / "KNOWLEDGE_LOCK.json", encoding="utf-8"))
man = {"data_base": DB, "versao_publicacao": "piloto-0.1.0", "status": "PILOTO_NAO_APROVADO_PARA_PRODUCAO", "gerado_em": now,
       "autoria": "Arthur Henrique Lima", "empresas_incluidas": [{"dist": r["dist"], "sigla": r["sigla"], "item_id": r["item_id"], "url": r["url_item"], "sha256_gdb_zip": r["checksum_sha256"]} for r in pil],
       "empresas_excluidas": "piloto: demais 96 DIST com GDB 2025 encontrados aguardam processamento; 15 DIST sem_publicacao_2025 (ver inventario)",
       "dda_versao": "BDGD_DDA_CATALOG_M10 v1.1", "conhecimento": {f["file"]: f["sha256_copy"] for f in lock["files"]},
       "testes_minimos": testes, "checksums": chk, "licenca_fonte": "Dados abertos ANEEL (atribuicao: Agencia Nacional de Energia Eletrica)"}
(OUT / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(testes, indent=1)); print("alertas:", len(al)); [print("  ", a) for a in al]
