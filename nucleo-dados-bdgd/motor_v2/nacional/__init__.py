"""National experimental run of Motor V2 (internal; never written to public products).

Kept in a subpackage on purpose: the executors fingerprint the top-level motor_v2/*.py files, so orchestration and reporting
code can evolve here without invalidating extraction/comparison checkpoints that are already running."""
from pathlib import Path

ROOT_OUT = Path('D:/NUCLEO_BDGD_2025/motor_v2/nacional')
CONTRACT = Path(__file__).resolve().parents[2] / 'output-historico/contrato-integracao/serie_fisica_nacional.csv'
GROUPS = Path(__file__).resolve().parents[2] / 'etl/bdgd2025/config/grupos_2025.json'
LEVEL_A = ('ucbt_quantidade', 'trafo_dist_quantidade', 'trafo_dist_potencia_kva', 'rede_mt_extensao_km', 'rede_bt_extensao_km')
BATCH = 16
