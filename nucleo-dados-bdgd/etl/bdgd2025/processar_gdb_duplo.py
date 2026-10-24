"""Processa um item cujo ZIP contem mais de um GDB (2022/6072 Equatorial GO: Enel_GO_* e Equatorial_GO_*), SOMENTE se
equivalencia_gdb_duplo.json comprovar que todos os GDBs do ZIP sao integralmente equivalentes (todas as camadas com
esquema, contagem, atributos e geometria identicos). Escolhe o GDB cujo nome contem o nome da empresa no inventario
(controlador vigente); a escolha nao altera dados porque os GDBs sao equivalentes. Usa pipeline_antijoin.py (o
pipeline.py original fica intacto), o mesmo lock e o mesmo gate de recursos do runner. Registra gdb_escolhido.json.
Uso: processar_gdb_duplo.py ANO DIST [--memory-mb 1536]"""
import argparse, json, os, sys, traceback, zipfile
from pathlib import Path

HROOT = Path(os.environ.get("BDGD_HIST_ROOT", "D:/NUCLEO_BDGD_2022_2024"))
sys.path.insert(0, str(HROOT / "repo" / "nucleo-dados-bdgd" / "historico"))
import run as R                      # noqa: E402
import pipeline_antijoin as P        # noqa: E402

ORIGINAL = P.inspect_gdb


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("ano"); ap.add_argument("dist"); ap.add_argument("--memory-mb", type=int, default=1536); a = ap.parse_args()
    row = next(r for r in R.csv_read(HROOT / "inventario" / "inventario_historico_2022_2024.csv") if r["ano"] == a.ano and r["dist"] == a.dist and r["status"] == "candidato")
    eqf = HROOT / "proc" / a.ano / a.dist / "equivalencia_gdb_duplo.json"
    eq = json.loads(eqf.read_text(encoding="utf-8"))
    if not eq.get("equivalente"):
        sys.exit("GDBs nao comprovadamente equivalentes: decisao humana")
    alvo = row["empresa"].replace(" ", "_").lower()
    escolhido = [g for g in eq["gdbs"] if alvo in g.lower()]
    if len(escolhido) != 1:
        sys.exit(f"nao foi possivel escolher o GDB pelo nome da empresa ({row['empresa']}): {eq['gdbs']}")
    escolhido = escolhido[0]

    def inspect_um(archive, r):
        with zipfile.ZipFile(archive) as z:
            raizes = sorted({n[:n.lower().index(".gdb") + 4] for n in z.namelist() if ".gdb" in n.lower()})
        if raizes != sorted(eq["gdbs"]): raise ValueError(f"GDBs do ZIP diferem dos comparados: {raizes}")
        orig_zip = zipfile.ZipFile
        class UmGDB(zipfile.ZipFile):  # expoe so os membros do GDB escolhido para a inspecao original
            def namelist(self): return [n for n in super().namelist() if n.startswith(escolhido + "/") or n == escolhido]
        P.zipfile.ZipFile = UmGDB
        try: return ORIGINAL(archive, r)
        finally: P.zipfile.ZipFile = orig_zip

    P.inspect_gdb = inspect_um
    base = R.checkpoint(HROOT, row).parent
    with R.lock(HROOT):
        if not R.resource_gate(HROOT, row, True, a.memory_mb):
            sys.exit("memoria insuficiente (resource gate)")
        f = base / "failure.json"
        if f.exists(): f.replace(f.with_name("failure.gdb_duplo_" + R.now().replace(":", "").replace("+", "_") + ".json"))
        print(f"START gdb_duplo {a.ano}/{a.dist} {escolhido}", flush=True)
        try:
            P.process(row, HROOT, a.memory_mb)
        except Exception as exc:
            R.atomic_json(f, dict(dist=row["dist"], ano=row["ano"], item_id=row["item_id"], failed_at=R.now(), error_type=type(exc).__name__, error=str(exc), trace=traceback.format_exc()))
            print(f"FAIL {a.ano}/{a.dist} {type(exc).__name__}: {exc}", flush=True); sys.exit(1)
        R.atomic_json(base / "gdb_escolhido.json", dict(gdb=escolhido, gdbs_no_zip=eq["gdbs"], criterio="equivalencia integral comprovada (equivalencia_gdb_duplo.json); escolhido pelo nome da empresa no inventario", em=R.now()))
    print("OK", flush=True)


if __name__ == "__main__":
    main()
