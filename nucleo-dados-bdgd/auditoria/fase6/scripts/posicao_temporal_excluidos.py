"""Fase 6 — posição temporal do conteúdo dos arquivos excluídos por competência (somente leitura dos ZIPs oficiais).
Para cada entidade-chave compara a contagem de registros do arquivo excluído com as publicações válidas da mesma DIST
nos anos vizinhos. Se o conteúdo fica entre o ano do título-1 e o ano do título+1 (e difere do ano declarado na BASE),
há indício de BASE preenchida com o ano errado; se coincide com o ano da BASE, o arquivo é outra versão daquele ano.
Saída: evidencias/posicao_temporal_excluidos.csv (indício, não decisão)."""
import csv, pathlib, zipfile
import pyogrio

H = pathlib.Path("D:/NUCLEO_BDGD_2022_2024"); R = pathlib.Path("D:/NUCLEO_BDGD_2025"); OUT = R / "auditoria-fase6/evidencias/posicao_temporal_excluidos.csv"
CHAVE = ["UCBT", "UCMT", "PIP", "SSDMT", "SSDBT", "PONNOT", "EQTRMT", "EQME", "UGBT", "CTMT"]
CONF = list(csv.DictReader(open(R / "auditoria-fase4/MATRIZ_CONFORMIDADE_BDGD_ORDINARIA.csv", encoding="utf-8")))
usado = {(c["ano_alvo"], c["dist"]): c["item_id"] for c in CONF if c["uso_na_serie"] in ("em_uso_na_serie", "pacote_2025", "par_competencia_unica_valida_em_uso")}


def zip_de(ano, dist, item):
    if ano == "2025": return next((R / "staging_raw" / f"DIST={dist}" / "DATA_BASE=2025-12-31").glob("*.zip"), None)
    return next((H / "raw" / ano / dist / item).glob("*.zip"), None)


def contagens(z):
    with zipfile.ZipFile(z) as zz:
        rz = sorted({n[:n.lower().index(".gdb") + 4] for n in zz.namelist() if ".gdb/" in n.lower()})
    src = f"/vsizip/{pathlib.Path(z).as_posix()}/{rz[0]}" if rz else f"/vsizip/{pathlib.Path(z).as_posix()}"
    lay = {l[0].upper().removesuffix("_TAB"): l[0] for l in pyogrio.list_layers(src)}
    return {e: int(pyogrio.read_info(src, layer=lay[e], force_feature_count=True)["features"]) for e in CHAVE if e in lay}


linhas = []
for c in CONF:
    if c["uso_na_serie"] not in ("excluido_competencia", "par_item_excluido_competencia"): continue
    t = int(c["ano_alvo"]); fnl = c["DAT_FNL"][-4:]
    ze = zip_de(c["ano_alvo"], c["dist"], c["item_id"]); ce = contagens(ze)
    viz = {}
    for y in (t - 1, t, t + 1, int(fnl)):
        k = (str(y), c["dist"])
        if k in usado and y not in viz:
            z = zip_de(str(y), c["dist"], usado[k])
            if z: viz[y] = contagens(z)
    votos_titulo = votos_base = comparaveis = 0
    det = []
    for e in CHAVE:
        if e not in ce or not ce[e]: continue
        a, b = viz.get(t - 1, {}).get(e), viz.get(t + 1, {}).get(e)
        vb = viz.get(int(fnl), {}).get(e) if int(fnl) != t else None
        det.append(f"{e}: excl={ce[e]} | {t - 1}={a} | {t + 1}={b}" + (f" | BASE {fnl}={vb}" if vb is not None and int(fnl) not in (t - 1, t + 1) else ""))
        if a is not None and b is not None and a != b:
            comparaveis += 1
            if min(a, b) < ce[e] < max(a, b) or (ce[e] not in (a, b) and abs(ce[e] - a) < abs(b - a) and abs(ce[e] - b) < abs(b - a)): votos_titulo += 1
            elif int(fnl) in viz and ce[e] == viz[int(fnl)].get(e): votos_base += 1
    if comparaveis == 0: ind = "sem_vizinhos_para_comparar"
    elif votos_titulo >= max(2, 0.6 * comparaveis): ind = "conteudo_compativel_com_o_ano_do_titulo (indicio de BASE preenchida com ano errado)"
    elif votos_base >= max(2, 0.6 * comparaveis): ind = "conteudo_igual_ao_ano_da_BASE (versao do ano da BASE)"
    else: ind = "inconclusivo"
    linhas.append(dict(ano_titulo=t, dist=c["dist"], empresa=c["empresa"], item_id=c["item_id"], DAT_INC=c["DAT_INC"], DAT_FNL=c["DAT_FNL"],
                       vizinhos_validos=";".join(str(y) for y in sorted(viz)), entidades_comparaveis=comparaveis, entre_vizinhos=votos_titulo,
                       igual_ano_base=votos_base, indicio=ind, detalhe=" || ".join(det)))
    print(t, c["dist"], c["empresa"][:14], ind, f"{votos_titulo}/{comparaveis}", flush=True)
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, list(linhas[0]), lineterminator="\n"); w.writeheader(); w.writerows(linhas)
