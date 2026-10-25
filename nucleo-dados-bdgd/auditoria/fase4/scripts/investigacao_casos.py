"""Fase 4 — investigacao somente leitura dos casos prioritarios (Parquet ja gerado; nenhum GDB reprocessado).
Saida: auditoria-fase4/evidencias/investigacao_casos.json"""
import csv, json, pathlib
import duckdb

H = pathlib.Path("D:/NUCLEO_BDGD_2022_2024"); S25 = pathlib.Path("D:/NUCLEO_BDGD_2025/staging_parquet")
OUT = pathlib.Path("D:/NUCLEO_BDGD_2025/auditoria-fase4/evidencias"); OUT.mkdir(parents=True, exist_ok=True)
con = duckdb.connect(); con.execute("SET memory_limit='768MB'; SET threads=2; SET preserve_insertion_order=false")
inv = list(csv.DictReader(open(H / "inventario/inventario_historico_2022_2024.csv", encoding="utf-8")))


def arquivo(ano, dist, ent):
    """Parquet da entidade para o item validado (candidato) do ano; 2025 vem do staging do pacote homologado."""
    if ano == 2025:
        b = S25 / f"DIST={dist}" / "DATA_BASE=2025-12-31" / f"entidade={ent}"
        f = sorted(p.as_posix() for p in b.glob("*.parquet")); return f or None
    for r in inv:
        if r["ano"] == str(ano) and r["dist"] == str(dist) and r["status"] == "candidato":
            p = H / "parquet" / str(ano) / str(dist) / r["item_id"] / f"{ent}.parquet"
            return [p.as_posix()] if p.exists() else None
    return None


def q(sql):
    return con.execute(sql).fetchall()


res = {}
# 1) situacao das UCs (SIT_ATIV) por ano: Enel CE (39), Equatorial GO (6072), Coopera (5370)
for d in (39, 6072, 5370):
    r = {}
    for a in (2022, 2023, 2024, 2025):
        for e in ("UCBT", "UCMT", "UCAT"):
            f = arquivo(a, d, e)
            r[f"{a}_{e}"] = None if not f else {k: n for k, n in q(f"SELECT coalesce(CAST(SIT_ATIV AS VARCHAR), 'NULO'), count(*) FROM read_parquet({f}) GROUP BY 1")}
    res[f"sit_ativ_{d}"] = r
# 1b) Enel CE: identidade das UCBT 2024 x 2025 (quantas UCs ativas em 2025 eram DS em 2024)
f24, f25 = arquivo(2024, 39, "UCBT"), arquivo(2025, 39, "UCBT")
if f24 and f25:
    res["enel_ce_transicao_ucbt_2024_2025"] = [list(x) for x in q(
        f"SELECT coalesce(a.SIT_ATIV,'AUSENTE_2024') s24, coalesce(b.SIT_ATIV,'AUSENTE_2025') s25, count(*) FROM "
        f"(SELECT DISTINCT CAST(COD_ID AS VARCHAR) k, CAST(SIT_ATIV AS VARCHAR) SIT_ATIV FROM read_parquet({f24})) a FULL JOIN "
        f"(SELECT DISTINCT CAST(COD_ID AS VARCHAR) k, CAST(SIT_ATIV AS VARCHAR) SIT_ATIV FROM read_parquet({f25})) b ON a.k = b.k GROUP BY 1, 2 ORDER BY 3 DESC")]
# 2) Cooperzem (5374): iluminacao publica (PIP) por ano e persistencia de COD_ID entre anos
pip = {a: arquivo(a, 5374, "PIP") for a in (2022, 2023, 2024, 2025)}
res["cooperzem_pip_registros"] = {a: (q(f"SELECT count(*), count(DISTINCT COD_ID) FROM read_parquet({f})")[0] if f else None) for a, f in pip.items()}
res["cooperzem_pip_persistencia"] = {}
for a, b in ((2022, 2023), (2023, 2024), (2024, 2025), (2023, 2025)):
    if pip[a] and pip[b]:
        res["cooperzem_pip_persistencia"][f"{a}_{b}"] = q(f"SELECT count(*) FROM (SELECT DISTINCT CAST(COD_ID AS VARCHAR) k FROM read_parquet({pip[a]})) x JOIN (SELECT DISTINCT CAST(COD_ID AS VARCHAR) k FROM read_parquet({pip[b]})) y USING (k)")[0][0]
# 3) Elektro (385): rede AT (SSDAT) e MT (SSDMT) por ano, km e registros, e persistencia de COD_ID AT
for e in ("SSDAT", "SSDMT"):
    res[f"elektro_{e}"] = {}
    for a in (2022, 2023, 2024, 2025):
        f = arquivo(a, 385, e)
        res[f"elektro_{e}"][a] = None if not f else [float(x) if x is not None else None for x in q(f"SELECT count(*), sum(CAST(COMP AS DOUBLE)) / 1000 FROM read_parquet({f})")[0]]
at = {a: arquivo(a, 385, "SSDAT") for a in (2022, 2023, 2024)}
res["elektro_ssdat_persistencia"] = {f"{a}_{b}": q(f"SELECT count(*) FROM (SELECT DISTINCT CAST(COD_ID AS VARCHAR) k FROM read_parquet({at[a]})) x JOIN (SELECT DISTINCT CAST(COD_ID AS VARCHAR) k FROM read_parquet({at[b]})) y USING (k)")[0][0]
                                     for a, b in ((2022, 2023), (2023, 2024), (2022, 2024)) if at[a] and at[b]}
for a in (2022, 2023):
    f = at[a]
    if f: res[f"elektro_ssdat_tensao_{a}"] = [list(x) for x in q(f"SELECT count(DISTINCT CT_COD_OP), count(*), round(sum(CAST(COMP AS DOUBLE))/1000, 1) FROM read_parquet({f})")]
(OUT / "investigacao_casos.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print(json.dumps(res, ensure_ascii=False, default=str)[:6000])
