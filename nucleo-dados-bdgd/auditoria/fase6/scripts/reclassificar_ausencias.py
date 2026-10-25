"""Fase 6 — reclassificação das células 'ativo não aplicável' com evidência (somente leitura).
Para cada célula 'ausente' da série: registros das entidades de origem no Parquet da publicação usada e presença do
ativo (valor > 0 validado) em outros anos da mesma DIST.
  camada/entidade inexistente ou vazia e ativo nunca presente na DIST  -> ATIVO_NAO_APLICAVEL (nao_aplicavel)
  entidade vazia na publicação, mas ativo presente em outro ano          -> ENTIDADE_VAZIA_NA_ORIGEM (ausente: dado faltante, não zero)
  entidade com registros, mas nenhum do tipo, e ativo presente em outro ano -> TIPO_SEM_REGISTROS_NA_PUBLICACAO (ausente)
Saída: auditoria-fase6/CORRECOES_AUSENCIAS.csv"""
import collections, csv, pathlib
import duckdb

H = pathlib.Path("D:/NUCLEO_BDGD_2022_2024"); R = pathlib.Path("D:/NUCLEO_BDGD_2025"); A6 = R / "auditoria-fase6"
ENT = {"consumidores": ["UCBT", "UCMT", "UCAT"], "geradores": ["UGBT", "UGMT", "UGAT"], "iluminacao": ["PIP"], "rede_bt": ["SSDBT"], "rede_mt": ["SSDMT"], "rede_at": ["SSDAT"],
       "ramais": ["RAMLIG"], "trafo_dist": ["EQTRMT"], "trafo_forca": ["EQTRAT"], "trafo_medida": ["EQTRM"], "chaves": ["EQSE"], "seccionalizadores": ["EQSE"], "disjuntores": ["EQSE"],
       "religadores": ["EQSE"], "reguladores": ["EQRE"], "bancos_capacitores": ["EQCR"], "reatores": ["EQCR"], "medidores": ["EQME"], "postes": ["PONNOT"], "torres": ["PONNOT"],
       "subestacoes": ["SUB"], "alimentadores": ["CTMT"], "circuitos_at": ["CTAT"], "conjuntos": ["CONJ"], "barramentos": ["BAR"]}
con = duckdb.connect(); con.execute("SET memory_limit='512MB'; SET threads=2")
S = {(int(r["ano"]), r["dist"], r["ativo"]): r for r in csv.DictReader(open(R / "output-historico/2022-2025/serie_ativos_original.csv", encoding="utf-8-sig"))}
item25 = {r["dist"]: r["item_id"] for r in csv.DictReader(open(R / "inventario/inventario_2025.csv", encoding="utf-8")) if r["item_id"]}


def arquivos(ano, dist, item, ent):
    if ano == 2025:
        b = R / "staging_parquet" / f"DIST={dist}" / "DATA_BASE=2025-12-31" / f"entidade={ent}"
        return sorted(p.as_posix() for p in b.glob("*.parquet")) if b.exists() else None
    p = H / "parquet" / str(ano) / dist / item / f"{ent}.parquet"
    return [p.as_posix()] if p.exists() else None


linhas = []
for (y, d, a), r in sorted(S.items()):
    if r["status"] != "ausente": continue
    item = r["item_id"] if r["item_id"] and r["item_id"] != "pacote-2025" else item25.get(d, "")
    regs = {}
    for e in ENT[a]:
        f = arquivos(y, d, item, e)
        regs[e] = None if f is None else con.execute(f"SELECT count(*) FROM read_parquet({f})").fetchone()[0]
    outros = [(yy, S[(yy, d, a)]["valor"]) for yy in (2022, 2023, 2024, 2025) if yy != y and (yy, d, a) in S and S[(yy, d, a)]["status"] == "validado" and S[(yy, d, a)]["valor"] not in ("", "0", "0.0")
              and float(S[(yy, d, a)]["valor"]) > 0]
    vazio = all((v or 0) == 0 for v in regs.values())
    if outros and vazio: cls = "ENTIDADE_VAZIA_NA_ORIGEM"
    elif outros: cls = "TIPO_SEM_REGISTROS_NA_PUBLICACAO"
    else: cls = "ATIVO_NAO_APLICAVEL"
    linhas.append(dict(ano=y, dist=d, empresa=r["empresa"], ativo=a, item_id=item, registros_entidades=";".join(f"{e}={'sem_arquivo' if v is None else v}" for e, v in regs.items()),
                       presenca_outros_anos=";".join(f"{yy}={v}" for yy, v in outros) or "nenhuma", classificacao_anterior="ATIVO_NAO_APLICAVEL", classificacao=cls,
                       estado_contrato="nao_aplicavel" if cls == "ATIVO_NAO_APLICAVEL" else "ausente", motivo_original=r["motivo"]))
with open(A6 / "CORRECOES_AUSENCIAS.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, list(linhas[0]), lineterminator="\n"); w.writeheader(); w.writerows(linhas)
c = collections.Counter((l["ano"], l["classificacao"]) for l in linhas)
for k in sorted(c): print(k, c[k])
print([(l["ano"], l["empresa"], l["ativo"], l["registros_entidades"], l["presenca_outros_anos"][:30]) for l in linhas if l["classificacao"] != "ATIVO_NAO_APLICAVEL"][:30])
