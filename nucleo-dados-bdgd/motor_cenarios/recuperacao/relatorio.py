"""Comparação exata por série; nenhum total mistura conceitos nem namespaces UN/EQ."""
import csv
import json
from collections import Counter, defaultdict
from .qualidade import LADOS

COLUNAS = 'DIST EMPRESA CONCEITO_ID METRICA UNIDADE STATUS_ANTERIOR STATUS_NOVO MODERADO_MODELO CONSERVADOR_MODELO AGRESSIVO_MODELO CONSERVADOR_TIPO AGRESSIVO_TIPO WAPE_REFERENCIA WAPE_CANDIDATO R2_CRESCIMENTO GANHO_COBERTURA MOTIVO_RECUPERACAO MOTIVO_BLOQUEIO STATUS_CIENTIFICO HASH_PROVENIENCIA'.split()

def status(s):
    n = sum(bool(s.get(l)) for l in (*LADOS, 'moderado'))
    return 'COMPLETA' if n == 3 else 'PARCIAL' if n else 'SEM_PREVISAO'

def linhas(produto, empresas):
    rows, trajectories = [], []
    for m in produto['metricas']:
        for d, s in sorted(m['series'].items(), key=lambda x: int(x[0])):
            ex = s['extremos']
            get = lambda l, field: (ex[l] or {}).get(field)
            old, new = status(s['anteriores']), status(s)
            rows.append(dict(zip(COLUNAS, [d, empresas.get(d, ''), m['conceito'], m['metrica'], m['unidade'], old, new,
                m['cenarios']['moderado'] if s['moderado'] else None, get('conservador','modelo'), get('agressivo','modelo'),
                get('conservador','natureza'), get('agressivo','natureza'), m['modelos'].get(m['cenarios']['moderado'],{}).get('wape'),
                {l:get(l,'wape_candidato') for l in LADOS}, {l:get(l,'r2_crescimento') for l in LADOS},
                int(new=='COMPLETA')-int(old=='COMPLETA'),
                {l:v for l,v in s['motivos_experimentais'].items() if s[l]},
                {l:v for l,v in s['motivos_experimentais'].items() if not s[l]}, s['estado_cientifico'], s['hash_proveniencia']])))
            for side in ('conservador','moderado','agressivo'):
                trajectory = s[side]
                trajectories.append(dict(DIST=d, CONCEITO_ID=m['conceito'], METRICA=m['metrica'], UNIDADE=m['unidade'],
                    cenario=side, modelo_serie=m['cenarios']['moderado'] if side=='moderado' and trajectory else (ex.get(side) or {}).get('modelo'),
                    categoria='MODERADO_PRESERVADO' if side=='moderado' and trajectory else (ex.get(side) or {}).get('categoria'),
                    motivo=s['motivos_experimentais'].get(side), **{str(y):trajectory[i] if trajectory else None for i,y in enumerate(range(2026,2031))}))
    return rows, trajectories

def cobertura(rows, produto):
    groups = defaultdict(list)
    for r in rows:
        for level, key in [('nacional','TODAS'),('metrica',r['CONCEITO_ID']+'/'+r['METRICA']),('distribuidora',r['DIST'])]:
            groups[(level,key)].append(r)
        if r['UNIDADE'] != 'kVA':
            groups[('nacional','SEM_KVA')].append(r)
    out=[]
    for (level,key), values in sorted(groups.items()):
        before=Counter(r['STATUS_ANTERIOR'] for r in values); after=Counter(r['STATUS_NOVO'] for r in values)
        out.append(dict(nivel=level,chave=key,series=len(values),antes=dict(before),depois=dict(after),
                        ganho_completas=after['COMPLETA']-before['COMPLETA'],
                        recuperadas=sum(r['STATUS_ANTERIOR']!='COMPLETA' and r['STATUS_NOVO']=='COMPLETA' for r in values),
                        perderam_completude=sum(r['STATUS_ANTERIOR']=='COMPLETA' and r['STATUS_NOVO']!='COMPLETA' for r in values)))
    total=next(r for r in out if r['nivel']=='nacional' and r['chave']=='TODAS')
    before=sum(bool(s['anteriores'][l]) for m in produto['metricas'] for s in m['series'].values() for l in LADOS)
    after=Counter(e['natureza'] for m in produto['metricas'] for s in m['series'].values() for e in s['extremos'].values() if e)
    blocked=Counter(v.split(':')[0] for m in produto['metricas'] for s in m['series'].values() for l,v in s['motivos_experimentais'].items() if not s[l])
    return dict(nacional=total, extremos_antes={'independente':before,'condicional':0}, extremos_depois=dict(after),
                bloqueios_depois=dict(blocked), por_grupo=out)

def csv_write(path, rows, fields=None):
    rows=list(rows)
    with path.open('w', encoding='utf-8', newline='') as f:
        w=csv.DictWriter(f, fieldnames=fields or list(rows[0]), lineterminator='\n')
        w.writeheader()
        for row in rows:
            w.writerow({k:json.dumps(v,ensure_ascii=False,sort_keys=True,allow_nan=False) if isinstance(v,(dict,list)) else v for k,v in row.items()})
