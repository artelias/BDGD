"""Additional extractors; all paths refer to existing Parquets, never GDB/ZIP."""
from pathlib import Path
from .runner import lit,norm,ident

def path(src,entity):
 b=Path(src['base']);return b/f'entidade={entity}/part-0.parquet' if src['year']==2025 else b/f'{entity}.parquet'
def source(con,src,entity,name):
 p=path(src,entity)
 if not p.exists():return None
 con.execute('CREATE OR REPLACE TEMP VIEW '+name+' AS SELECT * FROM read_parquet('+lit(p.as_posix())+')')
 return {r[0] for r in con.execute('DESCRIBE '+name).fetchall()}
def network(con,src):
 cols=source(con,src,'SSDMT','network')
 if not cols or not {'COD_ID','COMP'}<=cols:raise ValueError('SSDMT identity/length missing')
 n,ids,missing,negative,km=con.execute('SELECT count(*),count(distinct COD_ID),count(*) FILTER(WHERE try_cast(COMP as double) IS NULL),count(*) FILTER(WHERE try_cast(COMP as double)<0),sum(try_cast(COMP as double))/1000 FROM network').fetchone()
 return dict(value=km if n==ids and not missing and not negative else None,rows=n,unique_ids=ids,missing=missing,negative=negative,unit='km',source='SSDMT.COMP metres / 1000')
def transformers(con,src,tuc):
 pieces=[]
 for eq,un,fks,factor in [('EQTRMT','UNTRMT',['UNI_TR_MT','UN_TR_MT'],1),('EQTRAT','UNTRAT',['UNI_TR_AT','UN_TR_AT'],1000)]:
  ec=source(con,src,eq,'e0');uc=source(con,src,un,'u0')
  if not ec or not uc:continue
  fk=next((x for x in fks if x in ec),None)
  if not fk or not {'COD_ID','TUC','SITCONT'}<=ec or not {'COD_ID','POT_NOM','SIT_ATIV'}<=uc:continue
  q=f"""WITH e AS (SELECT {norm('COD_ID')} id,{norm(fk)} fk,{norm('TUC')} tuc,{norm('SITCONT')} sit,
  count(*) OVER(PARTITION BY {norm('COD_ID')}) ni,count(*) OVER(PARTITION BY {norm(fk)}) nf FROM e0),
  u AS (SELECT {norm('COD_ID')} fk,try_cast(POT_NOM as double)*{factor} kva,{norm('SIT_ATIV')} active,count(*) OVER(PARTITION BY {norm('COD_ID')}) nu FROM u0)
  SELECT e.sit,u.active,count(*) n,sum(u.kva) kva FROM e JOIN u USING(fk)
  WHERE tuc={lit(str(tuc))} AND ni=1 AND nf=1 AND nu=1 AND isfinite(kva) AND kva>0 AND id IS NOT NULL
  GROUP BY ALL"""
  pieces.extend(dict(entity=eq,unit_entity=un,SITCONT=sit,SIT_ATIV=active,rows=n,kva=kva) for sit,active,n,kva in con.execute(q).fetchall())
 return dict(parts=pieces,method='unique UN linked bijectively to EQ; TUC565/570 may occur in EQTRMT',homologated=False,add_EQ_UN=False)
