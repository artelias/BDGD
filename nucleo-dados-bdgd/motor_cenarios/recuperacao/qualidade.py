"""Q1–Q9: usa a função científica única, com validação estrutural antes dela."""
import math
from .fontes import C, R

LADOS = ('conservador', 'agressivo')

def publicar(traj, natureza):
    return R.publicar(traj, natureza)

def checar(E, Epub, M, Mpub, y25, lado, disc, p01, p99):
    if lado not in LADOS:
        raise ValueError('Lado desconhecido')
    if not M or not Mpub:
        return 'SEM_MODERADO', {}
    if not E:
        return 'SEM_PROJECAO', {}
    if any(len(v) != len(C.HORIZONTE) for v in (E, M, Mpub)) or Epub is None or len(Epub) != 5:
        return 'CONTRATO_INVALIDO', {}
    if y25 is None or not math.isfinite(y25) or y25 <= 0 or any(not math.isfinite(x) or x <= 0 for x in M):
        return 'CONTRATO_INVALIDO', {}
    if p01 is None or p99 is None:
        return 'SEM_EVIDENCIA_PERCENTIS', {}
    if not all(math.isfinite(x) for x in (p01, p99)) or p01 > p99:
        return 'CONTRATO_INVALIDO', {}
    if any(isinstance(x, bool) or not math.isfinite(x) or x < 0 for x in E + Epub + Mpub):
        return 'IMPLAUSIVEL', {'Q1': False}
    if disc and any(type(x) is not int for x in Epub + Mpub):
        return 'IMPLAUSIVEL', {'Q9': False}
    if not disc and any(abs(x - round(x, 3)) > 1e-9 for x in Epub + Mpub):
        return 'IMPLAUSIVEL', {'Q9': False}
    return R.checar(E, Epub, M, Mpub, y25, lado, disc, p01, p99)

def classe(serie):
    if not serie.get('moderado'):
        return 'SEM_PREVISAO'
    if not all(serie.get(l) for l in LADOS):
        return 'PARCIAL'
    cats = [serie['extremos'][l]['categoria'] for l in LADOS]
    n = sum(c.startswith('A') for c in cats)
    return ('COMPLETA_CONDICIONAL', 'COMPLETA_MISTA', 'COMPLETA_INDEPENDENTE')[n]
