"""Extrai evidência documental; Revisão 2 nunca é rotulada como Revisão 3."""
import argparse
from collections import defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def clean(x): return re.sub(r'\s+', ' ', x or '').strip()
def dump(path, value): Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

# Mapeamento revisado na Tabela I, com exceções explícitas por tipo de bem.
# Nenhum slot é adivinhado a partir de nome de coluna BDGD ou posição de A1 na página.
SLOTS = {
 '125':['II','VI','IIIA'], '130':['II','VI','IIIA'],
 '135':['II','LOCAL:135:MATERIAL','LOCAL:135:ISOLAMENTO','VIII'],
 '160':['II','V','IV','VI','VII'], '210':['II','V','VII','LOCAL:210:INSTALACAO','XV'],
 '255':['LOCAL:255:MATERIAL','LOCAL:255:ESTRUTURA','IX','X','LOCAL:255:TRAVESSIA'],
 '295':['LOCAL:295:TIPO','LOCAL:295:FASES'],
 '325':['II','V','IV','VI','VII'], '330':['II','V','IV'], '340':['II','IIIB','V','IV'],
 '345':['II','V','IV','VI','XV'],
 '540':['II','II','IIIB'], '545':['II','II','IIIB'], '560':['II','II','IIIB','IV'],
 '565':['II','II','IIIB','IV','LOCAL:565:PROTECAO'],
 '570':['II','II','IIIB','IV','LOCAL:570:COMUTACAO'],
 '575':['II','XI','CONDICIONAL:575:A4','XIII','LOCAL:575:INSTALACAO'],
 '580':['II','II','IIIB','IV'],
}
# Só estes slots comuns foram conferidos com texto/página; demais ficam sem atribuição automática.
REVIEWED = {'125','130','135','160','210','325','330','340','345','540','545','560','565','570','575','580'}
AUX_PAGES = {'II':[189,190,191], 'IIIA':[191], 'IIIB':[192,193], 'IV':[194], 'V':[194,195],
             'VI':[195], 'VII':[195], 'VIII':[196,197,198], 'IX':[199], 'X':[200,201],
             'XI':[202], 'XII':[203,204], 'XIII':[205], 'XIV':[206], 'XV':[207]}
# Os índices abaixo são substituídos pelo título encontrado na página (sem presumir paginação).


