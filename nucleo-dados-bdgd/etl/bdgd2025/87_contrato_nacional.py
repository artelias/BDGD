"""Contrato de integração nacional BDGD 2022–2025 (Claude fornece, motor do PR #6 consome) — R3-HANDOFF-CLAUDE-FASE6.md.
Uma linha por ano × DIST × conceito × métrica para TODO o universo (114 códigos × 4 anos × 25 ativos), perímetro da
publicação original. Somente leitura dos artefatos versionados; nada é recalculado a partir de GDB e nenhum valor é criado.
Estados (contrato TS EstadoSerie): observado | zero_verificado | ausente | nao_homologado | nao_aplicavel | ruptura.
  - observado/zero_verificado: célula publicável na matriz (homologado, completo técnico ou apto com ressalvas);
    zero_verificado só quando a entidade existe na publicação e não há registros do tipo (valor validado 0);
  - nao_homologado: valor existe mas a célula é pendente de decisão ou bloqueada (valor = null; nunca entra em treino);
  - ausente: publicação inexistente, entidade vazia na publicação, campo ausente ou valor não homologável pela regra;
  - nao_aplicavel: ativo inexistente na DIST ou código de distribuidora incorporada (sucessão);
  - ruptura: não usado como estado da célula (o valor da competência é válido); a quebra de comparabilidade em relação
    ao ano anterior vem em ruptura_desde_ano_anterior / tipo_ruptura, para o motor cortar o trecho de treino.
status_homologacao: estado de publicação da matriz; fonte_homologada = true SOMENTE para HOMOLOGADO (COMPLETO_TECNICO
é validação automática, não homologação humana).
Saídas: output-historico/contrato-integracao/{serie_fisica_nacional.csv, agregados_nacionais.csv, pontes_sucessao.csv,
esquema.json, MANIFESTO.json}. Uso: python 87_contrato_nacional.py [raiz nucleo-dados-bdgd]"""
import csv, hashlib, json, pathlib, sys

RAIZ = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parents[2]
F4, F6 = RAIZ / "auditoria/fase4", RAIZ / "auditoria/fase6"; OUT = RAIZ / "output-historico/contrato-integracao"
DATA_GERACAO = "2026-10-28"; VERSAO = "contrato-nacional-1.0.1+republicacao-editorial-1"; REGRA = "r3-1+homologacao-fase6-1+republicacao-mais-recente"
rd = lambda p: list(csv.DictReader(open(p, encoding="utf-8-sig")))
# SHA-256 sobre o conteúdo com quebras de linha normalizadas para LF (independe de core.autocrlf / sistema operacional)
sha = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
CAT = json.loads((RAIZ / "etl/bdgd2025/config/conceitos_2025.json").read_text(encoding="utf-8"))
MED = {a["id"]: a["medida"] for a in CAT["ativos"]}; UNID = {"quantidade": "itens", "extensao_km": "km"}
MAT = {(r["ano"], r["dist"], r["ativo"]): r for r in rd(F4 / "MATRIZ_HOMOLOGACAO_2022_2025.csv") if r["nivel"] == "DIST"}
CONF = {}
for r in rd(F4 / "MATRIZ_CONFORMIDADE_BDGD_ORDINARIA.csv"):
    CONF.setdefault((r["ano_alvo"], r["dist"]), []).append(r)
INV = rd(F6 / "INVENTARIO_LACUNAS_NACIONAL.csv")
# SHA-256 recalculado e conferido nesta fase para cada ZIP oficial (auditoria/fase6/evidencias/integridade_downloads.csv)
SHA = {r["item_id"]: r["sha256"] for r in rd(F6 / "evidencias/integridade_downloads.csv") if r["sha_confere"] == "sim"}
RUPT = {"alteracao_classificacao", "alteracao_cadastral", "anomalia_fonte", "sucessao_societaria", "sem_evidencia_suficiente"}
rup = {}
for r in rd(F4 / "RANKING_ANOMALIAS_TEMPORAIS.csv"):
    if r["categoria"] in RUPT: rup[(r["ano_para"], r["dist"], r["ativo"])] = r["categoria"]
