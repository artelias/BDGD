#!/usr/bin/env bash
# Apos o reprocesso OOM (auditoria e consistencia ANTES do 79, que grava o manifesto com checksums dos CSV): Equatorial GO 2022 (GDB duplo equivalente) -> 78 -> equivalencia -> 79 -> validador -> auditoria por item
set -u
L=/d/NUCLEO_BDGD_2025/logs/cadeia_historico.log; H=/d/NUCLEO_BDGD_2022_2024
P25=/d/NUCLEO_BDGD_2025/.venv/Scripts/python.exe; PH=$H/.venv/Scripts/python.exe
log() { echo "$(date -Iseconds) $*" >> "$L"; }
until grep -q "oom1536 fim" "$L"; do sleep 60; done
log "final: inicio 6072"
cd "$H" && "$PH" -u /d/NUCLEO_BDGD_2025/scripts/processar_gdb_duplo.py 2022 6072 --memory-mb 1536 >> /d/NUCLEO_BDGD_2025/logs/gdb_duplo_6072.log 2>&1; log "6072: exit $?"
cd /d/NUCLEO_BDGD_2025 && BDGD_DUCKDB_MEM=768MB "$P25" -u scripts/78_conceitos_historico.py >> logs/conceitos_hist.log 2>&1; log "78: exit $?"
BDGD_DUCKDB_MEM=768MB "$P25" -u scripts/equivalencia_duplicatas.py >> logs/dup_equivalencia.log 2>&1; log "equivalencia: exit $?"
"$P25" -I scripts/auditoria_itens_historico.py >> "$L" 2>&1; log "auditoria: exit $?"
"$P25" -I scripts/consistencia_temporal.py >> "$L" 2>&1; log "consistencia: exit $?"
"$P25" -u scripts/79_serie_historica.py >> logs/serie_historica.log 2>&1; log "79: exit $?"
node repo/nucleo-dados-bdgd/etl/validate-serie-historica.mjs output-historico/2022-2025 repo/nucleo-dados-bdgd/web/public/data/historico/serie.json >> "$L" 2>&1; log "validador: exit $?"
log "final fim"
