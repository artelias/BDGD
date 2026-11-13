"""Contrato do módulo: estados, fórmulas e regras. Só biblioteca padrão; as fórmulas são testadas em tests/.

Regras centrais (PRODIST Módulo 8):
  * DEC e FEC do conjunto são médias por unidade consumidora: DEC = Σ DIC / Cc e FEC = Σ FIC / Cc no período de apuração.
    Somar DIC ou FIC dá o NUMERADOR, nunca o indicador.
  * O valor anual do conjunto é a soma dos 12 valores mensais apurados (cada mês com o seu próprio Cc).
  * O valor de um agregado de conjuntos (distribuidora, grupo) em um mês é a média ponderada pelo número de consumidores
    de cada conjunto no mês; o anual do agregado é a soma dos meses. Nunca a média simples dos conjuntos.
  * Ausência não é zero: None permanece None e sai das somas, com a contagem do que faltou.
"""
import math

VERSAO_CONTRATO = 'confiabilidade-1'
ANOS = (2022, 2023, 2024, 2025)          # competências BDGD permitidas; a continuidade é restrita ao mesmo intervalo

OBSERVADO_OFICIAL = 'OBSERVADO_OFICIAL'              # publicado pela ANEEL
RECONSTRUIDO_VALIDADO = 'RECONSTRUIDO_VALIDADO'      # calculado da BDGD e reconciliado com o oficial dentro da tolerância
DERIVADO_EXPLORATORIO = 'DERIVADO_EXPLORATORIO'      # calculado neste módulo, sem homologação
DADO_INDISPONIVEL = 'DADO_INDISPONIVEL'
DEMONSTRATIVO_SINTETICO = 'DEMONSTRATIVO_SINTETICO'  # só em testes; nunca em produto público
ESTADOS = (OBSERVADO_OFICIAL, RECONSTRUIDO_VALIDADO, DERIVADO_EXPLORATORIO, DADO_INDISPONIVEL, DEMONSTRATIVO_SINTETICO)

SUPRESSAO_K = 5                # contagens de consumidores de 1 a K-1 em recortes finos (alimentador) não são publicadas
TOL_RECONSTRUCAO = 0.05        # |reconstruído − oficial| / oficial ≤ 5% no ano para o estado RECONSTRUIDO_VALIDADO
TOL_RECONSTRUCAO_ABS = 0.05    # ou diferença absoluta ≤ 0,05 (h ou interrupções) quando o oficial é pequeno

# Classes de unidade seccionadora MT (UNSEMT.TIP_UNID, domínio TUNI do DDA M10). Instalações, não equipamentos.
CLASSES_SECCIONAMENTO = {
    'fusivel': {22, 23, 24, 25, 26, 27, 46},
    'religador': {32},
    'seccionalizador': {35, 36},
    'disjuntor': {29, 30, 53},
    'manobra': {15, 16, 17, 18, 19, 20, 21, 28, 31, 33, 34, 47, 48, 49, 50},
}


def finito(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def anual(mensais):
    """Valor anual do conjunto = soma dos meses apurados. -> (valor|None, meses_com_valor, completo)."""
    v = [x for x in mensais if finito(x)]
    return (math.fsum(v) if v else None, len(v), len(v) == 12 and len(mensais) == 12)


def agregado_mensal(pares):
    """Média ponderada por consumidores de um mês. pares = [(indicador, consumidores)]. -> (valor|None, n_usados, n_fora)."""
    num = den = 0.0
    usados = fora = 0
    for v, c in pares:
        if finito(v) and finito(c) and c > 0:
            num += v * c; den += c; usados += 1
        else:
            fora += 1
    return (num / den if den > 0 else None, usados, fora)


def agregado_anual(meses):
    """meses = 12 listas de pares (indicador, consumidores) -> (valor|None, meses_com_valor, completo)."""
    return anual([agregado_mensal(p)[0] for p in meses])


def razao_limite(observado, limite):
    """Observado / limite. None quando falta um dos dois ou o limite não é positivo."""
    if not finito(observado) or not finito(limite) or limite <= 0:
        return None
    return observado / limite


def situacao_limite(observado, limite):
    r = razao_limite(observado, limite)
    return 'ND' if r is None else 'ACIMA' if r > 1 else 'DENTRO'


def razao(a, b):
    """a / b com ausência preservada (None se faltar um lado ou se b não for positivo)."""
    if not finito(a) or not finito(b) or b <= 0:
        return None
    return a / b


def suprimir(n, k=SUPRESSAO_K):
    """Contagem de consumidores em recorte fino: 0 e n ≥ k passam; 1..k−1 viram None (suprimido)."""
    if n is None:
        return None
    return n if n == 0 or n >= k else None


def gini(valores):
    """Índice de Gini de valores não negativos (0 = distribuição igual; →1 = concentrada). None com menos de 2 valores."""
    v = sorted(x for x in valores if finito(x) and x >= 0)
    n, s = len(v), math.fsum(v)
    if n < 2 or s <= 0:
        return None
    acum = math.fsum((i + 1) * x for i, x in enumerate(v))
    return (2 * acum) / (n * s) - (n + 1) / n


def participacao_maiores(valores, k):
    """Parcela do total que está nos k maiores valores. None sem total positivo."""
    v = sorted((x for x in valores if finito(x) and x >= 0), reverse=True)
    s = math.fsum(v)
    return math.fsum(v[:k]) / s if s > 0 else None


def classe_seccionamento(tip_unid):
    try:
        t = int(tip_unid)
    except (TypeError, ValueError):
        return 'outros'
    return next((k for k, s in CLASSES_SECCIONAMENTO.items() if t in s), 'outros')


def reconciliado(reconstruido, oficial):
    """True se o reconstruído reproduz o oficial dentro da tolerância do contrato; None se faltar um lado."""
    if not finito(reconstruido) or not finito(oficial):
        return None
    d = abs(reconstruido - oficial)
    return d <= TOL_RECONSTRUCAO_ABS or (oficial > 0 and d / oficial <= TOL_RECONSTRUCAO)
