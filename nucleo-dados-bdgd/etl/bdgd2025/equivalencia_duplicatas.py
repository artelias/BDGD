"""Equivalencia integral entre publicacoes multiplas da mesma DIST/competencia (ETL historico 2022-2024).

Regra (decisao do responsavel, 24/10/2026): totais iguais NAO bastam. Dois itens so sao equivalentes se
  (a) o SHA-256 da fonte e identico; ou
  (b) para TODAS as entidades: mesmo esquema (colunas e tipos), mesma contagem de registros, mesma identidade (COD_ID),
      mesmos atributos (impressao digital por registro, independente da ordem, separada em TUC/A1-A6, codigos DDA,
      vinculos e demais campos) e mesma geometria (COD_ID + WKB por feicao, lida do GDB original).
Qualquer diferenca, campo nao comparavel ou falha de leitura -> nao comprovado -> revisao humana.
Impressao digital de um conjunto: (n, soma de hash64 mod 2^64, xor de hash64) — duas agregacoes independentes de 64 bits.
Unica coluna ignorada: OBJECTID (numero interno da linha no GDB, sem significado de negocio).
Saida: proc/ANO/DIST/equivalencia_duplicatas.json e D:/NUCLEO_BDGD_2025/logs/equivalencia_duplicatas.csv. Somente leitura dos dados."""
import csv, hashlib, json, os, pathlib, sys, time, zipfile
import duckdb, pyogrio
from pyogrio import raw as pr

H = pathlib.Path(os.environ.get("BDGD_HIST_ROOT", "D:/NUCLEO_BDGD_2022_2024"))
K = pathlib.Path(os.environ.get("BDGD_KNOWLEDGE", "C:/GEOIA/GEOIA_DATA_HUB/knowledge"))
LOG = pathlib.Path("D:/NUCLEO_BDGD_2025/logs/equivalencia_duplicatas.csv")
IGNORAR = {"OBJECTID"}
TUC = {"TUC", "A1", "A2", "A3", "A4", "A5", "A6", "UAR", "TUC_FAS", "A1_FAS", "A2_FAS", "A3_FAS", "A4_FAS", "A5_FAS", "A6_FAS"}
SCH = json.loads((K / "BDGD_ENTITY_SCHEMA_SEMANTIC_REV5.json").read_text(encoding="utf-8"))
TIPOS = {(e["entity"], f["name"]): f["normalized_type"] for e in SCH["entities"] for f in e["fields"]}
M64 = 2 ** 64


def grupos(ent, cols):
    g = {"identidade": [c for c in cols if c == "COD_ID"], "tuc_mcpse": [c for c in cols if c in TUC],
         "dda": [c for c in cols if TIPOS.get((ent, c)) == "DDA"], "vinculos": [c for c in cols if TIPOS.get((ent, c)) == "ENTITY_LINK"]}
    usados = set().union(*g.values())
    g["demais"] = [c for c in cols if c not in usados]
    return g


def ident(c):
    """Identificador SQL entre aspas duplas, com aspas internas duplicadas."""
    return '"' + str(c).replace('"', '""') + '"'


def literal(v):
    return "'" + str(v).replace("'", "''") + "'"


def digital(con, pq, cols):
    """(n, soma, xor) do hash por registro do struct NOMEADO das colunas (ordem alfabetica, independente da ordem no arquivo)."""
    if not cols: return None
    campos = ", ".join(f"{ident(c)} := {ident(c)}" for c in sorted(cols))
    n, s, x = con.execute(f"SELECT count(*), sum(h::HUGEINT) % {M64}, bit_xor(h) FROM "
                          f"(SELECT hash(struct_pack({campos})) AS h FROM read_parquet({literal(pq)}))").fetchone()
    return [int(n), str(s or 0), str(x or 0)]


def geo_digital(zip_path, layer, idcol):
    """(n, soma, xor) de blake2b-64(COD_ID || WKB) por feicao, em lotes, a partir do GDB original."""
    with zipfile.ZipFile(zip_path) as z:
        raiz = next(n.split(".gdb")[0] + ".gdb" for n in z.namelist() if ".gdb" in n.lower())
    src = f"/vsizip/{pathlib.Path(zip_path).as_posix()}/{raiz}"
    n = s = x = 0
    with pr.open_arrow(src, layer=layer, columns=[idcol] if idcol else [], batch_size=20000, use_pyarrow=True) as (meta, rdr):
        gcol = meta.get("geometry_name") or "wkb_geometry"
        for b in rdr:
            g = b.column(b.schema.get_field_index(gcol)) if gcol in b.schema.names else b.column(b.num_columns - 1)
            ids = b.column(b.schema.get_field_index(idcol)).to_pylist() if idcol and idcol in b.schema.names else [None] * b.num_rows
            for i, w in zip(ids, g.to_pylist()):
                h = int.from_bytes(hashlib.blake2b((str(i) + "|").encode() + (w or b""), digest_size=8).digest(), "little")
                n += 1; s = (s + h) % M64; x ^= h
    return [n, str(s), str(x)]


