"""Leitura em lotes de Parquets existentes. Saída independente, sem junção EQ/UN."""
import hashlib
import json
import sqlite3
from pathlib import Path
from .engine import enrich_record


def hashfile(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
 return h.hexdigest()


def enrich_parquets(manifest, dictionary, output):
 import pyarrow as pa
 import pyarrow.parquet as pq
 out=Path(output);out.mkdir(parents=True,exist_ok=False)
 db=sqlite3.connect(out/'_cardinalidade.sqlite')
 db.execute('CREATE TABLE seen(dist TEXT, ano INTEGER, entidade TEXT, pub TEXT, cod TEXT, PRIMARY KEY(dist,ano,entidade,pub,cod)) WITHOUT ROWID')
 inventory=[]; outputs=[]
 # A lista deve vir de seleção formal do fornecedor, não de um glob que aprova republicações.
 if not manifest.get('dataset_version') or manifest.get('schema_version')!='parquets-patrimonio-1':raise ValueError('Manifesto de seleção/versionamento obrigatório')
 for i,spec in enumerate(manifest['files']):
  for field in ['path','DIST','ANO','ENTIDADE','PUBLICACAO','sha256','status_fonte']:
   if not spec.get(field):raise ValueError('Escopo/proveniência ausente: '+field)
  path=Path(spec['path']);h=hashfile(path)
  if h!=spec['sha256']:raise ValueError('Hash de entrada divergente')
  approved=spec['status_fonte']=='SELECIONADA_FORMALMENTE'
  source=pq.ParquetFile(path)
  attribute_fields=['TUC','A1','A2','A3','A4','A5','A6']
  cols=[c for c in ['DIST','COD_ID','POT_NOM']+attribute_fields+[f'{a}_{component}' for component in ['FAS','NEU'] for a in attribute_fields] if c in source.schema_arrow.names]
  writer=None;n=0;counts={};dest=out/f'enriquecido-{i:05d}.parquet'
  try:
   for batch in source.iter_batches(batch_size=4096,columns=cols):
    values=[]
    for row in batch.to_pylist():
     key=(str(spec['DIST']),spec['ANO'],spec['ENTIDADE'],spec['PUBLICACAO'],str(row.get('COD_ID')))
     try: db.execute('INSERT INTO seen VALUES (?,?,?,?,?)',key)
     except sqlite3.IntegrityError as exc: raise ValueError('Chave de registro duplicada; não deduplicar silenciosamente') from exc
     e=enrich_record(dictionary,row,entity=spec['ENTIDADE'],dist=spec['DIST'],year=spec['ANO'],publication=spec['PUBLICACAO'])
     sets=[('',e['atributos'])]+[(component+':',v['atributos']) for component,v in e['componentes_patrimoniais'].items()]
     for prefix,attributes in sets:
      for slot,a in attributes.items():
       k=prefix+slot+':'+a['status'];counts[k]=counts.get(k,0)+1
       if not approved:a['status_fonte']='NAO_SELECIONADA';a['elegivel_feature']=False
     values.append({'DIST':str(spec['DIST']),'ANO':spec['ANO'],'ENTIDADE':spec['ENTIDADE'],'PUBLICACAO':spec['PUBLICACAO'],
                    'COD_ID':e['COD_ID'],'TUC':e['TUC'],'A1':e['A1'],'ATRIBUTOS_JSON':json.dumps(e,ensure_ascii=False,sort_keys=True),
                    'POTENCIA_HOMOLOGADA_KVA':None,'ELEGIVEL_MODELO':False})
    schema=pa.schema([('DIST',pa.string()),('ANO',pa.int32()),('ENTIDADE',pa.string()),('PUBLICACAO',pa.string()),('COD_ID',pa.string()),
                      ('TUC',pa.string()),('A1',pa.string()),('ATRIBUTOS_JSON',pa.string()),('POTENCIA_HOMOLOGADA_KVA',pa.float64()),('ELEGIVEL_MODELO',pa.bool_())])
    table=pa.Table.from_pylist(values,schema=schema)
    if writer is None:writer=pq.ParquetWriter(dest,schema,compression='zstd')
    writer.write_table(table);n+=len(values)
  finally:
   if writer:writer.close()
   db.commit()
  assert hashfile(path)==h,'Fonte alterada durante leitura'
  inventory.append({**{k:spec[k] for k in ['DIST','ANO','ENTIDADE','PUBLICACAO','status_fonte']},'linhas_lidas':n,
                    'atributos_presentes':[c for c in cols if c.startswith('A')],'contagem_status':counts,
                    'sha256_entrada':h,'potencia_homologada_recuperada':None})
  if dest.exists():outputs.append({'arquivo':dest.name,'sha256':hashfile(dest)})
 db.close();(out/'_cardinalidade.sqlite').unlink()
 report={'dataset_version':manifest['dataset_version'],'inventario':inventory,'saidas':outputs,'targets_modificados':False,
         'agregacao_eq_un':False,'sintetico':manifest.get('sintetico',False),'potencia_total_recuperada':None,
         'estado':'ENRIQUECIMENTO_DOCUMENTAL_SEM_HOMOLOGACAO'}
 (out/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 return report
