"""Extrai, dos Parquets já processados (sem reabrir ZIPs/GDBs), as variáveis internas do Motor de Expansão:

1. UC por município (UCBT ∪ UCMT ∪ UCAT, SIT_ATIV='AT'): pesos DIST→município comprovados pelo atributo MUN da própria UC
   (nenhuma inferência espacial). Usados para ponderar variáveis externas municipais do IBGE.
2. Energia declarada das UC (ENE_01..ENE_12, kWh) por DIST-ano: variável interna de mercado.
3. Potência nominal instalada de transformadores por TUC (565, 570, 575) via vínculo EQ→UN, contando cada unidade uma vez:
   EQTRMT.UNI_TR_MT → UNTRMT.COD_ID (POT_NOM em kVA) e EQTRAT.UNI_TR_AT → UNTRAT.COD_ID (POT_NOM em MVA, ×1000).
   EQ*.POT_NOM é código de domínio e A4 é faixa patrimonial: nenhum dos dois é usado como potência.

Uso: python extrair_features.py <serie_fisica_nacional.csv> <saida_dir>
A publicação usada por DIST-ano é a mesma do contrato nacional (publicacao_id), inclusive a republicação mais recente.
"""
import csv
import json
import sys
import time
from pathlib import Path

import duckdb

H = Path("D:/NUCLEO_BDGD_2022_2024/parquet")
R = Path("D:/NUCLEO_BDGD_2025/staging_parquet")
KVA_PADRAO = {1.5, 3, 5, 7.5, 10, 15, 25, 30, 37.5, 45, 50, 75, 100, 112.5, 125, 150, 167, 200, 225, 250, 300, 333, 500, 750, 1000}


def caminho(ano, dist, pub, ent):
    if ano == 2025:
        p = R / f"DIST={dist}" / "DATA_BASE=2025-12-31" / f"entidade={ent}" / "part-0.parquet"
    else:
        p = H / str(ano) / str(dist) / pub / f"{ent}.parquet"
    return p if p.exists() else None


def colunas(con, p):
    return {r[0] for r in con.sql(f"DESCRIBE SELECT * FROM read_parquet('{p.as_posix()}')").fetchall()}


def publicacoes(contrato):
    pubs = {}
    for r in csv.DictReader(open(contrato, encoding="utf-8")):
        if r["estado"] in ("observado", "zero_verificado") and r["publicacao_id"]:
            k = (int(r["ano"]), int(r["dist"]))
            # preferência: publicação da linha de consumidores; senão qualquer linha observada
            if k not in pubs or r["conceitoId"] == "consumidores":
                pubs[k] = r["publicacao_id"]
    return pubs


