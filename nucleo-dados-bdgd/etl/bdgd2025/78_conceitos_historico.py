"""R3 — mesmos ativos de 2025 aplicados as competencias 2022, 2023 e 2024 (serie tecnica comparavel).

Reutiliza integralmente o 77_conceitos.py (fontes, dimensoes, regra UC v3, vinculos EQ->UN deduplicados): somente a leitura
muda para o layout do ETL historico (D:/NUCLEO_BDGD_2022_2024/parquet/ANO/DIST/ITEM/<ENT>.parquet). Nada do historico e alterado.

Por item com checkpoint (BASE.DAT_FNL conferida e reconciliacao sem falha pelo pipeline historico):
  - cubo principal de cada conceito e total de cada ativo (mesmo filtro do catalogo 2025);
  - campos exigidos pelo filtro do ativo ausentes no layout do ano -> N/D (campo_ausente), nunca zero;
  - potencia nao entra na serie (traducao DDA historica nao homologada).
Saida por item: proc/ANO/DIST/ITEM/conceitos_r3.json. Uso: 78_conceitos_historico.py [--anos 2024] [--forcar]"""
import argparse, importlib.util, json, os, pathlib, sys, time
from decimal import Decimal
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import bdgd_etl as E
import duckdb

AQUI = pathlib.Path(__file__).parent
spec = importlib.util.spec_from_file_location("c77", AQUI / "77_conceitos.py"); c77 = importlib.util.module_from_spec(spec); spec.loader.exec_module(c77)
HROOT = pathlib.Path(os.environ.get("BDGD_HIST_ROOT", "D:/NUCLEO_BDGD_2022_2024"))
CFG = c77.CFG
SEM_TUC = {"000", "00", "0", "SEM_CODIGO", "NA"}
VERSAO_REGRA = "r3-1 (mesma regra 2025: 77_conceitos.py + config/conceitos_2025.json)"


class DistHist(c77.Dist):
    """Mesma interface do Dist de 2025, lendo o Parquet de atributos do ETL historico."""
    def __init__(self, d, con, pasta):
        self.d, self.con, self.base, self._cols = d, con, pasta, {}
        self.linhas = {}
        for ok in pasta.glob("*.ok.json"):
            e = ok.name.split(".")[0]
            self.linhas[e] = json.loads(ok.read_text(encoding="utf-8")).get("rows", 0)
        for e, n in self.linhas.items():
            if n and (pasta / f"{e}.parquet").exists():
                con.execute(f"CREATE OR REPLACE TEMP VIEW v_{e} AS SELECT * FROM read_parquet('{(pasta / f'{e}.parquet').as_posix()}')")
            else:
                self.linhas[e] = 0


def processa(ano, d, pasta, K, con):
    D = DistHist(d, con, pasta)
    c77.prepara(D, K)
    F = c77.fontes(D)
    principal = {}
    for cid, cfg in CFG["conceitos"].items():
        dims = cfg["cubos"]["principal"]
        linhas = []
        for (ent, frm, where, dmap, meds) in F.get(cid, []):
            sel = [dmap.get(dm, c77.lit(c77.NA)) for dm in dims]
            mcols = [meds.get(m, "NULL") for m in ("quantidade", "extensao_km")]
            q = f"SELECT {', '.join(sel + mcols) if sel else ', '.join(mcols)} FROM {frm} {'GROUP BY ALL' if sel else ''}"
            for r in D.con.execute(q).fetchall():
                linhas.append((ent, list(r[:len(dims)]), r[len(dims)], r[len(dims) + 1]))
        principal[cid] = {"dims": dims, "fontes": sorted({x[0] for x in F.get(cid, [])}), "linhas": linhas,
                          "campos_na": {dm for (ent, frm, where, dmap, meds) in F.get(cid, []) for dm, ex in dmap.items() if ex == c77.lit(c77.NA)}}
    ativos = {}
    for a in CFG["ativos"]:
        p = principal[a["conceito"]]
        st, mo, val = "validado", "", None
        if not p["fontes"]:
            st, mo = "ausente", "tipo de ativo inexistente no GDB desta competencia"
        elif any(dm in p["campos_na"] and all(dm in p["campos_na"] for _ in p["fontes"]) for dm in a["filtro"]):
            st, mo = "campo_ausente", "campo do recorte ausente no layout desta competencia: " + ", ".join(dm for dm in a["filtro"] if dm in p["campos_na"])
        else:
            sel = [x for x in p["linhas"] if all(x[1][p["dims"].index(k)] in v for k, v in a["filtro"].items())]
            if a["medida"] == "quantidade":
                val = sum(int(x[2] or 0) for x in sel)
            else:
                ms = [x[3] for x in sel if x[3] is not None]
                val = str(Decimal(sum(Decimal(m) for m in ms)) / 1000) if ms else None
                if val is None and sel: st, mo = "bloqueado", "comprimento nulo em todos os segmentos do recorte"
                if not sel: st, mo = "ausente", "sem registros desse tipo nesta competencia"
        ativos[a["id"]] = {"medida": a["medida"], "valor": val, "status": st, "motivo": mo}
    # populacao de cada conceito e parcela sem classificacao patrimonial MCPSE: base para marcar quebra de classificacao entre anos
    pop = {}
    for cid, p in principal.items():
        q = sum(int(x[2] or 0) for x in p["linhas"])
        sem = sum(int(x[2] or 0) for x in p["linhas"] if "tipo" in p["dims"] and x[1][p["dims"].index("tipo")] in SEM_TUC)
        pop[cid] = {"quantidade": q, "sem_tuc_mcpse": sem if "tipo" in p["dims"] else None}
    uc = c77.uc_qa(D)
    return {"ativos": ativos, "uc_v3": uc, "fontes": {k: v["fontes"] for k, v in principal.items()}, "populacao": pop}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--anos", default="2022,2023,2024"); ap.add_argument("--forcar", action="store_true"); a = ap.parse_args()
    K = E.Conhecimento()
    con = duckdb.connect(); con.execute(f"SET threads={os.environ.get('BDGD_DUCKDB_THREADS', '2')}; SET memory_limit='{os.environ.get('BDGD_DUCKDB_MEM', '1200MB')}'; "
                                        f"SET temp_directory='{(E.R / 'tmp_duckdb').as_posix()}'; SET preserve_insertion_order=false")
    for ano in a.anos.split(","):
        for ck in sorted((HROOT / "proc" / ano).glob("*/*/checkpoint.json"), key=lambda p: int(p.parent.parent.name)):
            c = json.loads(ck.read_text(encoding="utf-8"))
            dst = ck.parent / "conceitos_r3.json"
            if dst.exists() and not a.forcar: continue
            if c.get("data_base") != f"{ano}-12-31" or c.get("reconciliation_failures", 1) != 0: continue
            pasta = HROOT / "parquet" / ano / ck.parent.parent.name / ck.parent.name
            if not pasta.exists(): continue
            t0 = time.time()
            out = processa(ano, ck.parent.parent.name, pasta, K, con)
            out.update({"ano": int(ano), "dist": int(ck.parent.parent.name), "item_id": ck.parent.name, "source_sha256": c.get("source_sha256"),
                        "data_base": c["data_base"], "versao_regra": VERSAO_REGRA, "gerado_em": E.now()})
            tmp = dst.with_suffix(".tmp"); tmp.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8"); tmp.replace(dst)
            print(f"{E.now()} {ano}/{ck.parent.parent.name}: {sum(1 for x in out['ativos'].values() if x['status'] == 'validado')} ativos validados ({time.time() - t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
