"""Asset web da homologacao assistida (Fase 4) para a pagina Evolucao: so leitura dos artefatos versionados em
auditoria/fase4/ e de output-historico/2022-2025/ (nenhum GDB, checkpoint ou valor e recalculado).
Saida: web/public/data/historico/homologacao.json
  celulas[ativo]  = [[dist, ano, estado, motivo_idx, flags]]   estado: H homologado, T completo tecnico, R apto com ressalvas,
                                                                P pendente decisao, B bloqueado, N nao disponivel
                    flags: bits 1 quebra de classificacao, 2 sinal temporal, 4 nao somar (sucessao ja contida no destino), 8 entidade vazia na publicacao (Fase 6)
  brasil[ativo]   = [[ano, valor|null, estado, n_incluidas, n_excluidas, [dists_excluidas], motivo_idx]]
  painel[ativo]   = {universo: [dists], valores: [[ano, valor]]}
  proveniencia["dist|ano"] = publicacoes oficiais (item ArcGIS, versao, BASE, tag Extra, SHA-256, uso na serie)
  sinais["dist|ativo|de|para"] = [natureza, confianca, causa, prioridade]
  pares["dist|ano"], sem_tuc["dist|ano|conceito"], fontes (SHA-256 dos CSV de origem)
Uso: python 86_homologacao_web.py [raiz do repositorio nucleo-dados-bdgd]"""
import csv, hashlib, json, pathlib, sys

RAIZ = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parents[2]
F4 = RAIZ / "auditoria" / "fase4"; HIS = RAIZ / "output-historico" / "2022-2025"; OUT = RAIZ / "web" / "public" / "data" / "historico" / "homologacao.json"
EST = {"HOMOLOGADO": "H", "COMPLETO_TECNICO": "T", "APTO_COM_RESSALVAS": "R", "PENDENTE_DECISAO": "P", "BLOQUEADO": "B", "NAO_DISPONIVEL": "N"}
NAT = {"variacao_real_plausivel": "expansao_fisica", "alteracao_cadastral": "mudanca_cadastral", "alteracao_classificacao": "mudanca_classificacao",
       "anomalia_fonte": "anomalia_publicacao", "sucessao_societaria": "sucessao", "base_pequena": "base_pequena", "sem_evidencia_suficiente": "sem_explicacao"}
rd = lambda p: list(csv.DictReader(open(p, encoding="utf-8-sig")))
num = lambda v: None if v in ("", None) else float(v)
FONTES = ["MATRIZ_HOMOLOGACAO_2022_2025.csv", "MATRIZ_CONFORMIDADE_BDGD_ORDINARIA.csv", "RANKING_ANOMALIAS_TEMPORAIS.csv", "DECISOES_DUPLICATAS_13_PARES.csv", "PONTES_SUCESSOES_HISTORICAS.csv"]

import re
# texto de apresentacao: a matriz (fonte de verdade) usa ASCII e referencias internas; o asset web usa portugues legivel
ACENTOS = {"nao": "não", "versao": "versão", "expansao": "expansão", "inclusao": "inclusão", "ha": "há", "reclassificacao": "reclassificação",
           "persistencia": "persistência", "recodificacao": "recodificação", "fisica": "física", "nao_identificada": "não identificada", "tendencia": "tendência",
           "consistente": "consistente", "atributo": "atributo", "publicaveis": "publicáveis", "celulas": "células", "compativel": "compatível", "observacao": "observação", "atipica": "atípica", "catalogo": "catálogo", "publicacao": "publicação", "publicacoes": "publicações", "competencia": "competência", "decisao": "decisão",
           "validacao": "validação", "automaticas": "automáticas", "automatica": "automática", "classificacao": "classificação", "homologavel": "homologável",
           "homologacao": "homologação", "multiplas": "múltiplas", "divergentes": "divergentes", "escolha": "escolha", "intervalo": "intervalo", "anual": "anual",
           "periodo": "período", "dias": "dias", "correto": "correto", "inconsistente": "inconsistente", "degenerado": "degenerado", "comprovada": "comprovada",
           "registros": "registros", "provavelmente": "provavelmente", "parque": "parque", "sinal": "sinal", "temporal": "temporal", "distribuidora": "distribuidora",
           "ja": "já", "contidos": "contidos", "somar": "somar", "regra": "regra", "valor": "valor", "subestimado": "subestimado", "saneadas": "saneadas",
           "marcadas": "marcadas", "fonte": "fonte", "sem": "sem", "ressalva": "ressalva", "presente": "presente", "significado": "significado", "documentado": "documentado",
           "ciclo": "ciclo", "incompleto": "incompleto", "identidade": "identidade", "entidade": "entidade", "origem": "origem", "humana": "humana", "orgao": "órgão",
           "ate": "até", "alteracao": "alteração", "variacao": "variação", "codificacao": "codificação", "mudanca": "mudança", "parcela": "parcela", "nivel": "nível"}
