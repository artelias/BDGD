"""Processa as publicacoes em 'revisao_pendente' (mais de um item ArcGIS para a mesma DIST/competencia) com o MESMO pipeline
historico (pipeline.process), o mesmo gate de recursos e o mesmo lock exclusivo do run.py. Nao altera o codigo nem o
inventario do ETL historico; so cria checkpoints/failures dos itens, como o runner faria.

A decisao sobre qual publicacao usar NAO e tomada aqui. equivalencia_duplicatas.py compara os itens validados:
  - mesmo SHA-256 da fonte                                                          -> equivalentes;
  - registros, atributos, TUC/A1-A6, codigos DDA, vinculos e geometria identicos      -> equivalentes;
  - qualquer diferenca ou comparacao impossivel                                     -> revisao humana (pendente).
Totais iguais nos ativos nao comprovam equivalencia.
Uso: duplicatas_historico.py [--memory-mb 768]"""
import argparse, csv, json, os, sys, traceback
from pathlib import Path

HROOT = Path(os.environ.get("BDGD_HIST_ROOT", "D:/NUCLEO_BDGD_2022_2024"))
sys.path.insert(0, str(HROOT / "repo" / "nucleo-dados-bdgd" / "historico"))
import run as R          # noqa: E402  (lock, resource_gate, completed, checkpoint, atomic_json, now)
import pipeline as P     # noqa: E402


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--memory-mb", type=int, default=768); a = ap.parse_args()
    inv = HROOT / "inventario" / "inventario_historico_2022_2024.csv"
    rows = [r for r in R.csv_read(inv) if r["status"] == "revisao_pendente"]
    rows.sort(key=lambda r: (int(r["tamanho_bytes"] or 0), r["ano"], r["dist"]))
    with R.lock(HROOT):
        for row in rows:
            if R.completed(HROOT, row) or (R.checkpoint(HROOT, row).parent / "failure.json").exists():
                continue
            mem = min(a.memory_mb, 128) if int(row["tamanho_bytes"] or 0) <= 20 * 1024 ** 2 else a.memory_mb
            if not R.resource_gate(HROOT, row, True, mem):
                return
            print(f"START duplicata {row['ano']}/{row['dist']} {row['item_id']}", flush=True)
            try:
                P.process(row, HROOT, mem)
            except Exception as exc:
                R.atomic_json(R.checkpoint(HROOT, row).parent / "failure.json", dict(dist=row["dist"], ano=row["ano"], item_id=row["item_id"], failed_at=R.now(),
                              error_type=type(exc).__name__, error=str(exc), trace=traceback.format_exc()))
                print(f"FAIL {row['ano']}/{row['dist']} {type(exc).__name__}: {exc}", flush=True)
        from report import report
        report(HROOT)
    print(json.dumps({"fim": R.now(), "itens": len(rows)}), flush=True)


if __name__ == "__main__":
    main()