# Seleção editorial explícita de republicações, sem alterar matrizes históricas da auditoria.
POL_P = RAIZ / "web/public/data/historico/politica-republicacoes.json"
POL = json.loads(POL_P.read_text(encoding="utf-8")) if POL_P.exists() else {"pares": []}
SELECOES = {(str(p["ano"]), str(p["dist"])): p for p in POL["pares"]}
AUDITADOS = {(r["ano"], r["dist"], r["ativo"]): r for r in rd(F4 / "DECISOES_DUPLICATAS_13_PARES.csv")
            if (r["ano"], r["dist"]) in SELECOES}
if POL["pares"] and len(AUDITADOS) != 25 * len(POL["pares"]):
    raise RuntimeError("Seleção de republicações com quantitativos incompletos")
ESTADO = {"DISPONIVEL": None, "SUCESSAO_SOCIETARIA": "nao_aplicavel", "ATIVO_NAO_APLICAVEL": "nao_aplicavel", "REPUBLICACOES_DIVERGENTES": "nao_homologado",
          "BLOQUEIO_COMPETENCIA": "nao_homologado", "BASE_INCONSISTENTE": "nao_homologado", "ENTIDADE_VAZIA_NA_ORIGEM": "ausente", "PUBLICACAO_INCOMPLETA_NA_ORIGEM": "nao_homologado",
          "PUBLICACAO_NAO_LOCALIZADA": "ausente", "INDICADOR_AUSENTE_OUTRA_RAZAO": "ausente"}
ANOMALIA = ("subestim", "desativadas", "incompleto", "entidade de origem sem registros")


def iso(d):
    d = (d or "").split(";")[0]
    return f"{d[6:10]}-{d[3:5]}-{d[0:2]}" if len(d) == 10 and d[2] == "/" else None


linhas = []
for i in INV:
    y, d, a = i["ano"], i["dist"], i["ativo"]; mt = MAT.get((y, d, a)) or {}
    pubs = [c for c in CONF.get((y, d), []) if c["uso_na_serie"] in ("em_uso_na_serie", "pacote_2025", "par_competencia_unica_valida_em_uso")]
    pub = pubs[0] if pubs else None
    causa = i["causa"]; st_mat = mt.get("estado_publicacao", "NAO_DISPONIVEL")
    rec = AUDITADOS.get((y, d, a))
    if rec:
        escolha = SELECOES[(y, d)]
        if rec["item_B"] != escolha["selecionada"]["item_id"] or rec["competencia_declarada_B"] != f"{y}-12-31" or rec["DAT_FNL_B"] != f"31/12/{y}":
            raise RuntimeError(f"Publicacao inconsistente com o criterio: {d}/{y}/{a}")
        candidatos = [p for p in CONF.get((y, d), []) if p["item_id"] == rec["item_B"]]
        if len(candidatos) != 1:
            raise RuntimeError(f"Publicacao recente ausente na conformidade: {d}/{y}/{a}")
        pub = candidatos[0]
        if rec["status_B"] == "validado":
            causa, st_mat = "DISPONIVEL", "APTO_COM_RESSALVAS"
            mt = {**mt, "valor": rec["valor_B"], "motivo": "Republicacao mais recente: escolha tecnica com ressalva (sem homologacao)"}
        elif rec["status_B"] == "ausente":
            causa, st_mat = "INDICADOR_AUSENTE_OUTRA_RAZAO", "NAO_DISPONIVEL"
        else:
            raise RuntimeError(f"Status nao esperado no par {d}/{y}/{a}")
    if causa == "DISPONIVEL":
        v = float(mt["valor"]); estado = "zero_verificado" if v == 0 else "observado"; valor = v
        anomalo = any(w in mt["motivo"] for w in ANOMALIA) or (pub and pub["classe_intervalo"] != "INTERVALO_ANUAL_COMPATIVEL")
        cobertura = None if anomalo else 1
    else:
        estado, valor, cobertura = ESTADO.get(causa, "ausente"), None, None
        if st_mat in ("PENDENTE_DECISAO", "BLOQUEADO"): estado = "nao_homologado"   # há publicação, mas a célula aguarda decisão ou é bloqueada
    linhas.append(dict(
        ano=int(y), dist=int(d), conceitoId=a, metrica=MED[a], unidade=UNID[MED[a]], valor=valor, perimetroId="publicacao_original", regraVersao=REGRA,
        estado=estado, cobertura=cobertura, fonte="ANEEL — BDGD (catálogo ArcGIS aneel_aneel)" if pub else None,
        dataBase=iso(pub["DAT_FNL"]) if pub else f"{y}-12-31", perimetroBridgeId=None,
        motivo_nd=None if estado in ("observado", "zero_verificado") else (i["detalhe"] or mt.get("motivo") or causa),
        status_homologacao=st_mat if mt else "NAO_DISPONIVEL", fonte_homologada=st_mat == "HOMOLOGADO",
        publicacao_id=pub["item_id"] if pub else (i["publicacoes"] or None), sha256=SHA.get(pub["item_id"]) if pub else None,
        tipo_lacuna=None if causa == "DISPONIVEL" else causa, data_geracao=DATA_GERACAO,
        ruptura_desde_ano_anterior=(y, d, a) in rup or "quebra_classificacao" in mt.get("flags", ""), tipo_ruptura=rup.get((y, d, a)) or ("alteracao_classificacao" if "quebra_classificacao" in mt.get("flags", "") else None),
        intervalo_base=pub["classe_intervalo"] if pub else None, tag_extra=pub["tag_extra"] if pub else None, empresa=i["empresa"],
        nao_somar_em_agregados="NAO SOMAR" in mt.get("motivo", "")))
