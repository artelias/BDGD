#!/usr/bin/env bash
# v3 (24/10/2026): sem reexecutar o run.py (o pipeline.py original segue intacto). Em serie:
# aguarda a v2 terminar -> duplicatas + itens com falha de memoria (pipeline_antijoin) -> 78 -> equivalencia -> 79 -> validador
set -u
L=/d/NUCLEO_BDGD_2025/logs/cadeia_historico.log
H=/d/NUCLEO_BDGD_2022_2024
P25=/d/NUCLEO_BDGD_2025/.venv/Scripts/python.exe
PH=$H/.venv/Scripts/python.exe
log() { echo "$(date -Iseconds) $*" >> "$L"; }
log "v3 inicio (v2 ja concluida)"
rm -f "$H/STOP_REQUESTED"
cd "$H" && BDGD_DUCKDB_MEM=768MB "$PH" -u /d/NUCLEO_BDGD_2025/scripts/duplicatas_historico.py --memory-mb 768 --retentar-oom >> /d/NUCLEO_BDGD_2025/logs/dup_driver.log 2>&1; log "duplicatas+oom: exit $? $(grep -c '^FAIL' /d/NUCLEO_BDGD_2025/logs/dup_driver.log) linha(s) FAIL no log"
cd /d/NUCLEO_BDGD_2025 && BDGD_DUCKDB_MEM=768MB "$P25" -u scripts/78_conceitos_historico.py >> logs/conceitos_hist.log 2>&1; log "78: exit $?"
BDGD_DUCKDB_MEM=768MB "$P25" -u scripts/equivalencia_duplicatas.py >> logs/dup_equivalencia.log 2>&1; log "equivalencia: exit $?"
"$P25" -u scripts/79_serie_historica.py >> logs/serie_historica.log 2>&1; log "79: exit $?"
node repo/nucleo-dados-bdgd/etl/validate-serie-historica.mjs output-historico/2022-2025 repo/nucleo-dados-bdgd/web/public/data/historico/serie.json >> "$L" 2>&1; log "validador: exit $?"
log "v3 fim"
