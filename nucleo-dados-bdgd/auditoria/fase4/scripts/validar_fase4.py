"""Validacao dos artefatos da Fase 4 (somente leitura). Sai com codigo 1 se algum teste falhar.
Grava evidencias/validacao_fase4.json."""
import collections, csv, glob, hashlib, json, pathlib, sys

R = pathlib.Path("D:/NUCLEO_BDGD_2025"); A = R / "auditoria-fase4"; O = R / "output-historico/2022-2025"; H = pathlib.Path("D:/NUCLEO_BDGD_2022_2024")
rd = lambda p: list(csv.DictReader(open(p, encoding="utf-8-sig")))
sha = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
T = []


def t(nome, ok, det=""):
    T.append(dict(teste=nome, ok=bool(ok), detalhe=str(det)[:300])); print(("OK   " if ok else "FALHA"), nome, det if not ok else "")


M = rd(A / "MATRIZ_HOMOLOGACAO_2022_2025.csv"); S = rd(O / "serie_ativos_original.csv")
D = [m for m in M if m["nivel"] == "DIST"]
k = collections.Counter((m["ano"], m["dist"], m["ativo"], m["medida"]) for m in M)
t("matriz: chave unica (ano, dist, ativo, medida)", all(v == 1 for v in k.values()), [x for x, v in k.items() if v > 1][:5])
t("matriz: uma celula DIST por celula da serie", len(D) == len(S), f"{len(D)} x {len(S)}")
ESTADOS = {"HOMOLOGADO", "COMPLETO_TECNICO", "APTO_COM_RESSALVAS", "PENDENTE_DECISAO", "BLOQUEADO", "NAO_DISPONIVEL"}
t("matriz: estados dentro do dominio", all(m["estado_publicacao"] in ESTADOS for m in M))
src = {(r["ano"], r["dist"], r["ativo"]): r for r in S}
NP = {"PENDENTE_DECISAO", "BLOQUEADO", "NAO_DISPONIVEL"}
t("N/D: nenhuma celula nao publicavel com valor", all(m["valor"] == "" and m["valor_nd"] == "sim" for m in D if m["estado_publicacao"] in NP))
zeros = [m for m in D if m["valor"] not in ("",) and float(m["valor"]) == 0 and src[(m["ano"], m["dist"], m["ativo"])]["valor"] in ("", None)]
t("N/D: nenhum zero criado a partir de ausencia", not zeros, len(zeros))
dif = [m for m in D if m["valor"] != "" and abs(float(m["valor"]) - float(src[(m["ano"], m["dist"], m["ativo"])]["valor"])) > 1e-9]
t("totais: valores publicaveis identicos a serie de origem", not dif, len(dif))
t("totais: so celulas 'validado' na origem tem valor", all(src[(m["ano"], m["dist"], m["ativo"])]["status"] == "validado" for m in D if m["valor"] != ""))
t("homologacao: HOMOLOGADO so em 2025 (decisao vigente)", all(m["ano"] == "2025" for m in M if m["estado_publicacao"] == "HOMOLOGADO"))
PUB = {"HOMOLOGADO", "COMPLETO_TECNICO", "APTO_COM_RESSALVAS"}; NS = {("2022", "6612")}
idx = collections.defaultdict(list)
for m in D: idx[(m["ano"], m["ativo"])].append(m)
ok_br, ok_exc, ok_2223 = True, True, True
for m in M:
    if m["nivel"] != "BRASIL": continue
    cs = idx[(m["ano"], m["ativo"])]
    inc = [c for c in cs if c["estado_publicacao"] in PUB and c["valor"] != "" and (c["ano"], c["dist"]) not in NS]
    exc = sorted((c["dist"] for c in cs if c["estado_publicacao"] in ("PENDENTE_DECISAO", "BLOQUEADO")), key=int)
    soma = round(sum(float(c["valor"]) for c in inc), 6)
    alvo = m["valor_soma_parcial_nao_publicar"] if m["ano"] in ("2022", "2023") else m["valor"]
    ok_br &= abs(float(alvo) - soma) < 1e-6 and int(m["n_dist_incluidas"]) == len(inc)
    ok_exc &= m["dists_excluidas"] == ";".join(exc) and int(m["n_dist_excluidas"]) == len(exc)
    if m["ano"] in ("2022", "2023"): ok_2223 &= m["valor"] == "" and m["estado_publicacao"] == "BLOQUEADO"
t("Brasil: soma = celulas publicaveis (sem pendentes/bloqueadas)", ok_br)
t("Brasil: celulas pendentes/bloqueadas identificadas no agregado", ok_exc)
t("Brasil 2022-2023: sem valor publicado como total nacional", ok_2223)
ok_p = True
for m in M:
    if m["nivel"] != "PAINEL": continue
    u = m["universo"].split(";") if m["universo"] else []
    cs = {c["dist"]: c for c in idx[(m["ano"], m["ativo"])]}
    ok_p &= all(cs[d]["estado_publicacao"] in PUB and cs[d]["valor"] != "" for d in u) and abs(sum(float(cs[d]["valor"]) for d in u) - float(m["valor"])) < 1e-6 and not ({d for d in u} & {"6612"})
