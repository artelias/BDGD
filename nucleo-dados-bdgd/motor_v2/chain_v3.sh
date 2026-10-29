#!/bin/bash
cd /d/NUCLEO_BDGD_2025/wt-motor-v2/nucleo-dados-bdgd
PY=/d/NUCLEO_BDGD_2025/motor_v2/.venv/Scripts/python
for n in ucbt trafo_qty trafo_kva rede_mt; do PYTHONPATH=. $PY -X utf8 -W ignore -u -m motor_v2.runner --config motor_v2/v3_$n.json > /d/NUCLEO_BDGD_2025/motor_v2/comparative_v3_$n.log 2>&1; done
echo CHAIN_DONE > /d/NUCLEO_BDGD_2025/motor_v2/chain_v3.done
