"""Pré-validação de futura matriz municipal; não rateia alvos/features DIST."""
from collections import defaultdict
import math
from .contracts import finite


def validate_municipal_mapping(mapping):
    if mapping.get('schema_version') != 'municipios-dist-1' or not mapping.get('dataset_version') or not mapping.get('rows'):
        raise ValueError('Contrato territorial sem versão/linhas')
    groups, keys = defaultdict(list), set()
    for row in mapping['rows']:
        if not isinstance(row.get('ano'), int) or isinstance(row['ano'], bool) or not 1900 <= row['ano'] <= 2100:
            raise ValueError('Ano territorial inválido')
        if not isinstance(row.get('municipio'), str) or len(row['municipio']) != 7 or not row['municipio'].isdigit():
            raise ValueError('Município deve usar código IBGE de sete dígitos')
        if not isinstance(row.get('DIST'), str) or not row['DIST'].isdigit() or int(row['DIST']) <= 0 or str(int(row['DIST'])) != row['DIST']:
            raise ValueError('DIST territorial inválida')
        if not finite(row.get('peso')) or not 0 < row['peso'] <= 1 or not row.get('fonte') or not row.get('populacao_peso'):
            raise ValueError('Peso/fonte/população territorial inválido')
        key = row['ano'], row['municipio'], row['DIST']
        if key in keys: raise ValueError('Vínculo municipal duplicado')
        keys.add(key); groups[key[:2]].append(row)
    for rows in groups.values():
        if len({r['populacao_peso'] for r in rows}) != 1 or not math.isclose(sum(r['peso'] for r in rows), 1, rel_tol=0, abs_tol=1e-9):
            raise ValueError('Município multi-DIST sem rateio coerente: soma de pesos deve ser 1')
        if len(rows) > 1 and any(not r.get('evidencia_rateio') for r in rows):
            raise ValueError('Município multi-DIST exige evidência de rateio por população')
    return {'vinculos': len(keys), 'municipios_ano': len(groups), 'agregacao_ativada': False,
            'nota': 'Pré-validação de contrato; não certifica geografia nem autoriza aplicar pesos a outra variável'}
