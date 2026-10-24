"""Processa as publicacoes em 'revisao_pendente' (mais de um item ArcGIS para a mesma DIST/competencia) com o MESMO pipeline
historico (pipeline.process), o mesmo gate de recursos e o mesmo lock exclusivo do run.py. Nao altera o codigo nem o
inventario do ETL historico; so cria checkpoints/failures dos itens, como o runner faria.

A decisao sobre qual publicacao usar NAO e tomada aqui. equivalencia_duplicatas.py compara os itens validados:
  - mesmo SHA-256 da fonte                                                          -> equivalentes;
  - registros, atributos, TUC/A1-A6, codigos DDA, vinculos e geometria identicos      -> equivalentes;
  - qualquer diferenca ou comparacao impossivel                                     -> revisao humana (pendente).
Totais iguais nos ativos nao comprovam equivalencia.
Correcao de memoria (24/10/2026): usa pipeline_antijoin.py, copia do pipeline.py em que a checagem de vinculos
NOT IN (mark join, sem uso de disco) virou LEFT JOIN contra chaves DISTINCT (mesmo resultado, pode usar disco).
O pipeline.py original fica intacto para nao invalidar o hash dos checkpoints ja concluidos; os checkpoints novos
registram o hash do pipeline_antijoin.py. --retentar-oom tambem reprocessa itens 'candidato' que falharam por
OutOfMemoryException (o failure.json anterior e preservado como failure.oom_anterior.json).
Uso: duplicatas_historico.py [--memory-mb 768] [--retentar-oom]"""
import argparse, csv, json, os, sys, traceback
from pathlib import Path

HROOT = Path(os.environ.get("BDGD_HIST_ROOT", "D:/NUCLEO_BDGD_2022_2024"))
sys.path.insert(0, str(HROOT / "repo" / "nucleo-dados-bdgd" / "historico"))
import run as R          # noqa: E402  (lock, resource_gate, completed, checkpoint, atomic_json, now)
import pipeline_antijoin as P     # noqa: E402
import hashlib             # noqa: E402
SHA_P = hashlib.sha256(Path(P.__file__).read_bytes()).hexdigest()


def feito(row):
    """Concluido pelo pipeline original (R.completed) ou pelo pipeline_antijoin."""
    if R.completed(HROOT, row): return True
    ck = R.checkpoint(HROOT, row)
    if not ck.exists(): return False
    rec = json.loads(ck.read_text(encoding="utf-8"))
    return rec.get("item_id") == row["item_id"] and rec.get("data_base") == row["data_base"] and rec.get("reconciliation_failures") == 0 and rec.get("pipeline_sha256") == SHA_P


def falha_oom(row):
    f = R.checkpoint(HROOT, row).parent / "failure.json"
    return f.exists() and json.loads(f.read_text(encoding="utf-8")).get("error_type") == "OutOfMemoryException"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--memory-mb", type=int, default=768); ap.add_argument("--retentar-oom", action="store_true"); a = ap.parse_args()
    inv = HROOT / "inventario" / "inventario_historico_2022_2024.csv"
    todos = R.csv_read(inv)
    rows = [r for r in todos if r["status"] == "revisao_pendente"]
    if a.retentar_oom:
        oom = [r for r in todos if r["status"] == "candidato" and not feito(r) and falha_oom(r)]
        for r in oom:
            f = R.checkpoint(HROOT, r).parent / "failure.json"; f.replace(f.with_name("failure.oom_" + R.now().replace(":", "").replace("+", "_") + ".json"))
        rows += oom
    rows.sort(key=lambda r: (int(r["tamanho_bytes"] or 0), r["ano"], r["dist"]))
    with R.lock(HROOT):
        for row in rows:
            if feito(row) or (R.checkpoint(HROOT, row).parent / "failure.json").exists():
                continue
            mem = min(a.memory_mb, 128) if int(row["tamanho_bytes"] or 0) <= 20 * 1024 ** 2 else a.memory_mb
            if not R.resource_gate(HROOT, row, True, mem):
                return
            print(f"START {row['status']} {row['ano']}/{row['dist']} {row['item_id']}", flush=True)
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