def legivel(t):
    t = re.sub(r"\s*\((?:RANKING_ANOMALIAS_TEMPORAIS|DECISOES_DUPLICATAS_13_PARES)\.csv[^)]*\)", "", t)
    t = t.replace("BLOQUEAR", "bloquear").replace("tag Extra no catalogo", "tag “Extra” no catálogo ANEEL").replace("NAO SOMAR ao Brasil/painel", "não somado ao Brasil nem ao painel")
    t = t.replace("intervalo BASE", "intervalo da tabela BASE").replace("regra UC v3", "regra de unidades consumidoras").replace(" DS ", " desativadas (DS) ").replace("sinal temporal", "variação atípica sinalizada")
    return re.sub(r"\b[a-z]+\b", lambda w: ACENTOS.get(w.group(0), w.group(0)), t)

motivos, mi = [], {}
def m(t):
    t = legivel(t)
    if t not in mi: mi[t] = len(motivos); motivos.append(t)
    return mi[t]

M = rd(F4 / "MATRIZ_HOMOLOGACAO_2022_2025.csv")
cel, br, painel = {}, {}, {}
for r in M:
    a = r["ativo"]
    if r["nivel"] == "DIST":
        fl = (1 if "quebra_classificacao" in r["flags"] else 0) | (2 if "sinal_temporal" in r["flags"] else 0) | (4 if "NAO SOMAR" in r["motivo"] else 0)
        cel.setdefault(a, []).append([int(r["dist"]), int(r["ano"]), EST[r["estado_publicacao"]], m(r["motivo"]), fl])
    elif r["nivel"] == "BRASIL":
        br.setdefault(a, []).append([int(r["ano"]), num(r["valor"]), EST[r["estado_publicacao"]], int(r["n_dist_incluidas"] or 0), int(r["n_dist_excluidas"] or 0),
                                     [int(x) for x in r["dists_excluidas"].split(";") if x], m(r["motivo"])])
    else:
        p = painel.setdefault(a, {"universo": [int(x) for x in r["universo"].split(";") if x], "valores": []})
        p["valores"].append([int(r["ano"]), num(r["valor"])])
for v in list(br.values()) + [p["valores"] for p in painel.values()]: v.sort()

# Fase 6: células que a Fase 4 tratou como "ativo não aplicável" mas cuja entidade veio vazia (ou sem o tipo) na publicação,
# com o ativo presente em outros anos da mesma DIST: dado AUSENTE (nunca zero, nunca "não aplicável"). Flag 8. Os agregados
# Brasil desses anos deixam de ser completos: a DIST entra como excluída e o estado vira "apto com ressalvas".
F6 = RAIZ / "auditoria" / "fase6" / "CORRECOES_AUSENCIAS.csv"
corr = {}
if F6.exists():
    for r in rd(F6):
        if r["classificacao"] != "ATIVO_NAO_APLICAVEL": corr[(int(r["dist"]), int(r["ano"]), r["ativo"])] = r
    FONTES.append("../fase6/CORRECOES_AUSENCIAS.csv")
for a, cs in cel.items():
    for c in cs:
        r = corr.get((c[0], c[1], a))
        if r and c[2] == "N":
            c[3] = m(f"entidade vazia na publicação de {c[1]} ({r['registros_entidades']}), mas o ativo existe na distribuidora em outros anos ({r['presenca_outros_anos']}): dado ausente na fonte, não zero")
            c[4] |= 8