def main(contrato, saida):
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.sql("SET memory_limit='2GB'; SET threads=4; SET temp_directory='D:/NUCLEO_BDGD_2025/motor_externas/tmp_duckdb'")
    mun_rows, ene_rows, pot_rows = [], [], []
    pubs = publicacoes(contrato)
    t0 = time.time()
    for i, ((ano, dist), pub) in enumerate(sorted(pubs.items())):
        # 1-2) UC por município e energia
        ene_total, n_uc_ene, fontes = 0.0, 0, []
        por_mun = {}
        for ent in ("UCBT", "UCMT", "UCAT"):
            p = caminho(ano, dist, pub, ent)
            if not p:
                continue
            cols = colunas(con, p)
            enes = [f"ENE_{m:02d}" for m in range(1, 13) if f"ENE_{m:02d}" in cols]
            soma = " + ".join(f"coalesce(try_cast({c} AS DOUBLE),0)" for c in enes) or "0"
            q = f"""SELECT coalesce(cast(MUN AS VARCHAR),'') mun, count(*) FILTER (WHERE cast(SIT_ATIV AS VARCHAR)='AT') n_at,
                    sum({soma}) ene FROM read_parquet('{p.as_posix()}') GROUP BY 1"""
            for mun, n_at, ene in con.sql(q).fetchall():
                por_mun[mun] = por_mun.get(mun, 0) + (n_at or 0)
                ene_total += ene or 0.0
            n_uc_ene += 1
            fontes.append(ent)
        for mun, n in por_mun.items():
            if n:
                mun_rows.append({"ano": ano, "dist": dist, "mun": mun, "uc_ativas": n})
        ene_rows.append({"ano": ano, "dist": dist, "publicacao_id": pub, "energia_uc_mwh": round(ene_total / 1000, 3),
                         "entidades": "+".join(fontes)})
        # 3) potência por TUC via EQ→UN, cada unidade contada uma vez
        res = {}
        for eq, un, chave, fator in (("EQTRMT", "UNTRMT", "UNI_TR_MT", 1.0), ("EQTRAT", "UNTRAT", "UNI_TR_AT", 1000.0)):
            pe, pu = caminho(ano, dist, pub, eq), caminho(ano, dist, pub, un)
            if not pe:
                continue
            if not pu or chave not in colunas(con, pe) or "POT_NOM" not in colunas(con, pu):
                for tuc, n in con.sql(f"SELECT cast(TUC AS VARCHAR), count(*) FROM read_parquet('{pe.as_posix()}') GROUP BY 1").fetchall():
                    r = res.setdefault(tuc, {"eq": 0, "eq_vinc": 0, "un": 0, "kva": 0.0, "un_multi_tuc": 0, "kva_padrao": 0})
                    r["eq"] += n
                continue
            tipo = (con.sql(f"SELECT typeof(POT_NOM) FROM read_parquet('{pu.as_posix()}') LIMIT 1").fetchall() or [None])[0]
            q = f"""WITH e AS (SELECT cast(TUC AS VARCHAR) tuc, cast({chave} AS VARCHAR) un FROM read_parquet('{pe.as_posix()}')),
                    u AS (SELECT cast(COD_ID AS VARCHAR) un, try_cast(POT_NOM AS DOUBLE) pot FROM read_parquet('{pu.as_posix()}')),
                    u1 AS (SELECT un, max(pot) pot, count(*) dup FROM u GROUP BY un),
                    m AS (SELECT un, count(DISTINCT tuc) ntuc FROM e GROUP BY un),
                    lig AS (SELECT DISTINCT e.tuc, e.un, u1.pot, m.ntuc FROM e JOIN u1 USING (un) JOIN m USING (un))
                    SELECT t.tuc, t.n_eq, coalesce(v.n_vinc,0), coalesce(l.n_un,0), coalesce(l.kva,0), coalesce(l.multi,0), coalesce(l.padrao,0)
                    FROM (SELECT tuc, count(*) n_eq FROM e GROUP BY tuc) t
                    LEFT JOIN (SELECT tuc, count(*) n_vinc FROM e JOIN u1 USING (un) GROUP BY tuc) v USING (tuc)
                    LEFT JOIN (SELECT tuc, count(*) n_un, sum(pot) * {fator} kva, count(*) FILTER (WHERE ntuc > 1) multi,
                               count(*) FILTER (WHERE pot * {fator} IN ({','.join(str(x) for x in sorted(KVA_PADRAO))})) padrao
                               FROM lig GROUP BY tuc) l USING (tuc)"""
            for tuc, n_eq, n_vinc, n_un, kva, multi, padrao in con.sql(q).fetchall():
                r = res.setdefault(tuc, {"eq": 0, "eq_vinc": 0, "un": 0, "kva": 0.0, "un_multi_tuc": 0, "kva_padrao": 0})
                r["eq"] += n_eq; r["eq_vinc"] += n_vinc; r["un"] += n_un; r["kva"] += kva or 0.0
                r["un_multi_tuc"] += multi; r["kva_padrao"] += padrao if eq == "EQTRMT" else 0
                r.setdefault("tipo_pot", []).append(f"{un}:{tipo[0] if tipo else ''}")
        for tuc, r in res.items():
            if tuc in ("565", "570", "575"):
                pot_rows.append({"ano": ano, "dist": dist, "tuc": tuc, "eq": r["eq"], "eq_vinculados": r["eq_vinc"], "unidades": r["un"],
                                 "potencia_kva": round(r["kva"], 3), "unidades_multi_tuc": r["un_multi_tuc"],
                                 "unidades_kva_padrao": r["kva_padrao"], "tipo_pot_nom": "|".join(r.get("tipo_pot", []))})
        if i % 20 == 0:
            print(f"{i+1}/{len(pubs)} {ano} {dist} {time.time()-t0:.0f}s", flush=True)
    for nome, rows in (("uc_por_municipio.csv", mun_rows), ("energia_uc.csv", ene_rows), ("potencia_trafos_tuc.csv", pot_rows)):
        with open(saida / nome, "w", encoding="utf-8", newline="\n") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
            w.writeheader(); w.writerows(rows)
    json.dump({"publicacoes": len(pubs), "segundos": round(time.time() - t0)}, open(saida / "extracao.json", "w"))
    print("OK", len(pubs), "publicações", round(time.time() - t0), "s")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
