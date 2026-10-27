"""Tradução rastreável, sem imputação de alvos nem homologaçāo normativa automática."""
from decimal import Decimal
import json
from pathlib import Path
import re

ROOT=Path(__file__).parent

def load_dictionary(path=None):
 d=json.loads(Path(path or ROOT/'data/dicionario.json').read_text())
 if d.get('schema_version')!='patrimonio-mcpse-1':raise ValueError('Dicionário incompatível')
 return d


def code(value, width):
 if value is None: return None
 if isinstance(value,bool):raise ValueError('Booleano não é código patrimonial')
 if isinstance(value,int): value=str(value)
 if not isinstance(value,str):raise ValueError('Código deve ser texto ou inteiro; sem arredondamento')
 v=value.strip()
 if not v:return None
 if re.fullmatch(r'[0-9]+',v):return v.zfill(width) if len(v)<=width else v
 return v


def technical(text):
 """Retorna escalar somente para uma grandeza pontual inequívoca; faixas ficam faixas."""
 pattern=r'([0-9]+(?:[.,][0-9]+)?)\s*(MVA|kVA|kVAR|kV|V|kA|daN|A|m|mm²|AWG|MCM)\b'
 matches=re.findall(pattern,text,re.I)
 quantities=[]
 for n,u in matches:
  units={'mva':('kVA',Decimal('1000')),'kva':('kVA',Decimal(1)),'kvar':('kvar',Decimal(1)),
         'kv':('kV',Decimal(1)),'v':('V',Decimal(1)),'ka':('kA',Decimal(1)),'a':('A',Decimal(1)),
         'dan':('daN',Decimal(1)),'m':('m',Decimal(1)),'mm²':('mm²',Decimal(1)),'awg':('AWG',Decimal(1)),'mcm':('MCM',Decimal(1))}
  unit,factor=units[u.lower()]
  ambiguous=bool(re.fullmatch(r'[0-9]+\.[0-9]{3}',n))
  quantities.append({'valor':None if ambiguous else str(Decimal(n.replace(',','.'))*factor),'unidade':unit,'numero_original':n,'pontuacao_ambigua':ambiguous})
 interval=bool(re.search(r'\bat[eé]\b|acima|abaixo|anterior|superior|inferior|maior|menor|[<>≤≥]',text,re.I))
 scalar=quantities[0] if len(quantities)==1 and quantities[0]['valor'] is not None and not interval and not any(c in text for c in [';','/','+','X','x','√']) else None
 return {'valor_tecnico':scalar['valor'] if scalar else None,'unidade':scalar['unidade'] if scalar else quantities[0]['unidade'] if quantities and len({q['unidade'] for q in quantities})==1 else None,
         'natureza_valor':'FAIXA' if interval else 'PONTUAL' if scalar else 'COMPOSTO_OU_CATEGORICO', 'componentes':quantities}


