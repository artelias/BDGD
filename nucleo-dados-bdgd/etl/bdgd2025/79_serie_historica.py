"""R3 — serie anual 2022-2025 por ativo fisico: publicacao original e perimetro comparavel 2025.

Entradas: 2025 = pacote homologado (ativos_totais.csv); 2022-2024 = conceitos_r3.json do 78_conceitos_historico.py
(mesma regra de 2025) + inventario/checkpoints do ETL historico. Nada e preenchido, interpolado ou estimado.

Estado de cada celula DIST x ano x ativo:
  validado            publicacao unica da competencia, BASE conferida, reconciliacao sem falha, mesma regra 2025
  ausente             ativo inexistente no GDB da competencia (N/D, nunca zero)
  campo_ausente       campo exigido pelo recorte nao existe no layout do ano
  bloqueado           valor nulo/ nao homologavel
  revisao_pendente    mais de uma publicacao valida para DIST/ano (nao se escolhe automaticamente)
  nao_processado      publicacao existe, ETL historico ainda nao concluiu
  competencia_divergente  arquivo publicado como do ano, mas BASE.DAT_FNL de outra competencia
  sem_publicacao      ANEEL nao publicou BDGD daquela DIST na competencia
Comparabilidade (coluna propria): quebra_classificacao quando a parcela sem TUC do MCPSE no conceito muda mais de 10 p.p.
entre anos consecutivos (reclassificacao patrimonial nao e crescimento fisico).
Perimetro 2025: predecessoras somadas a sucessora SOMENTE com prova de disjuncao (conjuntos CONJ sem intersecao) e
evidencia societaria documentada; sem prova -> pendente.
Saida: output-historico/2022-2025/ (CSV + manifest) e web/public/data/historico/serie.json."""
import csv, json, pathlib, sys, hashlib, datetime
from decimal import Decimal
import duckdb

R = pathlib.Path("D:/NUCLEO_BDGD_2025"); H = pathlib.Path("D:/NUCLEO_BDGD_2022_2024")
PKG = R / "output-publicavel" / "2025-12-31"
OUT = R / "output-historico" / "2022-2025"
WEB = R / "repo" / "nucleo-dados-bdgd" / "web" / "public" / "data" / "historico"
CFG = json.loads((pathlib.Path(__file__).parent / "config" / "conceitos_2025.json").read_text(encoding="utf-8"))
ANOS = [2022, 2023, 2024, 2025]
SEM_TUC = {"000", "00", "0", "SEM_CODIGO", "NA"}
LIMIAR_QUEBRA = 0.10
# eventos societarios documentados (fontes em docs/HARMONIZACAO-SUCESSAO-2022-2025.md e R3-MOTOR-EXPANSAO-ELETRICA-SUCESSOES.md)
EVENTOS = [
    {"evento_id": "EPB_EBO_2023", "tipo_evento": "incorporacao", "dist_destino_2025": 6600, "dist_origem": 6611, "data_autorizacao": "2022-09-13", "data_efetivacao": "2023-04-30",
     "fonte_oficial": "https://auniao.pb.gov.br/servicos/editais-balancos-e-atas-na-integra/energisa-borborema-27-05-23-cdepc.pdf ; https://www2.aneel.gov.br/cedoc/areh20233250_1.pdf"},
    {"evento_id": "EMR_ENF_2022", "tipo_evento": "incorporacao", "dist_destino_2025": 6585, "dist_origem": 6612, "data_autorizacao": "", "data_efetivacao": "2022-11-30",
     "fonte_oficial": "https://www.abrasca.org.br/noticias/sia-cia-1627-energisa-reorganizacao-societaria-de-controladas"},
]
rd = lambda p: list(csv.DictReader(open(p, encoding="utf-8")))


def num(v):
    return None if v in ("", None) else (int(v) if str(v).lstrip("-").isdigit() else float(v))


