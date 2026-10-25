"""Fase 6 — inventário nacional ANO × DIST × ATIVO × PUBLICAÇÃO × STATUS e causa exata de cada lacuna (somente leitura).
Usa: catálogo ANEEL atual (evidencias/catalogo_arcgis_atual.json), inventários, checkpoints/failures, integridade dos ZIPs,
comparações e posição temporal dos excluídos, matriz de homologação da Fase 4, série e assets web.
Saídas (auditoria-fase6/): INVENTARIO_LACUNAS_NACIONAL.csv, RECUPERACAO_PUBLICACOES.csv, COBERTURA_ANTES_DEPOIS.csv"""
import collections, csv, json, pathlib, re

H = pathlib.Path("D:/NUCLEO_BDGD_2022_2024"); R = pathlib.Path("D:/NUCLEO_BDGD_2025"); A6 = R / "auditoria-fase6"; EV = A6 / "evidencias"
REPO = R / "repo/nucleo-dados-bdgd"
rd = lambda p: list(csv.DictReader(open(p, encoding="utf-8-sig")))
ANOS = [2022, 2023, 2024, 2025]
cat = json.loads((EV / "catalogo_arcgis_atual.json").read_text(encoding="utf-8"))["items"]
rx = re.compile(r"^(.+?)_(\d+)_(\d{4})-(\d{2})-(\d{2})")
pub_anos = collections.defaultdict(set); pub_itens = collections.defaultdict(list)
for x in cat:
    m = rx.search(x.get("title") or "")
    if m:
        pub_anos[m.group(2)].add(int(m.group(3)))
        if m.group(4) + m.group(5) == "1231": pub_itens[(m.group(2), int(m.group(3)))].append(x["id"])
inv = rd(H / "inventario/inventario_historico_2022_2024.csv"); inv25 = [r for r in rd(R / "inventario/inventario_2025.csv") if r["item_id"]]
nome = {r["dist"]: r["empresa"] for r in inv} | {r["dist"]: r["empresa"] for r in inv25}
itens = collections.defaultdict(list)
for r in inv: itens[(r["dist"], int(r["ano"]))].append(r)
for r in inv25: itens[(r["dist"], 2025)].append(dict(r, ano="2025", status="candidato"))
integ = {r["item_id"]: r for r in rd(EV / "integridade_downloads.csv")}
MAT = {(r["ano"], r["dist"], r["ativo"]): r for r in rd(REPO / "auditoria/fase4/MATRIZ_HOMOLOGACAO_2022_2025.csv") if r["nivel"] == "DIST"}
SER = {(r["ano"], r["dist"], r["ativo"]): r for r in rd(REPO / "output-historico/2022-2025/serie_ativos_original.csv")}
web = json.loads((REPO / "web/public/data/historico/serie.json").read_text(encoding="utf-8"))
webv = {(str(c[1]), str(c[0]), a): c for a, cs in web["original"].items() for c in cs}
ATIVOS = sorted({k[2] for k in MAT})
pos = {(r["ano_titulo"], r["dist"]): r for r in rd(EV / "posicao_temporal_excluidos.csv")}
SUCESSAO_ANTIGA = {"70": "69", "71": "69", "72": "69", "73": "69", "75": "69", "84": "69", "386": "69", "5217": "69", "397": "396", "6896": "5372"}
INCORP = {"6611": ("6600", 2023, "EPB_EBO_2023"), "6612": ("6585", 2022, "EMR_ENF_2022")}
universo = sorted({r["dist"] for r in inv} | {r["dist"] for r in inv25}, key=int)


def causa_dist_ano(d, y):
    """Causa no nível DIST × ano quando não há publicação utilizável."""
    if d in SUCESSAO_ANTIGA:
        return ("SUCESSAO_SOCIETARIA", f"código sem publicação desde {max(pub_anos[d]) if pub_anos[d] else 'nunca'}; perímetro reportado pela DIST {SUCESSAO_ANTIGA[d]} ({nome.get(SUCESSAO_ANTIGA[d], '')})", "nao", "usar a DIST sucessora")
    if d in INCORP and y > max(pub_anos[d] or {0}):
        dd, ae, ev = INCORP[d]
        return ("SUCESSAO_SOCIETARIA", f"incorporada à DIST {dd} ({nome.get(dd, '')}) — evento {ev}; última publicação {max(pub_anos[d])}", "nao", "série de perímetro (ponte) quando comprovada")
    if not pub_itens.get((d, y)):
        outros = sorted(pub_anos[d])
        return ("PUBLICACAO_NAO_LOCALIZADA", f"nenhum item 31/12/{y} no catálogo oficial ANEEL (consulta {json.loads((EV / 'catalogo_arcgis_atual.json').read_text(encoding='utf-8'))['obtido_em'][:10]}); anos publicados pela DIST: {','.join(map(str, outros)) or 'nenhum'}", "nao", "aguardar publicação ANEEL")
    return None


