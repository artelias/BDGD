"""Porta de entrada para o motor: tradução documental não comprova comparabilidade."""

def to_feature(translation, *, referencia, disponivel_em, fonte, versao):
    if not translation.get('elegivel_feature'):
        raise ValueError('FEATURE_PATRIMONIAL_BLOQUEADA_POR_VIGENCIA_OU_COMPARABILIDADE')
    if not all([referencia, disponivel_em, fonte, versao]):
        raise ValueError('Metadados da feature patrimonial incompletos')
    return {'valor':translation['valor_tecnico'],'unidade':translation['unidade'],'referencia':referencia,
            'disponivel_em':disponivel_em,'fonte':fonte,'versao':versao}