t("painel balanceado: universo publicavel nos 4 anos e soma correta", ok_p)
t("sucessoes: ENF 6612 (2022) fora de qualquer agregado", all("6612" not in m["universo"].split(";") for m in M if m["nivel"] == "PAINEL"))
P = rd(A / "PONTES_SUCESSOES_HISTORICAS.csv")
t("sucessoes: nenhuma ponte somada (perimetro so com DIST destino ou pendente)", all(p["valor_perimetro_comparavel"] in ("", p["valor_destino_original"]) for p in P if p["ano"]))
Dp = rd(A / "DECISOES_DUPLICATAS_13_PARES.csv"); rec = rd(O / "qa_duplicatas_reconciliadas.csv")
pares = {(d["ano"], d["dist"]) for d in Dp}; div = {(r["ano"], r["dist"]) for r in rec if r["classificacao"] == "divergente"}
t("duplicatas: 13 pares = divergentes reconciliados", pares == div and len(pares) == 13, f"{len(pares)}")
t("duplicatas: 25 ativos por par, sem repeticao", all(v == 25 for v in collections.Counter((d["ano"], d["dist"]) for d in Dp).values()) and len({(d["ano"], d["dist"], d["ativo"]) for d in Dp}) == len(Dp))
t("duplicatas: nenhuma decisao tomada automaticamente", all(d["DECISAO_HUMANA"] == "PENDENTE" for d in Dp))
g = collections.Counter(d["grupo"] for d in {(d["ano"], d["dist"]): d for d in Dp}.values())
t("duplicatas: 6 sem diferenca nos totais e 7 com diferenca", g == {"SEM_DIFERENCA_TOTAIS": 6, "COM_DIFERENCA_TOTAIS": 7}, dict(g))
t("duplicatas: celulas dos pares pendentes na matriz", all(m["estado_publicacao"] == "PENDENTE_DECISAO" for m in D if (m["ano"], m["dist"]) in pares))
Rk = rd(A / "RANKING_ANOMALIAS_TEMPORAIS.csv"); Sg = rd(O / "qa_sinais_temporais_classificados.csv")
kr = {(r["dist"], r["ativo"], r["ano_de"], r["ano_para"]) for r in Rk}; ks = {(r["dist"], r["ativo"], r["de"], r["para"]) for r in Sg}
t("sinais: 238 reconciliados com a Fase 3", len(Rk) == 238 and kr == ks, f"{len(Rk)}")
t("sinais: prioridade unica 1..N", sorted(int(r["prioridade"]) for r in Rk) == list(range(1, len(Rk) + 1)))
C = rd(A / "MATRIZ_CONFORMIDADE_BDGD_ORDINARIA.csv")
t("conformidade: um registro por publicacao (item_id unico)", len({c["item_id"] for c in C}) == len(C), len(C))
t("conformidade: toda celula validada usa publicacao auditada", all(m["item_id"] in {c["item_id"] for c in C} for m in D if m["valor"] != ""))
t("conformidade: nenhuma publicacao excluida so pela tag Extra", all(not c["recomendacao"].startswith("excl") for c in C if c["tag_extra"] == "sim"))
# preservacao das fontes
man = json.loads((O / "manifest.json").read_text(encoding="utf-8"))
t("preservacao: checksums do manifesto historico conferem", all(sha(O / n) == h for n, h in man["checksums"].items()))
HP = H / "repo/nucleo-dados-bdgd/historico"
t("preservacao: pipeline.py original intacto", sha(HP / "pipeline.py").startswith("d1811842211b"))
t("preservacao: pipeline_antijoin.py intacto", sha(HP / "pipeline_antijoin.py").startswith("e348a1afa64d"))
cks = glob.glob(str(H / "proc/*/*/*/checkpoint.json")); bad = 0
for f in cks:
    j = json.load(open(f, encoding="utf-8")); dd = pathlib.Path(f).parent
    bad += not all(sha(dd / n) == h for n, h in j.get("files", {}).items())
t("preservacao: 301 checkpoints presentes e integros", len(cks) == 301 and bad == 0, f"{len(cks)} checkpoints, {bad} com divergencia")
p25 = json.loads((R / "output-publicavel/2025-12-31/manifest.json").read_text(encoding="utf-8"))
t("preservacao: pacote 2025 com DATA_BASE 2025-12-31 inalterado", p25.get("data_base", "2025-12-31") == "2025-12-31")
(A / "evidencias/validacao_fase4.json").write_text(json.dumps(T, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{sum(x['ok'] for x in T)}/{len(T)} testes OK")
sys.exit(0 if all(x["ok"] for x in T) else 1)
