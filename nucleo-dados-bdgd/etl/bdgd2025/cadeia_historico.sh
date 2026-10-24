#!/usr/bin/env bash
# Cadeia de homologacao historica, em serie (nunca em paralelo ao runner): aguarda o run.py terminar e executa
# duplicatas -> equivalencia integral -> regra 2025 (78) -> serie (79) -> validador. Log: logs/cadeia_historico.log
set -u
L=/d/NUCLEO_BDGD_2025/logs/cadeia_historico.log
H=/d/NUCLEO_BDGD_2022_2024
P25=/d/NUCLEO_BDGD_2025/.venv/Scripts/python.exe
PH=$H/.venv/Scripts/python.exe
log() { echo "$(date -Iseconds) $*" >> "$L"; }
ativo() { powershell -NoProfile -Command "@(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { \$_.CommandLine -like '*historico\\run.py*' -or \$_.CommandLine -like '*historico/run.py*' }).Count"; }
log "inicio: aguardando o runner"
while [ "$(ativo | tr -d '\r')" != "0" ]; do sleep 120; done
log "runner encerrado: $(tail -1 $H/logs/run5.stdout.log)"
cd "$H" && BDGD_DUCKDB_MEM=768MB "$PH" -u /d/NUCLEO_BDGD_2025/scripts/duplicatas_historico.py --memory-mb 768 >> /d/NUCLEO_BDGD_2025/logs/dup_driver.log 2>&1; log "duplicatas: exit $?"
cd /d/NUCLEO_BDGD_2025 && BDGD_DUCKDB_MEM=768MB "$P25" -u scripts/78_conceitos_historico.py >> logs/conceitos_hist.log 2>&1; log "78: exit $?"
BDGD_DUCKDB_MEM=768MB "$P25" -u scripts/equivalencia_duplicatas.py >> logs/dup_equivalencia.log 2>&1; log "equivalencia: exit $?"
"$P25" -u scripts/79_serie_historica.py >> logs/serie_historica.log 2>&1; log "79: exit $?"
node repo/nucleo-dados-bdgd/etl/validate-serie-historica.mjs output-historico/2022-2025 repo/nucleo-dados-bdgd/web/public/data/historico/serie.json >> "$L" 2>&1; log "validador: exit $?"
log "fim"