def main():
    ativos = CFG["ativos"]
    inv = rd(H / "inventario" / "inventario_historico_2022_2024.csv")
    nomes = {int(x["dist"]): x["empresa"] for x in inv}
    for d in rd(PKG / "distribuidoras.csv"): nomes[int(d["dist"])] = d["nome"]
    cel, pop, itens_ok, multiplas = {}, {}, {}, []
    # ---- 2022-2024: estado por DIST/ano a partir do inventario, checkpoints e conceitos_r3
    for ano in ANOS[:-1]:
        pubs = {}
        for x in inv:
            if int(x["ano"]) == ano and x["status"] != "ausente_catalogo": pubs.setdefault(int(x["dist"]), []).append(x["item_id"])
        ausentes = {int(x["dist"]) for x in inv if int(x["ano"]) == ano and x["status"] == "ausente_catalogo"}
        for d in sorted(set(pubs) | ausentes):
            validos, divergentes, pendentes = [], [], []
            for it in pubs.get(d, []):
                pasta = H / "proc" / str(ano) / str(d) / it
                if (pasta / "failure.json").exists() and "DAT_FNL" in (pasta / "failure.json").read_text(encoding="utf-8"): divergentes.append(it); continue
                if (pasta / "conceitos_r3.json").exists(): validos.append(it)
                else: pendentes.append(it)
            base = {"item_id": "", "source_sha256": "", "motivo": ""}
            equivalente = None
            if len(pubs.get(d, [])) > 1 and len(validos) <= 1:
                # par ainda incompleto (item em processamento) ou com item de outra competencia: registrado, sem decisao
                multiplas.append({"ano": ano, "dist": d, "itens": "+".join(sorted(validos)), "pendentes_ou_falhas": "+".join(pendentes + divergentes), "sha256_distintos": "",
                                  "ativos_divergentes": "", "diferencas_integrais": "comparacao integral nao executada",
                                  "decisao": "aguarda processamento de todos os itens" if pendentes else "demais itens com BASE.DAT_FNL de outra competencia: item valido unico"})
            if len(validos) > 1:
                js = {it: json.loads((H / "proc" / str(ano) / str(d) / it / "conceitos_r3.json").read_text(encoding="utf-8")) for it in validos}
                shas = {j["source_sha256"] for j in js.values()}
                difs = [a_["id"] for a_ in ativos if len({json.dumps(j["ativos"][a_["id"]]["valor"]) for j in js.values()}) > 1]
                # equivalencia integral comprovada por equivalencia_duplicatas.py (SHA-256 igual, ou registros, atributos, TUC, DDA,
                # vinculos e geometria identicos); totais iguais nos ativos NAO bastam (decisao do responsavel, 24/10/2026)
                eqf = H / "proc" / str(ano) / str(d) / "equivalencia_duplicatas.json"
                eqj = json.loads(eqf.read_text(encoding="utf-8")) if eqf.exists() else None
                ok_eq = bool(eqj and eqj.get("equivalente") and sorted(eqj.get("itens", [])) == sorted(validos))
                crit = eqj["criterio"] if ok_eq else ""
                multiplas.append({"ano": ano, "dist": d, "itens": "+".join(sorted(validos)), "pendentes_ou_falhas": "+".join(pendentes + divergentes), "sha256_distintos": len(shas),
                                  "ativos_divergentes": ",".join(difs), "diferencas_integrais": "; ".join((eqj or {}).get("diferencas", [])[:12]) if eqj else "comparacao integral nao executada",
                                  "decisao": f"equivalentes: {crit}" if crit else "revisao humana: equivalencia integral nao comprovada"})
                if crit and not pendentes: equivalente = sorted(validos)[0]
                if pendentes: base["motivo"] = "publicacoes multiplas: item restante em processamento"
            if not pubs.get(d): st = "sem_publicacao"
            elif len(pubs[d]) > 1 and pendentes:
                st = "nao_processado"; base["motivo"] = "publicacoes multiplas: comparacao aguarda o processamento de todos os itens"
            elif len(validos) > 1 and not equivalente:
                st = "revisao_pendente" if not pendentes else "nao_processado"
                base["motivo"] = base["motivo"] or f"{len(validos)} publicacoes validas sem equivalencia integral comprovada: decisao humana"
            elif len(validos) == 1 or equivalente:
                if equivalente: validos = [equivalente]
                j = json.loads((H / "proc" / str(ano) / str(d) / validos[0] / "conceitos_r3.json").read_text(encoding="utf-8"))
                itens_ok[(d, ano)] = j
                for cid, p in j["populacao"].items(): pop[(d, ano, cid)] = p
                for a in ativos:
                    x = j["ativos"][a["id"]]
                    cel[(d, ano, a["id"])] = {"valor": x["valor"], "status": x["status"], "motivo": x["motivo"], "item_id": validos[0], "source_sha256": j["source_sha256"]}
                continue
            elif pendentes: st = "nao_processado"; base["motivo"] = "ETL historico em andamento"
            else: st = "competencia_divergente"; base["motivo"] = "arquivo publicado com BASE.DAT_FNL de outra competencia"
            for a in ativos: cel[(d, ano, a["id"])] = {"valor": None, "status": st, **base}
    # ---- 2025: pacote homologado
    for r in rd(PKG / "ativos_totais.csv"):
        a = next(x for x in ativos if x["id"] == r["ativo"])
        if r["medida"] != a["medida"]: continue
        st = {"aprovado": "validado", "alerta": "validado", "nao_aplicavel": "ausente", "bloqueado": "bloqueado"}.get(r["status"], r["status"])
        cel[(int(r["dist"]), 2025, r["ativo"])] = {"valor": num(r["valor"]), "status": st, "motivo": r["motivo"], "item_id": "pacote-2025", "source_sha256": ""}
    cub = {}
    with open(PKG / "conceitos" / "cubos.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["cubo"] != "principal": continue
            dims = CFG["conceitos"][r["conceito"]]["cubos"]["principal"]
            k = json.loads(r["chave"]); q = int(r["quantidade"] or 0)
            p = cub.setdefault((int(r["dist"]), 2025, r["conceito"]), {"quantidade": 0, "sem_tuc_mcpse": 0 if "tipo" in dims else None})
            p["quantidade"] += q
            if "tipo" in dims and k[dims.index("tipo")] in SEM_TUC: p["sem_tuc_mcpse"] += q
    pop.update(cub)
    # ---- comparabilidade: quebra de classificacao patrimonial entre anos consecutivos
    comp = {}
    for a in ativos:
        if "tipo" not in a["filtro"]: continue
        for d in {k[0] for k in cel}:
            prev = None
            for ano in ANOS:
                p = pop.get((d, ano, a["conceito"]))
                if not p or p.get("sem_tuc_mcpse") is None or not p["quantidade"]: prev = None; continue
                share = p["sem_tuc_mcpse"] / p["quantidade"]
                if prev is not None and abs(share - prev) > LIMIAR_QUEBRA: comp[(d, ano, a["id"])] = f"parcela sem TUC do MCPSE mudou de {prev:.0%} para {share:.0%}"
                prev = share
    # ---- ponte de perimetro 2025 com prova de disjuncao por conjuntos
    con = duckdb.connect()
    def conjs(d, ano):
        if ano == 2025: pq = R / "staging_parquet" / f"DIST={d}" / "DATA_BASE=2025-12-31" / "entidade=CONJ" / "part-0.parquet"
        else:
            j = itens_ok.get((d, ano)); pq = H / "parquet" / str(ano) / str(d) / j["item_id"] / "CONJ.parquet" if j else None
        if not pq or not pq.exists(): return None
        return {str(r[0]).strip() for r in con.execute(f"SELECT DISTINCT COD_ID FROM read_parquet('{pq.as_posix()}')").fetchall()}
    ponte, qa_suc = [], []
    destinos = sorted({k[0] for k in cel if k[1] == 2025})
    for d in destinos:
        for ano in ANOS:
            ponte.append({"ano_base": ano, "dist_origem": d, "dist_destino_2025": d, "evento_id": "", "criterio_inclusao": "mesma DIST", "status_qualidade": "validado", "prova_disjuncao": "n/a"})
    for ev in EVENTOS:
        for ano in ANOS[:-1]:
            o, s = conjs(ev["dist_origem"], ano), conjs(ev["dist_destino_2025"], ano)
            prox = conjs(ev["dist_destino_2025"], ano + 1)
            if o is None:
                continue
            inter = len(o & s) if s is not None else None
            absorvida = prox is not None and len(o & prox) / max(1, len(o)) >= 0.9
            contida = s is not None and len(o) > 0 and inter == len(o)
            ok = s is not None and inter == 0 and absorvida
            # origem ja contida no destino no mesmo ano: o destino ja representa o perimetro; somar duplicaria
            st = "ja_incluida" if contida else ("validado" if ok else "pendente")
            prova = f"CONJ origem={len(o)}, destino={len(s) if s is not None else 'N/D'}, intersecao={inter}; conjuntos da origem presentes no destino em {ano + 1}: {len(o & prox) if prox is not None else 'N/D'}"
            ponte.append({"ano_base": ano, "dist_origem": ev["dist_origem"], "dist_destino_2025": ev["dist_destino_2025"], "evento_id": ev["evento_id"],
                          "criterio_inclusao": "conjuntos da predecessora ja contidos no destino: nao somar" if st == "ja_incluida" else "predecessora incorporada; areas disjuntas por conjunto e absorcao confirmada no ano seguinte",
                          "status_qualidade": st, "prova_disjuncao": prova})
            qa_suc.append({"evento_id": ev["evento_id"], "ano_base": ano, "dist_destino_2025": ev["dist_destino_2025"], "dist_origem": ev["dist_origem"], "conj_origem": len(o),
                           "conj_destino": len(s) if s is not None else "", "intersecao": inter if inter is not None else "", "absorcao_ano_seguinte": absorvida, "status": st})
    # ---- series
    orig, perim = [], []
    for (d, ano, aid), c in sorted(cel.items()):
        a = next(x for x in ativos if x["id"] == aid)
        orig.append({"dist": d, "empresa": nomes.get(d, ""), "ano": ano, "data_base": f"{ano}-12-31", "ativo": aid, "conceito": a["conceito"], "medida": a["medida"],
                     "unidade": {"extensao_km": "km"}.get(a["medida"], "itens"), "valor": c["valor"] if c["status"] == "validado" else "", "status": c["status"], "motivo": c["motivo"],
                     "comparabilidade": "quebra_classificacao" if (d, ano, aid) in comp else "comparavel", "motivo_comparabilidade": comp.get((d, ano, aid), ""),
                     "item_id": c["item_id"], "source_sha256": c["source_sha256"], "versao_regra": CFG["versao"]})
    for d in destinos:
        for ano in ANOS:
            origens = [p for p in ponte if p["dist_destino_2025"] == d and p["ano_base"] == ano and (p["dist_origem"] == d or p["evento_id"])]
            pend = [p for p in origens if p["status_qualidade"] not in ("validado", "ja_incluida")]
            for a in ativos:
                partes = [cel.get((p["dist_origem"], ano, a["id"])) for p in origens if p["status_qualidade"] == "validado"]
                partes = [x for x in partes if x]
                sts = {x["status"] for x in partes}
                if pend: st, v, mo = "pendente", None, "predecessora sem prova de disjuncao: " + ", ".join(str(p["dist_origem"]) for p in pend)
                elif not partes: st, v, mo = "sem_publicacao", None, ""
                elif sts == {"validado"}:
                    vals = [x["valor"] for x in partes]
                    v = sum(Decimal(str(x)) for x in vals) if vals else None; st, mo = "validado", ""
                elif "validado" in sts and sts <= {"validado", "ausente"}:
                    v = sum(Decimal(str(x["valor"])) for x in partes if x["status"] == "validado"); st, mo = "validado", "parte das origens sem esse ativo"
                else: st, v, mo = sorted(sts - {"validado"})[0], None, "; ".join(sorted({x["motivo"] for x in partes if x["motivo"]}))
                perim.append({"dist_destino_2025": d, "empresa": nomes.get(d, ""), "ano_base": ano, "ativo": a["id"], "medida": a["medida"], "valor": "" if v is None else str(v), "status": st,
                              "origens_incluidas": "+".join(str(p["dist_origem"]) for p in origens if p["status_qualidade"] == "validado"),
                              "comparabilidade": "quebra_perimetro" if any(p["evento_id"] for p in origens) else ("quebra_classificacao" if (d, ano, a["id"]) in comp else "comparavel"),
                              "perimetro_referencia": 2025, "modelo": "consolidado_comparavel", "motivo": mo})
    # ---- cobertura por ano e manifesto (completo_tecnico so com todas as elegiveis validadas; homologado exige decisao humana)
    cob = []
    for ano in ANOS:
        ds_ano = {k[0] for k in cel if k[1] == ano and cel[k]["status"] not in ("sem_publicacao",)}
        val = {k[0] for k in cel if k[1] == ano and cel[k]["status"] in ("validado", "ausente", "campo_ausente", "bloqueado")}
        pend = {k[0] for k in cel if k[1] == ano and cel[k]["status"] in ("nao_processado", "revisao_pendente")}
        div = {k[0] for k in cel if k[1] == ano and cel[k]["status"] == "competencia_divergente"}
        cob.append({"ano": ano, "publicadas": len(ds_ano), "validadas": len(val), "pendentes": len(pend), "competencia_divergente": len(div),
                    "status_ano": "homologado" if ano == 2025 else ("completo_tecnico" if not pend and val else "parcial")})  # completo_tecnico: validacao automatica, sem homologacao humana
    OUT.mkdir(parents=True, exist_ok=True)
    def w(nome, rows):
        cols = list(rows[0].keys()) if rows else []
        with open(OUT / nome, "w", newline="", encoding="utf-8") as f:
            wr = csv.DictWriter(f, cols, lineterminator="\n"); wr.writeheader(); wr.writerows(rows)
    w("serie_ativos_original.csv", orig); w("serie_ativos_perimetro_2025.csv", perim); w("ponte_perimetro_2025.csv", ponte)
    w("eventos_sucessao.csv", EVENTOS); w("qa_sucessao.csv", qa_suc); w("cobertura_por_ano.csv", cob)
    w("qa_publicacoes_multiplas.csv", multiplas)
    w("populacao_conceitos.csv", [{"dist": d, "ano": a, "conceito": c, **p} for (d, a, c), p in sorted(pop.items())])
    man = {"escopo": "BDGD 2022-2025, mesma regra de ativos de 2025", "versao_regra": CFG["versao"], "gerado_em": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
           "cobertura": cob, "estados": ["validado", "ausente", "campo_ausente", "bloqueado", "revisao_pendente", "nao_processado", "competencia_divergente", "sem_publicacao"],
           "regras": {"valores": "somente celulas validado tem valor; demais ficam vazias (N/D), nunca zero", "brasil": "total nacional so quando todas as publicacoes do ano estao validadas",
                      "perimetro": "predecessoras somadas apenas com prova de disjuncao por CONJ e absorcao no ano seguinte", "quebra_classificacao": f"variacao > {LIMIAR_QUEBRA:.0%} da parcela sem TUC"},
           "privacidade": "somente agregados por DIST/ano/ativo; nenhum identificador individual",
           "checksums": {}}
    for p in sorted(OUT.glob("*.csv")): man["checksums"][p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    (OUT / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
    # ---- asset web compacto
    WEB.mkdir(parents=True, exist_ok=True)
    ST = {"validado": "v", "ausente": "a", "campo_ausente": "c", "bloqueado": "b", "revisao_pendente": "r", "nao_processado": "p", "competencia_divergente": "d", "sem_publicacao": "s", "pendente": "r"}
    def serie(rows, kd, ka):
        o = {}
        for r in rows:
            o.setdefault(r["ativo"], []).append([int(r[kd]), int(r[ka]), num(r["valor"]), ST.get(r["status"], r["status"]), 1 if r["comparabilidade"] != "comparavel" else 0])
        return o
    web = {"anos": ANOS, "gerado_em": man["gerado_em"], "versao_regra": CFG["versao"], "cobertura": cob, "nomes": {str(k): v for k, v in nomes.items()},
           "original": serie(orig, "dist", "ano"), "perimetro": serie(perim, "dist_destino_2025", "ano_base"),
           "eventos": EVENTOS, "ponte": [p for p in ponte if p["evento_id"]], "notas": {f"{r['dist']}|{r['ano']}|{r['ativo']}": r["motivo_comparabilidade"] or r["motivo"] for r in orig if r["motivo_comparabilidade"] or (r["status"] != "validado" and r["motivo"])}}
    (WEB / "serie.json").write_text(json.dumps(web, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({"celulas": len(orig), "cobertura": cob, "ponte_eventos": qa_suc}, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