linhas = []
for y in ANOS:
    for d in universo:
        its = itens.get((d, y), [])
        base = causa_dist_ano(d, y) if not any(i["status"] in ("candidato", "revisao_pendente") for i in its) else None
        for a in ATIVOS:
            k = (str(y), d, a); mt = MAT.get(k); sr = SER.get(k)
            pubs = ";".join(i["item_id"] for i in its if i.get("item_id")) or ""
            if base:
                causa, det, rec, acao = base
            elif not mt:
                causa, det, rec, acao = ("INDICADOR_AUSENTE_OUTRA_RAZAO", "sem célula na série", "investigar", "")
            else:
                e = mt["estado_publicacao"]; st = mt["status_serie"]; mo = mt["motivo"]
                usado = mt["item_id"]
                ig = integ.get(usado) if usado else None
                if e in ("HOMOLOGADO", "COMPLETO_TECNICO", "APTO_COM_RESSALVAS"):
                    causa, det, rec, acao = ("DISPONIVEL", mo, "", "")
                    w = webv.get(k)
                    if not w or w[2] is None: causa, det, rec, acao = ("PARQUET_SEM_JSON", "valor validado ausente do asset web", "sim", "regenerar assets")
                elif st == "competencia_divergente":
                    c = [i for i in its if i["item_id"]]
                    p = pos.get((str(y), d), {})
                    causa, det, rec, acao = ("BLOQUEIO_COMPETENCIA", f"BASE do arquivo com outra competência; conteúdo: {p.get('indicio', 'não testado')}", "decisao_humana" if "titulo" in p.get("indicio", "") else "nao", "manter excluído (sem evidência para reatribuir o ano)")
                elif st == "revisao_pendente":
                    causa, det, rec, acao = ("REPUBLICACOES_DIVERGENTES", "duas publicações 31/12 com intervalo anual compatível e conteúdo divergente", "decisao_humana", "escolha registrada (DECISOES_DUPLICATAS_13_PARES.csv)")
                elif st == "ausente":
                    causa, det, rec, acao = ("ATIVO_NAO_APLICAVEL", sr["motivo"] if sr else mo, "nao", "N/D (nunca zero)")
                elif st == "campo_ausente":
                    causa, det, rec, acao = ("INDICADOR_AUSENTE_OUTRA_RAZAO", "campo do recorte ausente no layout da competência", "nao", "N/D")
                elif st == "bloqueado":
                    causa, det, rec, acao = ("INDICADOR_AUSENTE_OUTRA_RAZAO", "valor não homologável pela regra (comprimento nulo)", "nao", "N/D")
                elif e == "PENDENTE_DECISAO" and "sem registros" in mo:
                    causa, det, rec, acao = ("ENTIDADE_VAZIA_NA_ORIGEM", mo, "decisao_humana", "bloquear até republicação")
                elif e == "PENDENTE_DECISAO" and "incompleto" in mo:
                    causa, det, rec, acao = ("PUBLICACAO_INCOMPLETA_NA_ORIGEM", mo, "decisao_humana", "bloquear até republicação")
                elif e == "PENDENTE_DECISAO" and "BASE inconsistente" in mo:
                    causa, det, rec, acao = ("BASE_INCONSISTENTE", mo, "decisao_humana", "manter ou excluir (decisão humana)")
                elif st == "sem_publicacao":
                    causa, det, rec, acao = causa_dist_ano(d, y) or ("PUBLICACAO_NAO_LOCALIZADA", "sem item", "nao", "")
                elif st == "nao_processado":
                    causa, det, rec, acao = ("GDB_NAO_PROCESSADO", mo, "sim", "processar")
                else:
                    causa, det, rec, acao = ("INDICADOR_AUSENTE_OUTRA_RAZAO", f"{e}/{st}: {mo}", "investigar", "")
                if usado and ig and ig["sha_confere"] != "sim": causa, det, rec, acao = ("DOWNLOAD_INCOMPLETO_OU_CORROMPIDO", f"SHA {ig['sha_confere']}", "sim", "baixar novamente")
            linhas.append(dict(ano=y, dist=d, empresa=nome.get(d, ""), ativo=a, publicacoes=pubs, estado_publicacao=(mt or {}).get("estado_publicacao", "SEM_CELULA"),
                               status_serie=(mt or {}).get("status_serie", "sem_celula"), causa=causa, detalhe=det, recuperavel=rec, acao=acao))
