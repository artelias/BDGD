"""Estágio final após 80/85/86/87; lê derivados existentes, não abre GDB/checkpoint.
Uso: python etl/bdgd2025/89_reconciliar_anomalias.py [raiz do projeto]
Depois: regenerar cenários 88 e motor_universal com os hashes do novo contrato.
"""
from pathlib import Path
import runpy,sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root))
from reconciliacao.derivados import apply
print(apply(root))
sys.argv=[str(root/'etl/bdgd2025/87_contrato_nacional.py'),str(root)]
runpy.run_path(sys.argv[0],run_name='__main__')
