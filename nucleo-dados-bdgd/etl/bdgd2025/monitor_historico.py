"""Monitor do ETL historico (somente leitura): a cada 60 s registra RAM disponivel, RSS dos processos do runner, item atual
e novas linhas de erro (DuckDB/OOM/Exception) nos logs do runner. Termina quando o runner encerra. Log: logs/monitor_historico.log"""
import json, re, time, pathlib, datetime
import psutil

H = pathlib.Path("D:/NUCLEO_BDGD_2022_2024")
LOG = pathlib.Path("D:/NUCLEO_BDGD_2025/logs/monitor_historico.log")
PADRAO = re.compile(r"duckdb|out of memory|outofmemory|memoryerror|exception|traceback|FAIL", re.I)
vistos = {}


def runner():
    return [p for p in psutil.process_iter(["pid", "cmdline", "memory_info"])
            if any("run.py" in c or "duplicatas_historico.py" in c or "78_conceitos_historico.py" in c for c in (p.info["cmdline"] or []))]


def main():
    ocioso = 0
    while True:
        ps = runner()
        vm = psutil.virtual_memory()
        try: cur = json.loads((H / "current.json").read_text(encoding="utf-8"))
        except Exception: cur = {}
        novos = []
        for f in sorted((H / "logs").glob("run5.*.log")) + sorted(pathlib.Path("D:/NUCLEO_BDGD_2025/logs").glob("dup*.log")):
            linhas = f.read_text(encoding="utf-8", errors="replace").splitlines()
            ini = vistos.get(f, 0); vistos[f] = len(linhas)
            novos += [f"{f.name}: {l[:200]}" for l in linhas[ini:] if PADRAO.search(l)]
        reg = {"t": datetime.datetime.now().isoformat(timespec="seconds"), "ram_disponivel_mb": vm.available // 2**20, "ram_uso_pct": vm.percent,
               "processos": [{"pid": p.info["pid"], "rss_mb": (p.info["memory_info"].rss // 2**20) if p.info["memory_info"] else None} for p in ps],
               "item": f"{cur.get('year')}/{cur.get('dist')}", "erros_novos": novos}
        with open(LOG, "a", encoding="utf-8") as fh: fh.write(json.dumps(reg, ensure_ascii=False) + "\n")
        ocioso = ocioso + 1 if not ps else 0
        if ocioso >= 30: break          # 30 min sem nenhum processo do pipeline historico
        time.sleep(60)


if __name__ == "__main__":
    main()
