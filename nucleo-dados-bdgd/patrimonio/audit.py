"""Auditoria de insumos existentes; inventário de arquivos não é leitura de registros."""
import csv
from collections import Counter,defaultdict
import gzip
import hashlib
import io
import json
from pathlib import Path
import zipfile
from .engine import load_dictionary,translate,technical


def export_rows(root,name,rows):
 import pyarrow as pa
 import pyarrow.parquet as pq
 rows=list(rows)
 if not rows:return
 pq.write_table(pa.Table.from_pylist(rows),root/(name+'.parquet'),compression='zstd')
 buf=io.StringIO(newline='');w=csv.DictWriter(buf,fieldnames=list(rows[0]));w.writeheader()
 for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in r.items()})
 (root/(name+'.csv.gz')).write_bytes(gzip.compress(buf.getvalue().encode(),mtime=0))


def audit(handoff,dictionary,output):
 root=Path(output);root.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(handoff) as z:
  name=next(n for n in z.namelist() if n.endswith('09_esquema_parquets/ESQUEMA_PARQUETS_ARQUIVOS.csv'))
  listed=list(csv.DictReader(io.StringIO(z.read(name).decode('utf-8-sig'))))
  schemas={}
  for name in z.namelist():
   if '/07_proveniencia_por_publicacao/' not in name or not name.endswith('/schema.csv'):continue
   pub=name.split('/')[-2]
   for r in csv.DictReader(io.StringIO(z.read(name).decode('utf-8-sig'))):
    key=(r['ano'],r['dist'],pub,r['entidade']);schemas.setdefault(key,set()).add(r['campo'])
  inventory=[]
  for r in listed:
   key=(r['ano'],r['dist'],r['item_id'],r['entidade']);fields=schemas.get(key)
   attrs=[f for f in ['TUC','A1','A2','A3','A4','A5','A6'] if fields and f in fields]
   inventory.append({'ANO':int(r['ano']),'DIST':r['dist'],'PUBLICACAO':r['item_id'],'ENTIDADE':r['entidade'],
    'LINHAS_LISTADAS':int(r['linhas']),'BYTES_LISTADOS':int(r['bytes']),'COLUNAS_LISTADAS':int(r['n_colunas']),
    'CAMPOS_DOCUMENTADOS':attrs,'LEITURA_REGISTROS_REALIZADA':False,'COBERTURA_VALORES_A1_A6':None,
    'ESTADO':'PARQUET_LISTADO_FORA_DO_AMBIENTE','SCHEMA_POR_ARQUIVO':'DISPONIVEL' if fields else 'AUSENTE',
    'POTENCIA_EXATA_RECUPERAVEL_KVA':None})
  export_rows(root,'inventario-cobertura',inventory)
  # Facts existentes registram marginais. Só TUC observada por entidade/ano, jamais cruzar marginais A1/A4.
  observed=[]
  for name in z.namelist():
   if '/07_proveniencia_por_publicacao/' not in name or not name.endswith('/facts.csv'):continue
   pub=name.split('/')[-2]
   for r in csv.DictReader(io.StringIO(z.read(name).decode('utf-8-sig'))):
    dim=r.get('dimensao',r.get('dim','')); value=r.get('categoria',r.get('valor_dimensao',r.get('valor_dim','')))
    if dim=='TUC':observed.append({'ANO':int(r['ano']),'DIST':r['dist'],'PUBLICACAO':pub,'ENTIDADE':r['entidade'],'TUC':value})
  export_rows(root,'tuc-observada',observed)
 # namespace comparisons, not false divergences from unequal code numbers in different systems
 diffs=[]
 for code in sorted({m['codigo'] for m in dictionary['tabelas']['IIIB']}):
  norm=[m for m in dictionary['tabelas']['IIIB'] if m['codigo']==code]
  dda=[m for m in dictionary['dda']['TPOTAPRT'] if str(m['COD_ID'])==str(int(code))]
  diffs.append({'CODIGO_MCPSE':code,'TABELA_MCPSE':'IIIB','DESCRICAO_MCPSE':[m['descricao'] for m in norm],
                'PAGINA_MCPSE':[m['pagina'] for m in norm],'CODIGO_DDA_MESMO_NUMERO':str(int(code)),
                'DESCRICAO_DDA':[m['DESCR'] for m in dda], 'VALOR_DDA_POT':[m.get('POT') for m in dda],
                'CLASSIFICACAO':'NAMESPACES_DISTINTOS_NAO_EQUIVALENTES','ELEGIVEL_CONVERSAO_AUTOMATICA':False})
 export_rows(root,'auditoria-potencia-namespaces',diffs)
 conflicts=[]
 for table,items in dictionary['tabelas'].items():
  groups=defaultdict(list)
  for item in items:groups[item['codigo']].append(item)
  for code,items in groups.items():
   if len({m['descricao'] for m in items})>1:conflicts.append({'TABELA':table,'CODIGO':code,'ALTERNATIVAS':items,'STATUS':'AMBIGUIDADE_DOCUMENTAL_NAO_ESCOLHER_VALOR'})
 export_rows(root,'ambiguidades-normativas',conflicts)
 exports=[]
 for tc,t in dictionary['tucs'].items():
  for bem,b in t['bens'].items():
   for slot in ['A1','A2','A3','A4','A5','A6']:
    spec=t.get('excecoes_a1',{}).get(bem,t.get('slots',{})).get(slot,{})
    table=spec.get('tabela','I' if slot=='A1' else None)
    if table=='CONDICIONAL:575:A4':table=t['tabelas_a4_por_a1'].get(bem)
    exports.append({'TUC':tc,'NOME_UC':t['nome'],'A1':bem,'BEM_DOCUMENTAL':b['descricao_documental'],'ATRIBUTO':slot,
      'SIGNIFICADO':spec.get('nome','Tipo de bem' if slot=='A1' else None),'TABELA':table,
      'PAGINA':b['pagina'] if slot=='A1' else spec.get('pagina'),'REVISAO_LIDA':dictionary['source']['revisao_lida'],
      'VIGENCIA_2022_2025':'PENDENTE_R3','ESTADO_SLOT':t['status_slots'],'ELEGIVEL_MODELO':False})
 export_rows(root,'dicionario-tuc-atributos',exports)
 summary={'schema_version':'auditoria-patrimonio-1','sha256_handoff':hashlib.sha256(Path(handoff).read_bytes()).hexdigest(),
  'arquivos_parquet_listados':len(inventory),'arquivos_parquet_com_registros_acessiveis':0,'linhas_lidas_de_registros':0,
  'anos_listados':sorted({r['ANO'] for r in inventory}),'dist_listadas':len({r['DIST'] for r in inventory}),
  'entidades_listadas':len({r['ENTIDADE'] for r in inventory}),'tucs_documentais':len(dictionary['tucs']),
  'tucs_com_slots_conferidos':sum(t['status_slots']=='CONFERIDO_DOCUMENTAL' for t in dictionary['tucs'].values()),
  'tucs_observadas_facts':sorted({r['TUC'] for r in observed}) if observed else None, 'motivo_sem_tuc_facts':'Facts nacionais não expõem dimensões TUC/A1–A6; não inferir distribuição conjunta a partir de totais', 'ambiguidades_documentais':len(conflicts),
  'tabela_IIIB':{'codigos':len(dictionary['tabelas']['IIIB']), 'valores_pontuais_inequivocos':sum(technical(x['descricao'])['valor_tecnico'] is not None for x in dictionary['tabelas']['IIIB'])},
  'potencia_recuperada_homologada_kva':None,'vigencias':dictionary['vigencias'],'revisao_lida':dictionary['source']['revisao_lida'],
  'pendencias':['PDF integral Revisão 3 e verificação de vigência normativa por competência','Parquets EQ/UN originais, existentes somente no disco D: listado no pacote','Slots não conferidos e descrições de bens em células mescladas','Comparabilidade DDA por ano e relacionamento EQ/UN validado'],
  'targets_modificados':False,'arquivos_gerados':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.iterdir()) if p.is_file() and p.name!='resumo.json'}}
 (root/'resumo.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 return summary