for a, linhas_br in br.items():
    for l in linhas_br:
        afet = sorted(d for (d, y, aa) in corr if aa == a and y == l[0])
        if afet:
            if l[2] in ("H", "T"): l[2] = "R"
            l[4] += len(afet); l[5] = sorted(set(l[5]) | set(afet))
            l[6] = m(motivos[l[6]] + f"; {len(afet)} distribuidora(s) com entidade vazia na publicação ficam fora da soma: total incompleto")

prov = {}
for r in rd(F4 / "MATRIZ_CONFORMIDADE_BDGD_ORDINARIA.csv"):
    prov.setdefault(f"{r['dist']}|{r['ano_alvo']}", []).append(dict(item=r["item_id"], titulo=r["titulo_catalogo"], versao=r["versao_titulo"], data_base=r["data_base_titulo"],
        inc=r["DAT_INC"], fnl=r["DAT_FNL"], ext=r["DAT_EXT"], intervalo=r["classe_intervalo"], extra=r["tag_extra"], sha=r["sha256_fonte"], uso=r["uso_na_serie"],
        decisao=r["decisao_humana_necessaria"]))

sinais = {}
for r in rd(F4 / "RANKING_ANOMALIAS_TEMPORAIS.csv"):
    sinais[f"{r['dist']}|{r['ativo']}|{r['ano_de']}|{r['ano_para']}"] = [NAT.get(r["categoria"], r["categoria"]), r["grau_confianca"], legivel(r["possivel_causa"]), int(r["prioridade"])]

pares = {}
for r in rd(F4 / "DECISOES_DUPLICATAS_13_PARES.csv"):
    k = f"{r['dist']}|{r['ano']}"
    if k not in pares:
        pares[k] = dict(grupo=r["grupo"], risco=r["risco"], ordem=int(r["ordem_impacto"]), ativos_dif=int(r["ativos_com_diferenca"]), recomendacao=legivel(r["recomendacao_tecnica"]),
                        A=dict(item=r["item_A"], versao=r["versao_A"]), B=dict(item=r["item_B"], versao=r["versao_B"]), decisao=r["DECISAO_HUMANA"], dif={})
    if r["dif_abs_B_menos_A"] not in ("", "0", "0.0"): pares[k]["dif"][r["ativo"]] = [num(r["valor_A"]), num(r["valor_B"])]

pontes = []
for r in rd(F4 / "PONTES_SUCESSOES_HISTORICAS.csv"):
    if r["ativo"] in ("consumidores", "todos") and r["ano"] in ("2022", ""):
        pontes.append(dict(evento=r["evento_id"], tipo=r["tipo_evento"], destino=r["dist_destino_2025"], origem=r["dist_origem"], status=r["status_ponte"], regra=r["regra_aplicada"],
                           prova=r["prova"], efetivacao=r["data_efetivacao"], fonte=r["fonte_oficial"]))
absorcao = {}
ab = F4 / "evidencias" / "absorcao_epb_ebo_2023.csv"
if ab.exists():
    for r in rd(ab): absorcao.setdefault(r["ativo"], [num(r["razao_2023_sobre_epb2022"]), num(r["razao_2023_sobre_soma"])])

sem_tuc = {}
for r in rd(HIS / "populacao_conceitos.csv"):
    q, s = num(r["quantidade"]), num(r["sem_tuc_mcpse"])
    if q and s is not None: sem_tuc[f"{r['dist']}|{r['ano']}|{r['conceito']}"] = round(s / q, 4)

doc = dict(versao="fase6-1", fonte="auditoria/fase4 + auditoria/fase6/CORRECOES_AUSENCIAS.csv", fontes={f: hashlib.sha256((F4 / f).read_bytes()).hexdigest() for f in FONTES},
           estados={"H": "homologado", "T": "completo técnico", "R": "apto com ressalvas", "P": "pendente de decisão", "B": "bloqueado", "N": "não disponível"},
           motivos=motivos, celulas=cel, brasil=br, painel=painel, proveniencia=prov, sinais=sinais, pares=pares, pontes=pontes, absorcao_epb=absorcao, sem_tuc=sem_tuc)
OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(f"{OUT.name}: {len(cel)} ativos, {sum(len(v) for v in cel.values())} celulas, {len(motivos)} motivos, {OUT.stat().st_size // 1024} KB")