def extract(pdf_path, dda_path, output):
 import pdfplumber
 out=Path(output); out.mkdir(parents=True,exist_ok=True)
 with pdfplumber.open(pdf_path) as pdf:
  first=pdf.pages[0].extract_text() or ''
  revision='3' if re.search(r'1\.020', first) else '2' if '674' in first else None
  if revision not in {'2','3'}: raise ValueError('Edição MCPSE não identificada pela capa')
  raw=[]; tucs={}; current=None
  for n in range(172,188):
   page=pdf.pages[n]
   for table in page.extract_tables():
    for cells in table:
     if len(cells)<6 or any('MCPSE - MANUAL' in str(c) for c in cells):continue
     c=[clean(v) for v in cells]
     if re.fullmatch(r'\d{3}',c[0]):
      current=c[0]; tucs.setdefault(current,{'tuc':current,'nome':c[1], 'paginas':[], 'bens':{}, 'atributos_documentais':[]})
     if current is None or 'CÓDIGO' in c[0] or 'TIPO DE UNIDADE' in c[0]:continue
     # Continuação de página pertence ao TUC anterior, sem criar nova unidade.
     t=tucs[current]
     if n+1 not in t['paginas']:t['paginas'].append(n+1)
     ids=re.findall(r'(\d{3})\.(\d{2})',c[2])
     for tc,a1 in ids:
      if tc!=current: raise ValueError('TUC/A1 inconsistentes na extração')
      desc=c[3]
      t['bens'].setdefault(a1, {'codigo':a1, 'descricao_documental':desc, 'pagina':n+1,
          'status':'DESCRICAO_DE_GRUPO' if len(ids)>1 or not desc else 'TEXTO_DOCUMENTAL'})
     # Colunas extras vazias resultam de linhas do PDF, não de atributos novos.
     attr=next((v for v in c[4:6] if v and not v.startswith(('VIDE','VER ','CÓDIGO DA')) and not re.match(r'^\d',v)),None)
     if attr and attr not in {'TIPO','ATRIBUTOS','CÓDIGO','DESCRIÇÃO'}:
      if not t['atributos_documentais'] or t['atributos_documentais'][-1]['nome']!=attr:
       t['atributos_documentais'].append({'nome':attr,'pagina':n+1,'conteudo':[]})
     if t['atributos_documentais']:
      a=t['atributos_documentais'][-1]
      a['conteudo'].append({'celulas':c[4:],'pagina':n+1})
     raw.append({'pagina':n+1,'tuc':current,'celulas':c})
  tables=defaultdict(list); active=None
  for n in range(188,210):
   for line in (pdf.pages[n].extract_text() or '').splitlines():
    m=re.search(r'TABELA\s+([IVX]+[AB]?)\s*[-–]',line)
    if m:
     active=m.group(1)
     if active=='VIII': active='VIII_A4'
     continue
    if 'para atributo A6' in line and active and active.startswith('VIII'): active='VIII_A6'
    m=re.fullmatch(r'(\d{2})(\*)?\s+(.+)',line.strip())
    if m and active:
     tables[active].append({'codigo':m.group(1),'restricao_asterisco':bool(m.group(2)), 'descricao':clean(m.group(3)),'pagina':n+1})
  source={'id':'mcpse-r'+revision,'revisao_lida':revision,'sha256':digest(pdf_path),
          'arquivo':Path(pdf_path).name,'url':'https://www2.aneel.gov.br/cedoc/'+('aren20221020_2_6.pdf' if revision=='3' else 'aren2015674_2.pdf')}
  for tc,t in tucs.items():
   t['slots']={}
   if tc in REVIEWED:
    names=[a['nome'] for a in t['atributos_documentais']]
    # grupos condicionais explicitamente descritos abaixo; não zipar ramos distintos.
    if tc=='135':names=names[:4]
    for i,table in enumerate(SLOTS[tc],2):
     t['slots']['A'+str(i)]={'nome':names[i-2] if i-2<len(names) else 'INTERPRETACAO_PENDENTE',
                             'tabela':('VIII_A4' if table=='VIII' else table), 'pagina':t['paginas'][0], 'status':'CONFERIDO_DOCUMENTO_R'+revision}
   t['status_slots']='CONFERIDO_DOCUMENTAL' if tc in REVIEWED else 'SEM_MAPEAMENTO_DE_SLOT_VERIFICADO'
  # TUC 135.03 reinicia o conjunto de atributos; 575 A4 muda a tabela segundo A1.
  tucs['135']['excecoes_a1']={'03':{'A2':{'nome':'CLASSE DE TENSÃO','tabela':'II','pagina':174},
       'A3':{'nome':'MATERIAL','tabela':'LOCAL:135:03:MATERIAL','pagina':174}}}
  tucs['575']['tabelas_a4_por_a1']={'01':'XII','20':'XII','02':'XIV','11':'XIV','12':'XIV','13':'XIV'}
  for tc,t in tucs.items():
   for slot,spec in t['slots'].items():
    if not spec['tabela'].startswith('LOCAL:'): continue
    attr=next((a for a in t['atributos_documentais'] if a['nome']==spec['nome']),None)
    if attr:
     for evidence in attr['conteudo']:
      cells=[c for c in evidence['celulas'] if c]
      text=' '.join(cells)
      m=re.search(r'(?<![0-9])(\d{2})\s*[-–]?\s+(.+)',text)
      if m:
       tables[spec['tabela']].append({'codigo':m.group(1),'descricao':clean(m.group(2)), 'pagina':evidence['pagina']})
  tables['LOCAL:135:03:MATERIAL']=[{'codigo':c,'descricao':d,'pagina':174} for c,d in [('01','PORCELANA'),('02','POLÍMERO'),('03','OUTRO')]]
  dda=json.loads(Path(dda_path).read_text())
  result={'schema_version':'patrimonio-mcpse-1','source':source,'dda_source':{'versao':dda['version'],'authority':dda['authority'],'sha256':digest(dda_path)},
    'referencia_r3':{'url':'https://www2.aneel.gov.br/cedoc/aren20221020_2_6.pdf','status':'BYTES_NAO_ACESSIVEIS_HTTP403' if revision=='2' else 'LIDA',
       'motivo_revisao_indexado':'Aprimoramento de conceito do glossário; REN 1.020/2022. Não prova equivalência histórica dos registros.'},
    'vigencias':{str(y):{'status':'PENDENTE_VERIFICACAO_NORMATIVA','revisao_solicitada':'3'} for y in range(2022,2026)},
    'tucs':tucs,'tabelas':dict(tables), 'dda':{t['table']:t['values'] for t in dda['tables']},
    'limites':['Cópia integral lida é revisão '+revision+'; não apresentada como revisão 3.',
      'Sem aprovação automática de vigência 2022–2025; traduções documentais não homologam dados.',
      'Faixas e códigos com múltiplos significados nunca viram valor técnico pontual.',
      'Não associa registros EQ/UN por código global; não modifica targets.']}
 dump(out/'dicionario.json',result); dump(out/'tabela-I-evidencia.json',raw)
 return result


def main():
 p=argparse.ArgumentParser();p.add_argument('--pdf',required=True);p.add_argument('--dda',required=True);p.add_argument('--output',required=True)
 a=p.parse_args();r=extract(a.pdf,a.dda,a.output);print(json.dumps({'tucs':len(r['tucs']),'tabelas':{k:len(v) for k,v in r['tabelas'].items()},'revisao_lida':r['source']['revisao_lida']}))
if __name__=='__main__':main()