def comparar(ano, dist, itens, con):
    out = {"ano": ano, "dist": dist, "itens": itens, "criterio": None, "entidades": {}, "diferencas": []}
    cks = {it: json.loads((H / "proc" / ano / dist / it / "checkpoint.json").read_text(encoding="utf-8")) for it in itens}
    if len({c["source_sha256"] for c in cks.values()}) == 1:
        out["criterio"] = "mesmo SHA-256 da fonte"; out["equivalente"] = True; return out
    pastas = {it: H / "parquet" / ano / dist / it for it in itens}
    ents = sorted({p.name[:-8] for it in itens for p in pastas[it].glob("*.parquet")})
    zips = {it: next((H / "raw" / ano / dist / it).glob("*.zip"), None) for it in itens}
    camadas = {}
    for it in itens:
        try: camadas[it] = {l[0]: l[1] for l in pyogrio.list_layers(f"/vsizip/{zips[it].as_posix()}/" + next(n.split(".gdb")[0] + ".gdb" for n in zipfile.ZipFile(zips[it]).namelist() if ".gdb" in n.lower()))} if zips[it] else {}
        except Exception as e: camadas[it] = {}; out["diferencas"].append(f"leitura de camadas do GDB {it}: {e}")
    for e in ents:
        r = {}
        for it in itens:
            pq = pastas[it] / f"{e}.parquet"
            if not pq.exists(): r[it] = {"ausente": True}; continue
            pqs = pq.as_posix()
            esquema = sorted((c, t) for c, t, *_ in con.execute(f"DESCRIBE SELECT * FROM read_parquet({literal(pqs)})").fetchall() if c not in IGNORAR)
            cols = [c for c, _ in esquema]
            r[it] = {"esquema": hashlib.sha256(json.dumps(esquema).encode()).hexdigest()[:16],
                     "registro": digital(con, pqs, cols), **{f"grupo_{k}": digital(con, pqs, v) for k, v in grupos(e, cols).items()}}
            geom = camadas.get(it, {}).get(e)
            if geom and geom not in (None, "", "None"):
                try: r[it]["geometria"] = geo_digital(zips[it], e, "COD_ID" if "COD_ID" in cols else None)
                except Exception as ex: r[it]["geometria"] = f"erro: {ex}"
        out["entidades"][e] = r
        vals = list(r.values())
        for campo in sorted({k for v in vals for k in v}):
            if len({json.dumps(v.get(campo)) for v in vals}) > 1:
                out["diferencas"].append(f"{e}.{campo}")
    out["equivalente"] = not out["diferencas"]
    out["criterio"] = "registros, atributos, TUC, DDA, vinculos e geometria identicos" if out["equivalente"] else "nao comprovado"
    return out


def main():
    inv = list(csv.DictReader(open(H / "inventario" / "inventario_historico_2022_2024.csv", encoding="utf-8")))
    pares = {}
    for x in inv:
        if x["status"] == "revisao_pendente": pares.setdefault((x["ano"], x["dist"]), []).append(x["item_id"])
    con = duckdb.connect(); con.execute(f"SET threads=2; SET memory_limit='{os.environ.get('BDGD_DUCKDB_MEM', '768MB')}'; SET temp_directory='D:/NUCLEO_BDGD_2025/tmp_duckdb'")
    linhas = []
    for (ano, dist), itens in sorted(pares.items(), key=lambda k: (k[0][0], int(k[0][1]))):
        prontos = [it for it in itens if (H / "proc" / ano / dist / it / "checkpoint.json").exists()]
        falhas = [it for it in itens if (H / "proc" / ano / dist / it / "failure.json").exists()]
        dst = H / "proc" / ano / dist / "equivalencia_duplicatas.json"
        if len(prontos) < 2:
            linhas.append({"ano": ano, "dist": dist, "itens": "+".join(itens), "estado": "aguardando" if not falhas else "item com falha", "criterio": "", "diferencas": ""}); continue
        t0 = time.time()
        try: res = comparar(ano, dist, sorted(prontos), con)
        except Exception as ex: res = {"ano": ano, "dist": dist, "itens": prontos, "equivalente": False, "criterio": "nao comprovado", "diferencas": [f"erro: {ex}"]}
        dst.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        linhas.append({"ano": ano, "dist": dist, "itens": "+".join(sorted(prontos)), "estado": "equivalente" if res["equivalente"] else "revisao_humana",
                       "criterio": res["criterio"], "diferencas": "; ".join(res["diferencas"][:20])})
        print(f"{ano}/{dist}: {linhas[-1]['estado']} ({res['criterio']}) {len(res['diferencas'])} diferenca(s) {time.time() - t0:.0f}s", flush=True)
    with open(LOG, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["ano", "dist", "itens", "estado", "criterio", "diferencas"], lineterminator="\n"); w.writeheader(); w.writerows(linhas)


if __name__ == "__main__":
    main()
