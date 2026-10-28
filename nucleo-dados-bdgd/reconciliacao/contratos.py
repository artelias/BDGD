import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def observacoes(root=ROOT):
    doc=json.loads((Path(root)/'auditoria/reconciliacao/observacoes.json').read_text())
    if doc['schema_version']!='observacoes-bdgd-1' or doc['sintetico'] is not False:raise ValueError('Contrato de observações inválido')
    rows=doc['observacoes'];keys=[(x['dist'],x['ano'],x['ativo'],x['metrica']) for x in rows]
    if len(keys)!=len(set(keys)):raise ValueError('Observação duplicada')
    return rows

def anotar_contrato(rows,root=ROOT):
    notes={(x['dist'],x['ano'],x['ativo'],x['metrica']):x for x in observacoes(root)}
    for row in rows:
        key=(int(row['dist']),int(row['ano']),row['conceitoId'],row['metrica']);note=notes.get(key)
        row.update(observacao_id=note['id'] if note else None,subtotal_observado=note['subtotal_observado'] if note else None,
                   valores_publicados_json=json.dumps(note['valores_publicados'],sort_keys=True) if note else None)
        if note and note['bloqueia_total']:
            row.update(valor=None,cobertura=None)
            # Não substituir nem promover decisões humanas preexistentes.
            if row['estado'] in ['observado','zero_verificado']:row.update(estado='ausente',tipo_lacuna='AUSENCIA_CADASTRAL_NA_PUBLICACAO')
            row['motivo_nd']=note['problema']+' '+note['tratamento']
    return rows
