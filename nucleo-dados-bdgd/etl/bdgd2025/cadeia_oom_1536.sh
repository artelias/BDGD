#!/usr/bin/env bash
# Reprocesso dos itens com OOM a 768 MB (Enel SP 390, Coelba 47, Cemig 4950) com DuckDB 1536 MB (necessidade comprovada
# pelos failure.json); so inicia com >= 2000 MB livres e sem a comparacao da 6072 em execucao. Depois: 78 -> equivalencia -> 79 -> validador.
set -u
L=/d/NUCLEO_BDGD_2025/logs/cadeia_historico.log; H=/d/NUCLEO_BDGD_2022_2024
P25=/d/NUCLEO_BDGD_2025/.venv/Scripts/python.exe; PH=$H/.venv/Scripts/python.exe
log() { echo "$(date -Iseconds) $*" >> "$L"; }
livre() { powershell -NoProfile -Command "[int]((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1024)" | tr -d '\r'; }
log "oom1536: aguardando fim da comparacao 6072 e >= 2000 MB livres"
until grep -qE "^(EQUIVALENTE|DIVERGENTE)|Traceback" /d/NUCLEO_BDGD_2025/logs/equivalencia_6072.log 2>/dev/null; do sleep 60; done
until [ "$(livre)" -ge 2000 ]; do sleep 60; done
log "oom1536: inicio com $(livre) MB livres"
cd "$H" && "$PH" -u /d/NUCLEO_BDGD_2025/scripts/duplicatas_historico.py --memory-mb 1536 --retentar-oom >> /d/NUCLEO_BDGD_2025/logs/dup_driver.log 2>&1; log "oom1536 driver: exit $?"
cd /d/NUCLEO_BDGD_2025 && BDGD_DUCKDB_MEM=768MB "$P25" -u scripts/78_conceitos_historico.py >> logs/conceitos_hist.log 2>&1; log "78: exit $?"
BDGD_DUCKDB_MEM=768MB "$P25" -u scripts/equivalencia_duplicatas.py >> logs/dup_equivalencia.log 2>&1; log "equivalencia: exit $?"
"$P25" -u scripts/79_serie_historica.py >> logs/serie_historica.log 2>&1; log "79: exit $?"
node repo/nucleo-dados-bdgd/etl/validate-serie-historica.mjs output-historico/2022-2025 repo/nucleo-dados-bdgd/web/public/data/historico/serie.json >> "$L" 2>&1; log "validador: exit $?"
log "oom1536 fim"
