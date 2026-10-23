"""Driver em lotes com checkpoint. Uso: run_lote.py [--tam 4] [--max-lotes N] [--dists 26,31] [--ate-mb X]
Ordena por tamanho crescente; pula DIST ja com _OK; confere disco antes de cada lote; atualiza progresso.json."""
import argparse, csv, json, pathlib, shutil, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import bdgd_etl as E
ap = argparse.ArgumentParser(); ap.add_argument("--tam", type=int, default=4); ap.add_argument("--max-lotes", type=int, default=999)
ap.add_argument("--dists", default=""); ap.add_argument("--forcar", action="store_true"); a = ap.parse_args()
R = E.R; raw, pqr, out = R / "staging_raw", R / "staging_parquet", R / "proc"; out.mkdir(exist_ok=True); (R / "tmp_duckdb").mkdir(exist_ok=True)
logf = open(R / "logs" / "lotes_2025.log", "a", encoding="utf-8")
def log(m):
    l = f"{E.now()} {m}"; print(l, flush=True); logf.write(l + "\n"); logf.flush()
inv = [r for r in csv.DictReader(open(R / "inventario" / "inventario_2025.csv", encoding="utf-8")) if r["data_base_declarada"] == E.DB]
if a.dists: inv = [r for r in inv if r["dist"] in set(a.dists.split(","))]
inv.sort(key=lambda r: int(r["tamanho_bytes"]))
pend = [r for r in inv if a.forcar or not (out / f"DIST={r['dist']}" / "_OK").exists()]
log(f"pendentes: {len(pend)} de {len(inv)}; lotes de {a.tam}")
K_ = E.Conhecimento(); prog_f = R / "progresso.json"
def progresso():
    ok = [p for p in out.glob("DIST=*/_OK")]; resumos = [json.loads((p.parent / "resumo.json").read_text()) for p in ok]
    fal = [p.parent.name for p in out.glob("DIST=*/_FALHA.json")]
    prog = {"atualizado_em": E.now(), "concluidas": len(ok), "falhas_quarentena": fal, "linhas_processadas": sum(r["linhas_processadas"] for r in resumos),
            "alertas": sum(r["alertas"] for r in resumos), "recon_falhas": sum(r["reconciliacao_falhas"] for r in resumos), "total_alvo": 99}
    prog_f.write_text(json.dumps(prog, indent=1)); return prog
for i in range(0, len(pend), a.tam):
    if i // a.tam >= a.max_lotes: break
    lote = pend[i:i + a.tam]
    maior = max(int(r["tamanho_bytes"]) for r in lote); livre = shutil.disk_usage(str(R)).free
    if livre < 150e9 or livre < 2 * 3 * maior:
        log(f"PAUSA: disco insuficiente ({livre/1e9:.0f} GB livres, maior {maior/1e9:.2f} GB)"); break
    log(f"=== lote {i // a.tam + 1}: DIST {[r['dist'] for r in lote]} ({sum(int(r['tamanho_bytes']) for r in lote)/1e6:.0f} MB) ===")
    for r in lote: E.executar(r, K_, raw, pqr, out, log)
    log(f"progresso: {progresso()}")