with open(A6 / "INVENTARIO_LACUNAS_NACIONAL.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, list(linhas[0]), lineterminator="\n"); w.writeheader(); w.writerows(linhas)

# recuperação: ações executadas nesta fase, publicação por publicação
rec = []
for i in integ.values():
    rec.append(dict(acao="verificacao_integridade", item_id=i["item_id"], origem=i["origem"], resultado=f"SHA {i['sha_confere']}; ZIP abre {i['zip_abre']}", download_executado="nao", processamento_executado="nao"))
rec.append(dict(acao="consulta_catalogo_atual", item_id="(1014 itens)", origem="ArcGIS aneel_aneel", resultado="nenhum item novo ou modificado desde 23/10/2026", download_executado="nao (só metadados)", processamento_executado="nao"))
rec.append(dict(acao="identificacao_item_sem_rotulo", item_id="6c228d808d7548819b51859a8b2a775d", origem="catálogo ANEEL (título DUP)", resultado="baixado 16.303.005 bytes, SHA-256 e5579f5a…; ZIP íntegro; camada única DUP (Declarações de Utilidade Pública, 6.880 polígonos): não é BDGD", download_executado="sim", processamento_executado="nao"))
for r in rd(EV / "comparacao_gdbs.csv"):
    rec.append(dict(acao="comparacao_excluido_x_ano_da_BASE", item_id=r["item_a"], origem=f"{r['ano_a']}/{r['dist']}", resultado=f"{r['resultado']} ({r['camadas_identicas']}/{r['camadas_comuns']} camadas idênticas) com {r['ano_b'] or '-'} {r['item_b'][:8]}", download_executado="nao", processamento_executado="nao"))
for r in rd(EV / "posicao_temporal_excluidos.csv"):
    rec.append(dict(acao="posicao_temporal_do_conteudo", item_id=r["item_id"], origem=f"{r['ano_titulo']}/{r['dist']}", resultado=r["indicio"], download_executado="nao", processamento_executado="nao"))
with open(A6 / "RECUPERACAO_PUBLICACOES.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, list(rec[0]), lineterminator="\n"); w.writeheader(); w.writerows(rec)

# cobertura antes (Fase 3/4) e depois (Fase 6): DIST × ano com publicação utilizável e células publicáveis
cob = []
dep = collections.Counter((l["ano"], l["causa"]) for l in linhas)
for y in ANOS:
    cs = [l for l in linhas if l["ano"] == y]
    pubs = len({l["dist"] for l in cs if l["causa"] == "DISPONIVEL"})
    cob.append(dict(ano=y, dists_no_universo=len({l["dist"] for l in cs}), dists_com_celula_publicavel_antes=pubs, dists_com_celula_publicavel_depois=pubs,
                    celulas=len(cs), publicaveis_antes=sum(1 for l in cs if l["causa"] == "DISPONIVEL"), publicaveis_depois=sum(1 for l in cs if l["causa"] == "DISPONIVEL"),
                    recuperadas=0, **{f"causa_{c}": dep[(y, c)] for c in sorted({l['causa'] for l in linhas})}))
with open(A6 / "COBERTURA_ANTES_DEPOIS.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, list(cob[0]), lineterminator="\n"); w.writeheader(); w.writerows(cob)
tot = collections.Counter(l["causa"] for l in linhas)
print("células:", len(linhas), "| DIST no universo:", len(universo)); print(dict(tot))
print("recuperáveis tecnicamente sem decisão:", sum(1 for l in linhas if l["recuperavel"] == "sim"), "| decisão humana:", sum(1 for l in linhas if l["recuperavel"] == "decisao_humana"))
nd = collections.Counter((l["causa"], l["ano"]) for l in linhas if l["causa"] != "DISPONIVEL")
for k in sorted(nd): print(" ", k, nd[k])
