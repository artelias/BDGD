#!/bin/bash
cd "$(dirname "$0")/.."
PY=/d/NUCLEO_BDGD_2025/motor_v2/.venv/Scripts/python
for n in trafo_qty_strict trafo_kva_strict rede_mt_strict trafo_qty_coverage; do PYTHONPATH=. $PY -X utf8 -W ignore -u -m motor_v2.runner --config motor_v2/cmp_$n.json > /d/NUCLEO_BDGD_2025/motor_v2/comparative_assets_$n.log 2>&1; done
echo CHAIN_DONE > /d/NUCLEO_BDGD_2025/motor_v2/chain_assets.done
