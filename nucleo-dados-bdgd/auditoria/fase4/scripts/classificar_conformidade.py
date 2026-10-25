"""Fase 4 — matriz de conformidade BDGD Ordinaria (somente leitura; usa a leitura real da BASE feita por
conformidade_ordinaria.py). Evidencias mantidas SEPARADAS:
  (a) intervalo da BASE (criterio operacional informado pelo responsavel: ordinaria anual = DAT_INC 01/01/AAAA e DAT_FNL 31/12/AAAA);
  (b) tag 'Extra' do catalogo ArcGIS (metadado; nao exclui sozinha);
  (c) competencia nos metadados (data no titulo e tag de data do catalogo). As entidades do GDB nao tem campo DATA_BASE.
classe_intervalo: INTERVALO_ANUAL_COMPATIVEL | INTERVALO_NAO_ANUAL (DAT_FNL correto, DAT_INC diferente de 01/01) |
INCONSISTENTE (DAT_FNL fora de 31/12 do ano-alvo, intervalo degenerado ou GDBs conflitantes) | SEM_EVIDENCIA_SUFICIENTE.
Saida: auditoria-fase4/MATRIZ_CONFORMIDADE_BDGD_ORDINARIA.csv"""
import collections, csv, datetime as dt, json, pathlib, re

A = pathlib.Path("D:/NUCLEO_BDGD_2025/auditoria-fase4"); H = pathlib.Path("D:/NUCLEO_BDGD_2022_2024")
L = list(csv.DictReader(open(A / "CONFORMIDADE_BDGD_ORDINARIA.csv", encoding="utf-8")))
cat = {x["id"]: x for x in json.loads((H / "inventario/catalogo_arcgis.json").read_text(encoding="utf-8"))["items"]}
pares = collections.defaultdict(list)
for r in L:
    if r["status_inventario"] == "revisao_pendente": pares[(r["ano_alvo"], r["dist"])].append(r)
uso_par = {}
for r in csv.DictReader(open("D:/NUCLEO_BDGD_2025/output-historico/2022-2025/qa_duplicatas_reconciliadas.csv", encoding="utf-8")):
    uso_par[(r["ano"], r["dist"])] = r["classificacao"]


def d(s):
    try: return dt.datetime.strptime(s.strip(), "%d/%m/%Y").date()
    except Exception: return None