def translate(dictionary, tuc, a1, slot, value, year):
 if slot not in {'A1','A2','A3','A4','A5','A6'}:raise ValueError('Slot deve ser A1–A6')
 if not isinstance(year,int) or isinstance(year,bool):raise ValueError('Ano inteiro obrigatório')
 tc,bem,cv=code(tuc,3),code(a1,2),code(value,2)
 result={'TUC_original':tuc,'A1_original':a1,'slot':slot,'codigo_original':value,'tuc':tc,'a1':bem,'codigo':cv,
  'descricao':None,'valor_tecnico':None,'unidade':None,'tabela':None,'pagina':None,'fonte':dictionary['source'],
  'vigencia':dictionary['vigencias'].get(str(year),{'status':'ANO_FORA_DO_ESCOPO'}), 'elegivel_feature':False}
 if cv is None:return {**result,'status':'VAZIO'}
 if cv.upper() in {'NA','N/A','NÃO APLICÁVEL','NAO_APLICAVEL'}:return {**result,'status':'NAO_APLICAVEL_DECLARADO'}
 t=dictionary['tucs'].get(tc)
 if not t:return {**result,'status':'TUC_NAO_TRADUZIDO'}
 if slot=='A1':
  b=t['bens'].get(cv)
  return {**result,'status':b['status'] if b else 'CODIGO_NAO_TRADUZIDO','descricao':b['descricao_documental'] if b else None,
          'tabela':'I','pagina':b['pagina'] if b else None}
 if bem not in t['bens']:return {**result,'status':'A1_NAO_TRADUZIDO'}
 specs=t.get('excecoes_a1',{}).get(bem,t.get('slots',{}))
 spec=specs.get(slot)
 if not spec:return {**result,'status':'NAO_APLICAVEL_DOCUMENTAL' if t['status_slots']=='CONFERIDO_DOCUMENTAL' else 'SLOT_NAO_VERIFICADO'}
 table=spec['tabela']
 if table=='CONDICIONAL:575:A4':table=t['tabelas_a4_por_a1'].get(bem)
 result.update(nome_atributo=spec['nome'],tabela=table,pagina=spec['pagina'])
 if table and table.startswith('EMPRESA'):return {**result,'status':'CODIFICACAO_DA_EMPRESA'}
 matches=[m for m in dictionary['tabelas'].get(table,[]) if m['codigo']==cv]
 if not matches:return {**result,'status':'CODIGO_NAO_TRADUZIDO'}
 unique={m['descricao'] for m in matches}
 if len(unique)>1:return {**result,'status':'CODIGO_AMBIGUO','alternativas':matches}
 m=matches[0]
 if m.get('restricao_asterisco'):return {**result,'status':'RESTRICAO_CONTEXTUAL_PENDENTE','descricao':m['descricao'],'pagina':m['pagina']}
 return {**result,**technical(m['descricao']),'descricao':m['descricao'],'pagina':m['pagina'],'status':'TRADUZIDO_DOCUMENTAL'}


def enrich_record(dictionary, row, *, entity, dist, year, publication):
 if not publication:raise ValueError('Proveniência da publicação obrigatória')
 if str(row.get('DIST',dist))!=str(dist):raise ValueError('DIST do registro diverge do escopo')
 if row.get('COD_ID') is None or not str(row['COD_ID']).strip():raise ValueError('COD_ID obrigatório para auditoria de cardinalidade')
 t,a=row.get('TUC'),row.get('A1')
 attrs={s:translate(dictionary,t,a,s,row.get(s),year) for s in ['A1','A2','A3','A4','A5','A6']}
 power_slot=next((s for s,v in attrs.items() if v.get('nome_atributo')=='POTÊNCIA'),None)
 candidate=attrs.get(power_slot,{})
 # Não usar POT_NOM como A4: namespaces DDA e MCPSE distintos.
 native=None
 if entity in {'EQTRMT','EQTRAT','EQRE'} and row.get('POT_NOM') not in {None,''}:
  k=code(row['POT_NOM'],1)
  matches=[v for v in dictionary['dda'].get('TPOTAPRT',[]) if str(v['COD_ID'])==k and k!='0']
  if len(matches)==1 and matches[0].get('POT') is not None:
   native={'codigo_original':row['POT_NOM'],'descricao':matches[0].get('DESCR'),'valor_candidato_kva':str(matches[0]['POT']),
           'dominio':'TPOTAPRT','status':'DDA_DOCUMENTAL_VIGENCIA_PENDENTE'}
 elif entity in {'UNTRMT','UNTRAT'} and row.get('POT_NOM') not in {None,''}:
  native={'valor_original':row['POT_NOM'],'status':'UNIDADE_E_COMPARABILIDADE_A_CONFIRMAR_POR_ANO','valor_candidato_kva':None}
 return {'DIST':str(dist),'ANO':year,'PUBLICACAO':publication,'ENTIDADE':entity,'COD_ID':str(row['COD_ID']),
         'TUC':code(t,3),'A1':code(a,2),'atributos':attrs,'fonte_registro_preservada':True,
         'somavel_com_eq':False if entity.startswith('UN') else None,
         'potencia':{'slot':power_slot,'documental':candidate,'campo_nativo':native,
                     'potencia_recuperada_homologada_kva':None,'elegivel_modelo':False,
                     'motivo':'SEM_VIGENCIA_E_COMPARABILIDADE_VERIFICADAS; faixa patrimonial não define potência exata'}}