sys.path.insert(0, str(RAIZ))
from reconciliacao.contratos import anotar_contrato
anotar_contrato(linhas, RAIZ)
OUT.mkdir(parents=True, exist_ok=True)
CAMPOS = list(linhas[0])
def grava(nome, rows, campos):
    with open(OUT / nome, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, campos, lineterminator="\n"); w.writeheader()
        for r in rows: w.writerow({k: ("" if r[k] is None else ("true" if r[k] is True else "false" if r[k] is False else r[k])) for k in campos})
grava("serie_fisica_nacional.csv", linhas, CAMPOS)

# agregados: Brasil (asset web da homologação, com as correções da Fase 6) e painel balanceado
hom = json.loads((RAIZ / "web/public/data/historico/homologacao.json").read_text(encoding="utf-8"))
EST = {"H": "HOMOLOGADO", "T": "COMPLETO_TECNICO", "R": "APTO_COM_RESSALVAS", "P": "PENDENTE_DECISAO", "B": "BLOQUEADO", "N": "NAO_DISPONIVEL"}
ag = []
for a, rows in hom["brasil"].items():
    for ano, v, e, ninc, nexc, exc, mi in rows:
        total = ano not in (2022, 2023) and nexc == 0
        ag.append(dict(ano=ano, nivel="brasil", conceitoId=a, metrica=MED[a], unidade=UNID[MED[a]], valor=v, status_homologacao=EST[e], cobertura_completa=total,
                       n_dist_incluidas=ninc, n_dist_excluidas=nexc, dists_excluidas=";".join(map(str, exc)), universo="", motivo=hom["motivos"][mi], perimetroId="publicacao_original", data_geracao=DATA_GERACAO))
for a, p in hom["painel"].items():
    for ano, v in p["valores"]:
        ag.append(dict(ano=ano, nivel="painel_balanceado", conceitoId=a, metrica=MED[a], unidade=UNID[MED[a]], valor=v, status_homologacao="APTO_COM_RESSALVAS", cobertura_completa=False,
                       n_dist_incluidas=len(p["universo"]), n_dist_excluidas="", dists_excluidas="", universo=";".join(map(str, p["universo"])),
                       motivo="mesmas distribuidoras publicáveis nos quatro anos; não representa o total nacional", perimetroId="publicacao_original", data_geracao=DATA_GERACAO))
ag.sort(key=lambda r: (r["nivel"], r["conceitoId"], r["ano"]))
grava("agregados_nacionais.csv", ag, list(ag[0]))
pontes = [dict(perimetroBridgeId=pt["evento"], tipo=pt["tipo"], dist_destino=pt["destino"], dist_origem=pt["origem"], status=pt["status"], regra=pt["regra"], prova=pt["prova"],
               efetivacao=pt["efetivacao"], fonte=pt["fonte"], aplicada_na_serie=pt["status"] == "ja_incluida") for pt in hom["pontes"]]
grava("pontes_sucessao.csv", pontes, list(pontes[0]))

