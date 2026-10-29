import argparse, csv, datetime as dt, hashlib, importlib.util, json, os, platform, subprocess, sys, time, traceback
from pathlib import Path
from collections import defaultdict
import duckdb
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
from motor_universal.registry import registry_from_catalog
from motor_universal.contracts import validate_panel
from motor_universal.parquet_io import write_bundle
from motor_universal.models import CANDIDATES, predict
from .metric_contract import physical_prediction

VERSION='v2-pilot-2-uc-v3'
def digest(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  while b:=f.read(4*1024*1024):h.update(b)
 return h.hexdigest()
def fingerprint(x):return hashlib.sha256(json.dumps(x,sort_keys=True,default=str).encode()).hexdigest()
def atomic(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8');os.replace(t,p)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def csvread(p):return list(csv.DictReader(open(p,encoding='utf-8-sig')))
def lit(x):return "'"+str(x).replace("'","''")+"'"
def ident(x):return '"'+x.replace('"','""')+'"'
def norm(x):return 'nullif(trim(cast('+ident(x)+' as varchar)),\'\')'
def eligible(row,cutoff):return row.get('available') is not None and row['available']<=cutoff and row.get('value') is not None

def scenario_values(base,rates):
 if sorted(rates)!=list(rates):raise ValueError('unordered assumptions')
 values=[[v*(1+r)**h for h,v in enumerate(base,1)] for r in rates]
 if any(not np.isfinite(v) or v<0 for seq in values for v in seq):raise ValueError('invalid scenario')
 if any(not values[0][i]<=values[1][i]<=values[2][i] for i in range(len(base))):raise ValueError('scenario order violated')
 return values

def score(actual,forecast):
 a=np.asarray(actual,dtype=float);p=np.asarray(forecast,dtype=float);e=p-a
 return dict(mae=float(np.mean(abs(e))),rmse=float(np.sqrt(np.mean(e*e))),bias=float(np.mean(e)),wape=float(sum(abs(e))/sum(abs(a))) if sum(abs(a)) else None)

def select(results,min_folds=3):
 baseline=results.get('persistencia',[])
 if len(baseline)<min_folds:return 'persistencia','insufficient independent temporal folds'
 keys={x['key'] for x in baseline};scores={}
 for name,rs in results.items():
  if {x['key'] for x in rs}!=keys:continue
  loss=[abs(x['pred']-x['actual']) for x in rs]
  scores[name]=float(np.mean(loss)+np.std(loss))
 best=min(scores,key=lambda k:(scores[k],k!='persistencia',k))
 if scores[best]>=scores['persistencia']*.95:return 'persistencia','gain below 5%'
 return best,'individual MAE + fold instability; same test keys'

def catalog():
 path=ROOT/'motor_cenarios/entrada/externas_ibge_manifesto.json';meta=read(path)
 out=[dict(id=k,source=v['url'],reference=v['periodo'],released=v['divulgacao'],unit='pessoas' if k.startswith('pop') else 'mil BRL',granularity='municipio',availability='local snapshot; revisions require as-of validation',definition='municipal value; UC weights are exposure proxies, not population shares') for k,v in meta.items()]
 for name,url,unit in [('migracao','https://sidra.ibge.gov.br/','pessoas'),('SAMP','https://dadosabertos.aneel.gov.br/dataset/samp-balanco','MWh'),('DEC_FEC','https://dadosabertos.aneel.gov.br/','hours/interruptions'),('EPE','https://www.epe.gov.br/','source-specific'),('PDD','https://www.gov.br/aneel/','source-specific')]:out.append(dict(id=name,source=url,reference=None,released=None,unit=unit,granularity='pending',availability='not ingested; never imputed'))
 return out

def publication_map():
 hs=csvread('D:/NUCLEO_BDGD_2022_2024/inventario/inventario_historico_2022_2024.csv');rs=csvread('D:/NUCLEO_BDGD_2025/inventario/inventario_2025.csv')
 return {x['item_id']:x for x in hs+rs}
def resolve_sources(dist,concept='consumidores',metric='quantidade'):
 rows=csvread(ROOT/'output-historico/contrato-integracao/serie_fisica_nacional.csv');pubs=publication_map();out=[]
 for year in range(2022,2026):
  hits=[x for x in rows if x['dist']==str(dist) and x['ano']==str(year) and x['conceitoId']==concept and x['metrica']==metric]
  ids={x['publicacao_id'] for x in hits if x['publicacao_id']};
  if len(ids)!=1:out.append(dict(year=year,error='missing or ambiguous contract publication'));continue
  it=next(iter(ids));x=next(x for x in hits if x['publicacao_id']==it);p=pubs.get(it,{})
  # Availability of the specific revision, not the competence year.
  dates=[p.get(k,'')[:10] for k in ['publicado_em','atualizado_em'] if p.get(k)]
  available=max(dates) if dates else None
  base=Path('D:/NUCLEO_BDGD_2025/staging_parquet')/f'DIST={dist}'/'DATA_BASE=2025-12-31' if year==2025 else Path('D:/NUCLEO_BDGD_2022_2024/parquet')/str(year)/str(dist)/it
  out.append(dict(year=year,item=it,base=str(base),available=available,source_sha=x['sha256'],rupture=x['ruptura_desde_ano_anterior']=='true',homologation=x['status_homologacao']))
 return out

def extract_uc(con,src,dest):
 base=Path(src['base']);p=base/'entidade=UCBT/part-0.parquet' if src['year']==2025 else base/'UCBT.parquet'
 if not p.exists():raise ValueError('missing UCBT parquet')
 con.execute('CREATE OR REPLACE TEMP VIEW raw AS SELECT * FROM read_parquet('+lit(p.as_posix())+')');cols={r[0] for r in con.execute('DESCRIBE raw').fetchall()}
 required={'COD_ID','SIT_ATIV'}
 if not required<=cols:raise ValueError('missing identity or activation fields')
 dims=['MUN','CONJ','CTMT','ARE_LOC'];missing=[c for c in dims if c not in cols]
 energy=[f'ENE_{i:02}' for i in range(1,13) if f'ENE_{i:02}' in cols]
 energy_expr=' + '.join(f'try_cast({c} as double)' for c in energy) if len(energy)==12 else 'NULL::DOUBLE'
 sel=','.join((norm(c) if c in cols else 'NULL::VARCHAR')+' '+c for c in dims)
 pn="coalesce("+norm('PN_CON')+",'')" if 'PN_CON' in cols else "''"
 con.execute('CREATE OR REPLACE TEMP TABLE rawkeys AS SELECT '+norm('COD_ID')+' id,'+pn+' pn,'+norm('SIT_ATIV')+' sit,'+sel+','+energy_expr+' energy FROM raw')
 n,dup,null,active=con.execute("SELECT count(*),count(*)-count(distinct (id,pn)),count(*) FILTER(WHERE id IS NULL),count(distinct (id,pn)) FILTER(WHERE sit='AT' AND id IS NOT NULL) FROM rawkeys").fetchone()
 conflicts=con.execute("SELECT count(*) FROM (SELECT id,pn FROM rawkeys WHERE sit='AT' GROUP BY id,pn HAVING count(distinct (MUN,CONJ,CTMT,ARE_LOC))>1)").fetchone()[0]
 # Reuse UC-v3 activation/energy precedence, deterministic territorial tie-break.
 con.execute("CREATE OR REPLACE TEMP TABLE ids AS SELECT *,1 mult FROM rawkeys WHERE id IS NOT NULL QUALIFY row_number() OVER(PARTITION BY id,pn ORDER BY (sit='AT') DESC,energy DESC NULLS LAST,ARE_LOC,MUN,CTMT,CONJ)=1")
 query="SELECT MUN,CONJ,CTMT,ARE_LOC,count(*) clientes_ativos,count(energy) energia_denominador,sum(energy) energia_kwh FROM ids WHERE sit='AT' GROUP BY ALL"
 con.execute('COPY ('+query+') TO '+lit((dest/'territorial.parquet').as_posix())+" (FORMAT PARQUET,COMPRESSION ZSTD)")
 valid=con.execute("SELECT count(*) FROM ids WHERE sit='AT'").fetchone()[0]
 municipalities=con.execute("SELECT MUN,count(*) n FROM ids WHERE sit='AT' AND mult=1 AND id IS NOT NULL GROUP BY MUN").fetchall()
 invalid=sum(n for m,n in municipalities if m is None or len(m)!=7 or not m.isdigit())
 ufs=sorted({m[:2] for m,n in municipalities if m and len(m)==7 and m.isdigit()})
 urban=con.execute("SELECT count(*) FILTER(WHERE ARE_LOC='UB'),count(*) FILTER(WHERE ARE_LOC IN ('UB','NU')) FROM ids WHERE sit='AT' AND mult=1 AND id IS NOT NULL").fetchone()
 return dict(value=valid if n and active else None,source_rows=n,active_rows=active,duplicate_rows_collapsed=dup,territorial_conflicts=conflicts,identity_rule="COD_ID+PN_CON UC-v3",null_ids=null,coverage=valid/active if active else None,missing_fields=missing,energy_columns=len(energy),invalid_municipality_rows=invalid,municipality_ufs=ufs,urban_numerator=urban[0],urban_denominator=urban[1],density=None,density_reason='no validated served area denominator',flows=None,flows_reason='identifier continuity not certified; no physical expansion label',source=str(p),parquet_sha256=digest(p))

def run_task(cfg,dist,runroot,stop):
 task=runroot/str(dist)/'ucbt_quantidade';task.mkdir(parents=True,exist_ok=True);hist=[];audits=[];sources=read(cfg['sources_manifest'])[str(dist)] if cfg.get('sources_manifest') else resolve_sources(dist)
 con=duckdb.connect();con.execute('SET memory_limit='+lit(cfg['memory']));con.execute('SET threads='+str(cfg['threads']));con.execute('SET temp_directory='+lit(str(runroot/'tmp')));con.execute('SET preserve_insertion_order=false')
 try:
  for src in sources:
   if stop.exists():return None
   year=src['year'];dest=task/str(year);dest.mkdir(exist_ok=True);checkpoint=dest/'checkpoint.json'
   try:
    if 'error' in src:raise ValueError(src['error'])
    p=Path(src['base'])/('entidade=UCBT/part-0.parquet' if year==2025 else 'UCBT.parquet')
    # Input fingerprint invalidates a checkpoint even if code/config is unchanged.
    input_hash=digest(p);signature=fingerprint([src,input_hash,cfg,VERSION])
    old=read(checkpoint) if checkpoint.exists() else {}
    if old.get('signature')==signature and (dest/'territorial.parquet').exists() and digest(dest/'territorial.parquet')==old.get('output_sha256'):qa=old['qa']
    else:
     qa=extract_uc(con,src,dest);atomic(checkpoint,dict(signature=signature,qa=qa,output_sha256=digest(dest/'territorial.parquet')))
    row=dict(year=year,available=src['available'],value=qa['value'],rupture=src['rupture'],qa=qa,source=src)
    hist.append(row);audits.append(dict(year=year,**qa))
   except Exception as e:audits.append(dict(year=year,error=str(e)));atomic(dest/'failure.json',dict(error=str(e),traceback=traceback.format_exc()))
  results=defaultdict(list);registry=[]
  for name,candidate in CANDIDATES.items():
   why='eligible'
   if candidate.sklearn_class and not importlib.util.find_spec('sklearn'):why='dependency unavailable'
   if candidate.min_train>len(hist):why='insufficient independent annual observations'
   registry.append(dict(id=name,scope='individual',status=why,params=dict(candidate.params)))
   if why!='eligible':continue
   for origin in [2023,2024]:
    train=[x for x in hist if x['year']<=origin and eligible(x,f'{origin}-12-31') and not x['rupture']]
    for h in [1,2]:
     target=next((x for x in hist if x['year']==origin+h and x['value'] is not None),None)
     if not target or len(train)<candidate.min_train:continue
     try:
      pred,diag=predict(candidate,[dict(ano=x['year'],valor_alvo=x['value'],disponivel_em=x['available']) for x in train],[origin+h],cutoff=f'{origin}-12-31')
      results[name].append(dict(key=f'{origin}:{h}',origin=origin,horizon=h,actual=target['value'],pred=pred[0]))
     except Exception as e:registry.append(dict(id=name,origin=origin,status=str(e)))
  winner,reason=select(results,cfg['min_folds']);cutoff=cfg['as_of'];usable=[x for x in hist if eligible(x,cutoff)]
  # A structural rupture truncates the usable segment; no imputation or skipping gaps.
  tail=[]
  for x in sorted(usable,key=lambda x:x['year'],reverse=True):
   if tail and x['year']!=tail[-1]['year']-1:break
   tail.append(x)
   if x['rupture']:break
  tail=sorted(tail,key=lambda x:x['year']);forecast=[];diagnostics={}
  if tail and tail[-1]['year']==2025:
   if winner=='persistencia':base=[tail[-1]['value']]*5;diagnostics={'reason':reason}
   else:base,diagnostics=predict(CANDIDATES[winner],[dict(ano=x['year'],valor_alvo=x['value'],disponivel_em=x['available']) for x in tail],list(range(2026,2031)),cutoff=cutoff)
   # Neutral scenarios coincide unless explicit, approved sensitivities are supplied.
   values=scenario_values(base,cfg['scenario_rates'])
   for label,rate,values_ in zip(['Conservador','Moderado','Agressivo'],cfg['scenario_rates'],values):
    for year,v in zip(range(2026,2031),values_):forecast.append(dict(DIST=dist,ativo='ucbt',metrica='quantidade',ano=year,cenario=label,valor=physical_prediction(v,'discrete_count'),raw_prediction=v,rounding='half_up',unidade='clientes',model=winner,assumption_rate=rate,status='exploratorio_condicional',confidence_interval=None))
  metrics={name:score([x['actual'] for x in rs],[x['pred'] for x in rs]) for name,rs in results.items()}
  report=dict(synthetic=cfg.get('synthetic',False),dist=dist,asset='ucbt',metric='quantidade',winner=winner,reason=reason,candidates=registry,backtest=dict(results),metrics=metrics,history=hist,quality=audits,forecast=forecast,feature_decisions=[dict(feature='estoque_passado',selected=True,reason='baseline'),dict(feature='externas',selected=False,reason='territorial exposure and as-of revision not validated'),dict(feature='entradas_saidas',selected=False,reason='identity continuity not certified')],hyperparameters=dict(CANDIDATES[winner].params),explanation=diagnostics,territorial_validation='aggregated municipalities; held-out territorial ML not yet eligible',retrospective_status='available' if results else 'blocked_by_release_dates_or_sample',training_status='baseline_fallback' if winner=='persistencia' else 'selected')
  # Only aggregated targets are exported; UCBT is a scoped extension, not all consumers.
  import pyarrow as pa, pyarrow.parquet as pq
  pq.write_table(pa.Table.from_pylist([dict(DIST=dist,ANO=x['year'],OBJETIVO_ID='ucbt',METRICA='quantidade',VALOR_ALVO=x['value'],DISPONIVEL_EM=x['available'],FONTE=x['qa']['source'],COBERTURA=x['qa']['coverage']) for x in hist]),task/'targets.parquet')
  atomic(task/'result.json',report);return report
 finally:con.close()

def execute(cfg):
 out=Path(cfg['output']).resolve()
 if out.drive.upper()!='D:':raise ValueError('output must be on D:')
 out.mkdir(parents=True,exist_ok=True);lock=out/'executor.lock'
 import psutil
 child_guard=out/'worker.json'
 if child_guard.exists():
  child=read(child_guard)
  if psutil.pid_exists(child['pid']) and abs(psutil.Process(child['pid']).create_time()-child['created'])<1:raise RuntimeError('previous worker still active; do not duplicate task')
 try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
 except FileExistsError:
  old=read(lock)
  if psutil.pid_exists(old['pid']) and abs(psutil.Process(old['pid']).create_time()-old['created'])<1:raise RuntimeError('executor already running')
  lock.unlink();fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
 owner=dict(pid=os.getpid(),created=psutil.Process().create_time(),launch_id=os.environ.get('MOTOR_V2_LAUNCH_ID'));os.write(fd,json.dumps(owner).encode());os.close(fd)
 stop=out/'STOP';status=out/'status.json';code={str(p.relative_to(ROOT)):digest(p) for p in list((ROOT/'motor_v2').glob('*.py'))+list((ROOT/'motor_universal').glob('*.py'))};runid=fingerprint([cfg,code])[:16];runroot=out/'runs'/runid;runroot.mkdir(parents=True,exist_ok=True)
 try:
  if cfg.get('experiment')=='comparison':
   from .comparison import run
   atomic(status,dict(**owner,state='running',experiment='comparison',runid=runid))
   destination=run(cfg,stop)
   atomic(status,dict(**owner,state=read(destination/'progress.json')['state'],experiment='comparison',output=str(destination),runid=runid))
   return
  atomic(runroot/'manifest.json',dict(version=VERSION,config=cfg,code=code,python=sys.version,platform=platform.platform(),runid=runid))
  atomic(runroot/'externas_catalogo.json',catalog());atomic(runroot/'registry.json',registry_from_catalog(read(ROOT/'etl/bdgd2025/config/conceitos_2025.json')))
  outputs=[]
  for i,dist in enumerate(cfg['dists']):
   if stop.exists():break
   atomic(status,dict(**owner,state='running',runid=runid,current_dist=dist,completed=i,total=len(cfg['dists'])))
   try:
    command=[sys.executable,'-u','-m','motor_v2.runner','--config',str(runroot/'effective_config.json'),'--dist',str(dist),'--runroot',str(runroot)]
    atomic(runroot/'effective_config.json',cfg)
    with open(runroot/f'task_{dist}.log','a',encoding='utf-8') as log:
     worker=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
     atomic(child_guard,dict(pid=worker.pid,created=psutil.Process(worker.pid).create_time()))
     try:worker.wait(timeout=cfg['task_timeout_seconds'])
     except subprocess.TimeoutExpired:
      worker.terminate();worker.wait();raise TimeoutError('task budget exceeded; annual checkpoints retained')
     child_guard.unlink(missing_ok=True)
     if worker.returncode:raise RuntimeError('worker failed; inspect task log')
    result_path=runroot/str(dist)/'ucbt_quantidade/result.json'
    if result_path.exists():outputs.append(read(result_path))
   except Exception as e:atomic(runroot/f'failure_{dist}.json',dict(error=str(e),traceback=traceback.format_exc()))
  from .integration import export
  if outputs:atomic(runroot/'registry_integration.json',export(outputs,read(ROOT/'etl/bdgd2025/config/conceitos_2025.json'),runroot/('bundle-'+fingerprint(outputs)[:12]),runid+'-'+fingerprint(outputs)[:12]))
  allf=[r for o in outputs for r in o['forecast']]
  # Public forecast: integers only (physical_prediction in `valor`); the raw continuous value stays in the internal diagnostic file.
  atomic(runroot/'forecast.json',[{k:v for k,v in r.items() if k!='raw_prediction'} for r in allf]);atomic(runroot/'forecast_internal.json',allf)
  import pyarrow as pa,pyarrow.parquet as pq
  flat=[{k:v for k,v in r.items() if k!='raw_prediction'} for r in allf]
  if flat:pq.write_table(pa.Table.from_pylist(flat),runroot/'forecast.parquet')
  atomic(status,dict(**owner,state='stopped' if stop.exists() else 'completed' if len(outputs)==len(cfg['dists']) else 'completed_with_errors',runid=runid,completed=len(outputs),total=len(cfg['dists']),output=str(runroot)))
 except Exception as error:
  atomic(status,dict(**owner,state='failed',runid=runid,error=str(error),output=str(runroot)))
  raise
 finally:lock.unlink(missing_ok=True)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);ap.add_argument('--dist',type=int);ap.add_argument('--runroot');a=ap.parse_args();cfg=read(a.config)
 if a.dist:run_task(cfg,a.dist,Path(a.runroot),Path(cfg['output'])/'STOP')
 else:execute(cfg)
if __name__=='__main__':main()