out = []
for r in L:
    ano = int(r["ano_alvo"])
    incs = [d(x) for x in r["DAT_INC"].split(";")]; fnls = [d(x) for x in r["DAT_FNL"].split(";")]
    exts = [d(x) for x in r["DAT_EXT"].split(";")]
    lida = r["fonte_BASE"].startswith(("GDB original", "staging_parquet")) and all(incs) and all(fnls)
    if not lida: classe, det = "SEM_EVIDENCIA_SUFICIENTE", "BASE nao lida ou com datas invalidas"
    elif len(set(zip(incs, fnls))) > 1: classe, det = "INCONSISTENTE", "GDBs do mesmo ZIP com BASE diferentes"
    elif fnls[0] != dt.date(ano, 12, 31): classe, det = "INCONSISTENTE", f"DAT_FNL {fnls[0]:%d/%m/%Y} diferente de 31/12/{ano} (titulo declara {r['data_base_titulo']})"
    elif incs[0] >= fnls[0]: classe, det = "INCONSISTENTE", f"intervalo degenerado: DAT_INC = DAT_FNL = {fnls[0]:%d/%m/%Y}"
    elif incs[0] == dt.date(ano, 1, 1): classe, det = "INTERVALO_ANUAL_COMPATIVEL", f"01/01/{ano} a 31/12/{ano}"
    else: classe, det = "INTERVALO_NAO_ANUAL", f"DAT_INC {incs[0]:%d/%m/%Y} (DAT_FNL correto 31/12/{ano}); periodo de {(fnls[0] - incs[0]).days + 1} dias"
    x = cat.get(r["item_id"], {})
    tag_data = next((t for t in (x.get("tags") or []) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", t)), "")
    meta_ok = r["data_base_titulo"] == f"{ano}-12-31" and (tag_data in ("", f"{ano}-12-31"))
    ext_ok = bool(exts and exts[0] and fnls and fnls[0] and exts[0] >= fnls[0])
    # uso na serie
    if r["ano_alvo"] == "2025": uso = "pacote_2025"
    elif r["status_inventario"] == "revisao_pendente":
        c = uso_par.get((r["ano_alvo"], r["dist"]), "")
        uso = ("par_competencia_unica_valida_em_uso" if r["uso_atual"] == "par_duplicado_processado" else "par_item_excluido_competencia") if c == "competencia_unica_valida" else "par_divergente_pendente"
    else: uso = {"na_serie": "em_uso_na_serie", "excluido_competencia": "excluido_competencia"}.get(r["uso_atual"], r["uso_atual"])
    em_uso = uso in ("em_uso_na_serie", "pacote_2025", "par_competencia_unica_valida_em_uso")
    # decisao humana somente quando necessaria
    if classe == "INTERVALO_ANUAL_COMPATIVEL" and r["tag_extra"] == "nao": dec, rec = "nao", "elegivel: intervalo anual compativel, sem tag Extra"
    elif classe == "INTERVALO_ANUAL_COMPATIVEL" and r["tag_extra"] == "sim":
        dec = "sim (decisao unica por ciclo)" if r["ano_alvo"] == "2025" else "sim"
        rec = "manter: intervalo anual compativel; confirmar significado da tag Extra (" + ("presente em 100% das publicacoes 31/12/2025, sem alternativa sem tag" if r["ano_alvo"] == "2025" else "unica publicacao 31/12 da DIST/ano") + ")"
    elif classe == "INTERVALO_NAO_ANUAL": dec, rec = ("sim" if em_uso else "nao"), "DAT_FNL correto; aceitar ou nao periodo iniciado antes de 01/01 como base anual" + ("" if em_uso else " (item fora de uso)")
    elif classe == "INCONSISTENTE": dec, rec = ("sim" if em_uso else "nao"), ("item EM USO com BASE inconsistente: decidir manter ou excluir" if em_uso else "ja excluido da serie (correto pelo DAT_FNL); so reavaliar se houver republicacao")
    else: dec, rec = "sim", "sem evidencia suficiente"
    if uso == "par_divergente_pendente" and dec == "nao": rec += "; pendente apenas pela escolha entre publicacoes do par (ver DECISOES_DUPLICATAS_13_PARES.csv)"
    out.append(dict(ano_alvo=r["ano_alvo"], dist=r["dist"], empresa=r["empresa"], item_id=r["item_id"], url_item=r["url_item"], titulo_catalogo=r["titulo_catalogo"],
                    versao_titulo=r["versao_titulo"], publicado_em_catalogo=(dt.datetime.utcfromtimestamp(int(x["created"]) / 1000).strftime("%Y-%m-%d") if x.get("created") else "nao_disponivel"),
                    data_base_titulo=r["data_base_titulo"], tag_data_catalogo=tag_data or "nao_disponivel", competencia_metadados_ok="sim" if meta_ok else "nao",
                    DAT_INC=r["DAT_INC"], DAT_FNL=r["DAT_FNL"], DAT_EXT=r["DAT_EXT"], DAT_EXT_apos_DAT_FNL="sim" if ext_ok else "nao", DESCR=" ".join(r["DESCR"].split()),
                    DATA_BASE_entidades="campo_inexistente_no_GDB_original" if r["ano_alvo"] != "2025" else "campo_inexistente_no_GDB_original (coluna acrescentada pelo ETL)",
                    fonte_BASE=r["fonte_BASE"], classe_intervalo=classe, detalhe_intervalo=det, tag_extra=r["tag_extra"],
                    tipo_regulatorio="NAO_COMPROVADO_DOCUMENTALMENTE", sha256_fonte=r["sha256_fonte"], uso_na_serie=uso,
                    decisao_humana_necessaria=dec, recomendacao=rec, DECISAO_HUMANA="PENDENTE" if dec.startswith("sim") else "nao_requerida"))
with open(A / "MATRIZ_CONFORMIDADE_BDGD_ORDINARIA.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, list(out[0]), lineterminator="\n"); w.writeheader(); w.writerows(out)
print(collections.Counter((o["ano_alvo"], o["classe_intervalo"]) for o in out))
for grupo, cond in (("EM USO NA SERIE", lambda o: o["uso_na_serie"] in ("em_uso_na_serie", "pacote_2025", "par_competencia_unica_valida_em_uso")),
                    ("PARES DIVERGENTES PENDENTES", lambda o: o["uso_na_serie"] == "par_divergente_pendente"),
                    ("EXCLUIDAS", lambda o: "excluido" in o["uso_na_serie"])):
    g = [o for o in out if cond(o)]
    print(grupo, len(g), dict(collections.Counter(o["classe_intervalo"] for o in g)), "| tag Extra:", sum(o["tag_extra"] == "sim" for o in g))
print("decisao humana:", [(o["ano_alvo"], o["dist"], o["empresa"], o["classe_intervalo"], o["tag_extra"]) for o in out if o["decisao_humana_necessaria"] == "sim"])