esquema = dict(versao=VERSAO, descricao="Série física nacional BDGD 2022–2025 por ano × DIST × conceito × métrica (perímetro da publicação original).",
               chave=["ano", "dist", "conceitoId", "metrica", "perimetroId"],
               campos={"ano": "inteiro 2022–2025", "dist": "código ANEEL da distribuidora (inteiro)", "conceitoId": "ativo do catálogo (25)", "metrica": "quantidade | extensao_km",
                       "unidade": "itens | km", "valor": "número ou vazio (null); nunca zero quando ausente", "perimetroId": "publicacao_original",
                       "regraVersao": "regra de cálculo + versão da matriz", "estado": "observado | zero_verificado | ausente | nao_homologado | nao_aplicavel",
                       "cobertura": "1 somente quando a célula é integral e verificável (publicação anual 01/01–31/12, sem anomalia de fonte); vazio caso contrário",
                       "fonte": "origem oficial", "dataBase": "BASE.DAT_FNL da publicação (AAAA-MM-DD)", "perimetroBridgeId": "vazio no perímetro original (pontes em pontes_sucessao.csv)",
                       "motivo_nd": "causa exata quando não observado", "status_homologacao": "HOMOLOGADO | COMPLETO_TECNICO | APTO_COM_RESSALVAS | PENDENTE_DECISAO | BLOQUEADO | NAO_DISPONIVEL",
                       "fonte_homologada": "true somente para HOMOLOGADO (2025); COMPLETO_TECNICO é validação automática", "publicacao_id": "item ArcGIS ANEEL",
                       "sha256": "SHA-256 do ZIP oficial verificado", "tipo_lacuna": "causa do inventário nacional", "data_geracao": "data de geração",
                       "ruptura_desde_ano_anterior": "true quando a variação em relação ao ano anterior não é comparável (classificação, cadastro, anomalia, sucessão ou sem explicação)",
                       "tipo_ruptura": "categoria da ruptura", "intervalo_base": "classe do intervalo DAT_INC–DAT_FNL", "tag_extra": "tag Extra do catálogo (observação, não exclui)",
                       "empresa": "nome", "nao_somar_em_agregados": "true para predecessora já contida na sucessora (ENF 2022)",
                       "observacao_id": "chave da ressalva auditada DIST × ANO × ATIVO × METRICA", "subtotal_observado": "parcela publicada; nunca alvo completo nem feature imputada",
                       "valores_publicados_json": "contagens cadastrais de componentes, separadas do valor físico publicável"},
               regras_de_uso=["treinar só com estado observado/zero_verificado", "não somar linhas com nao_somar_em_agregados=true", "cortar a série em ruptura_desde_ano_anterior=true",
                              "fonte_homologada=false não autoriza previsão validada", "agregado Brasil só com cobertura_completa=true; 2022–2023 nunca"],
               estados_ts=["observado", "zero_verificado", "ausente", "nao_homologado", "nao_aplicavel", "ruptura"])
(OUT / "esquema.json").write_text(json.dumps(esquema, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
import collections
cnt = collections.Counter((r["ano"], r["estado"]) for r in linhas)
cob = {str(y): {e: cnt[(y, e)] for e in ("observado", "zero_verificado", "ausente", "nao_homologado", "nao_aplicavel")} | {
           "pct_observado_sobre_aplicavel": round(100 * (cnt[(y, "observado")] + cnt[(y, "zero_verificado")]) / max(1, sum(cnt[(y, e)] for e in ("observado", "zero_verificado", "ausente", "nao_homologado"))), 2)}
       for y in (2022, 2023, 2024, 2025)}
man = dict(versao=VERSAO, data_geracao=DATA_GERACAO, linhas=len(linhas), agregados=len(ag), pontes=len(pontes), cobertura_por_ano=cob,
           entradas={str(p.relative_to(RAIZ)).replace("\\", "/"): sha(p) for p in [F4 / "MATRIZ_HOMOLOGACAO_2022_2025.csv", F4 / "MATRIZ_CONFORMIDADE_BDGD_ORDINARIA.csv",
                     F4 / "RANKING_ANOMALIAS_TEMPORAIS.csv", F6 / "INVENTARIO_LACUNAS_NACIONAL.csv", F6 / "CORRECOES_AUSENCIAS.csv", RAIZ / "web/public/data/historico/homologacao.json", RAIZ / "auditoria/reconciliacao/observacoes.json"]},
           saidas={n: sha(OUT / n) for n in ("serie_fisica_nacional.csv", "agregados_nacionais.csv", "pontes_sucessao.csv", "esquema.json")})
(OUT / "MANIFESTO.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print(f"{VERSAO}: {len(linhas)} linhas, {len(ag)} agregados, {len(pontes)} pontes"); print(json.dumps(cob, ensure_ascii=False))
