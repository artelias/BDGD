"""Bounded comparative experiments on cached MUNICIPAL aggregates, not raw UCs."""
import argparse,csv,hashlib,json,math,time
from pathlib import Path
from collections import defaultdict
import numpy as np
import duckdb
from .runner import atomic,read,digest,fingerprint,score,ROOT
from .temporal import usable,label,MODES
from .ml import build
from .policy import FeaturePolicy
from .features import FEATURES, snapshots, csv_write
MODELS=('ols','ridge','elastic_net','poisson','random_forest','hist_gradient_boosting')
SCOPES=('individual','shared_pilot','peers_pilot')

def bucket(group,n):return int(hashlib.sha256(group.encode()).hexdigest()[:8],16)%n

def load_panel(input_run,asset='ucbt_quantidade',bridges=None):
 from .assets import ASSETS
 from .bridges import quarantine
 kind=ASSETS[asset]['unit_kind'];bridges=bridges or []
 data,metadata,provenance=snapshots(input_run,asset)
 # Syntactically invalid municipalities remain in audit/total, not the model cohort.
 valid={k:v for k,v in data.items() if k[2] and ((len(k[2])==7 and k[2].isdigit()) if kind=='municipality' else k[2]!='MISSING')}
 rows=[];quality=[]
 for (d,y,mun),s in sorted(valid.items()):
  prior=valid.get((d,y-1,mun))
  if prior is None:continue
  h=metadata[d,y];lag=metadata[d,y-1];held=quarantine(bridges,d,y,kind)
  rows.append(dict(dist=d,year=y,group=mun,feature_year=y-1,feature_available=lag['available'],feature_revision_available=lag['available'],target_available=h['available'],stock=prior['n'],y=float(s['n']),x=[math.log1p(prior['n']),prior['urban'],math.log1p(prior['energy']) if prior['energy'] is not None else None],rupture=h['rupture'] or mun in held,rupture_reason='perimeter_bridge_pending:'+held[mun] if mun in held else None,unit_kind=kind,territorial_conflicts=h['qa'].get('territorial_conflicts',0),key=f'{d}:{y}:{mun}'))
 for d,y in sorted(metadata):
  total=sum(v['n'] for (dd,yy,m),v in data.items() if (dd,yy)==(d,y))
  matched=sum(r['y'] for r in rows if (r['dist'],r['year'])==(d,y))
  quality.append(dict(dist=d,year=y,municipal_total=total,matched_cohort=matched,coverage=matched/total if total else None,available=metadata[d,y]['available'],rupture=metadata[d,y]['rupture'],territorial_conflicts=metadata[d,y]['qa'].get('territorial_conflicts',0),quarantined_units=sorted(u for (dd,yy,u) in valid if (dd,yy)==(d,y) and u in quarantine(bridges,d,y,kind)),limitation='territorial overlap is not proof of physical continuity'))
 return rows,quality,provenance

def scope_pool(rows,dist,origin,mode,scope,heldout):
 candidates=[r for r in rows if usable(r,origin,mode) and r['group'] not in heldout and not r['rupture']]
 if scope=='individual':return [r for r in candidates if r['dist']==dist],[]
 if scope=='shared_pilot':return candidates,sorted({r['dist'] for r in candidates})
 others=sorted({r['dist'] for r in candidates if r['dist']!=dist})
 if scope=='peers_pilot':
  # Similarity uses training stock/urbanization, never outer targets or future GDP.
  # Assets that carry no urbanization at all (network, transformers) are compared on stock only; when urbanization exists
  # for the pool, a company lacking it is excluded rather than imputed.
  has_urban=any(r['x'][1] is not None for r in candidates)
  def vector(d):
   rr=[r for r in candidates if r['dist']==d]
   if not rr:return None
   if not has_urban:return np.array([np.mean([r['x'][0] for r in rr])])
   urban=[r['x'][1] for r in rr if r['x'][1] is not None]
   return np.array([np.mean([r['x'][0] for r in rr]),np.mean(urban)]) if urban else None
  target=vector(dist)
  if target is None:return [],[]
  others=[d for d in others if vector(d) is not None]
  others=sorted(others,key=lambda d:(float(np.linalg.norm(vector(d)-target)),d))[:1]
 return [r for r in candidates if r['dist'] in others],others

def eligible_features(train,val,mode,n_features,policy=None):
 """Feature indices usable under the configured coverage/imputation policy (statistics from the training rows only).
 A feature is dropped for THIS candidate set only; coverage and the reason are recorded by `feature_report`."""
 from .externals import feature_allowed
 from .policy import FeaturePolicy,feature_status
 policy=policy or FeaturePolicy()
 return [i for i in range(n_features) if feature_status(i,train,val,mode,policy,feature_allowed)['eligible']]

def feature_report(train,val,mode,n_features,policy=None):
 from .externals import feature_allowed
 from .policy import FeaturePolicy,feature_status
 policy=policy or FeaturePolicy()
 return {FEATURES[i] if i<len(FEATURES) else str(i):feature_status(i,train,val,mode,policy,feature_allowed) for i in range(n_features)}

def feature_subsets(eligible):
 """Stock-only, stock+each eligible feature independently (energy never requires urbanization), then the full eligible set."""
 order=[i for i in [2,1]+sorted(set(eligible)-{0,1,2}) if i in eligible]
 subsets=[[0]]+[[0,i] for i in order]
 if {1,2}<=set(order):subsets.append([0,1,2])
 if len(order)>2:subsets.append([0]+order)
 out=[]
 for f in subsets:
  if f not in out:out.append(f)
 return out

def options(model,trials,seed,n_features=3,eligible=None):
 rng=np.random.default_rng(seed)
 choices={'ols':[{}],'ridge':[{'alpha':a} for a in [.1,1.,10.,100.]],'elastic_net':[{'alpha':a,'l1_ratio':l} for a in [.01,.1] for l in [.2,.8]],'poisson':[{'alpha':a} for a in [.1,1.,10.]],'random_forest':[{'max_depth':d,'min_samples_leaf':l} for d in [3,6] for l in [3,8]],'hist_gradient_boosting':[{'max_leaf_nodes':d,'learning_rate':.05} for d in [7,15]]}
 subsets=feature_subsets(list(eligible) if eligible is not None else list(range(min(n_features,3))))
 mandatory=[dict(params=choices[model][0],features=f) for f in subsets]
 combos=[dict(params=p,features=f) for p in choices[model] for f in subsets]
 extra=[combos[int(i)] for i in rng.permutation(len(combos)) if combos[int(i)] not in mandatory]
 return (mandatory+extra)[:max(len(subsets),trials)]

def fit_predict(model,opt,train,test,seed):
 from .externals import feature_allowed
 from .policy import FeaturePolicy,feature_status,fit_imputer,design
 fs=opt['features'];policy=FeaturePolicy(**opt.get('policy',{}));mode=opt.get('mode','point_in_time')
 if len({r['group'] for r in train})<5 or not test:raise ValueError('insufficient independent training territories')
 for i in fs:
  st=feature_status(i,train,test,mode,policy,feature_allowed)
  if not st['eligible']:raise ValueError('feature ineligible ('+st['reason']+'): '+(FEATURES[i] if i<len(FEATURES) else str(i)))
 stats=fit_imputer(train,fs,policy)
 x=design(train,fs,stats,policy);xt=design(test,fs,stats,policy);y=np.array([r['y'] for r in train])
 # Log-stock regressions; Poisson retains count response with log link.
 target=y if model=='poisson' else np.log1p(y)
 m=build(model,opt['params'],seed);m.fit(x,target);raw=m.predict(xt)
 pred=raw if model=='poisson' else np.expm1(raw)
 if not np.isfinite(pred).all() or (pred<0).any():raise ValueError('negative or nonfinite forecast rejected')
 estimator=m.named_steps['model'];explain=dict(policy=policy.as_dict(),imputation_statistics={FEATURES[i]:v for i,v in stats.items()})
 for attr in ['coef_','feature_importances_']:
  if hasattr(estimator,attr):explain[attr]=np.asarray(getattr(estimator,attr)).tolist()
 return pred.tolist(),explain

def choose_options(rows,dist,origin,mode,scope,heldout,model,cfg):
 # Inner time origin is strictly earlier than outer origin; outer groups excluded throughout.
 inner=origin-1;val=[r for r in rows if r['dist']==dist and r['year']==origin and r['group'] not in heldout and bucket(r['group'],5)==0 and usable(r,inner,mode,False) and not r['rupture'] and (mode!='point_in_time' or (r.get('target_available') and r['target_available']<=f'{origin}-12-31'))]
 blocked=heldout|{r['group'] for r in val};train,peers=scope_pool(rows,dist,inner,mode,scope,blocked)
 trials=[]
 policy=FeaturePolicy.from_cfg(cfg.get('feature_policy'));elig=eligible_features(train,val,mode,len(rows[0]['x']) if rows else 3,policy)
 for opt in options(model,cfg['max_trials'],cfg['seed'],eligible=elig):
  opt=dict(opt,mode=mode,policy=policy.as_dict())
  try:
   p,_=fit_predict(model,opt,train,val,cfg['seed']);metric=score([r['y'] for r in val],p)['mae'];trials.append(dict(**opt,mae=metric,status='inner_validation',inner_origin=inner))
  except Exception as e:trials.append(dict(**opt,mae=None,status=str(e),inner_origin=inner))
 good=[x for x in trials if x['mae'] is not None]
 selected=min(good,key=lambda x:(x['mae'],len(x['features']))) if good else dict(params=options(model,1,cfg['seed'],eligible=[0])[0]['params'],features=[0])
 selected=dict(selected,mode=mode,policy=policy.as_dict())
 return selected,trials,'inner_holdout_selection' if good else 'fixed_stock_only_default_no_eligible_inner_fold'

def experiment(rows,dist,mode,model,scope,cfg,stop):
 start=time.monotonic();predictions=[];folds=[];failures=[]
 for origin in cfg['origins']:
  targets=[r for r in rows if r['dist']==dist and r['year']==origin+1 and usable(r,origin,mode,False) and not r['rupture']]
  if not targets:failures.append(dict(origin=origin,reason='no eligible targets/features at forecast origin'));continue
  for part in range(cfg['territorial_folds']):
   if stop.exists():raise InterruptedError('stop requested')
   if time.monotonic()-start>cfg['seconds_per_candidate']:failures.append(dict(origin=origin,reason='candidate time budget'));return dict(predictions=predictions,folds=folds,failures=failures)
   test=[r for r in targets if bucket(r['group'],cfg['territorial_folds'])==part]
   if not test:continue
   heldout={r['group'] for r in rows if bucket(r['group'],cfg['territorial_folds'])==part}
   train,peers=scope_pool(rows,dist,origin,mode,scope,heldout)
   try:
    if model=='persistencia':values=[r['stock'] for r in test];opt=dict(params={},features=[0]);trials=[];selection='baseline';explain={}
    else:
     opt,trials,selection=choose_options(rows,dist,origin,mode,scope,heldout,model,cfg)
     values,explain=fit_predict(model,opt,train,test,cfg['seed'])
    folds.append(dict(origin=origin,part=part,scope=scope,peers=peers,train_n=len(train),train_territories=len({r['group'] for r in train}),test_n=len(test),selected_features=[FEATURES[i] for i in opt['features']],rejected_features=[dict(feature=f,reason='not selected by inner validation or unavailable; no claim of no effect') for i,f in enumerate(FEATURES) if i<len(test[0]['x']) and i not in opt['features']],params=opt['params'],selection=selection,trials=trials,explanation=explain))
    predictions.extend(dict(key=r['key'],origin=origin,horizon=1,municipality=r['group'],actual=r['y'],pred=p) for r,p in zip(test,values))
   except Exception as e:failures.append(dict(origin=origin,part=part,reason=str(e)))
 return dict(predictions=predictions,folds=folds,failures=failures)

def summarise(experiments,minimum_origins):
 baseline=experiments['persistencia:individual']['predictions'];keys={r['key'] for r in baseline};out=[]
 for name,e in experiments.items():
  rs=e['predictions'];equivalent=bool(keys) and {r['key'] for r in rs}==keys and len(rs)==len(keys)
  by=defaultdict(list)
  for r in rs:by[r['origin']].append(r)
  fold_metrics=[dict(origin=o,**score([r['actual'] for r in z],[r['pred'] for r in z])) for o,z in sorted(by.items())]
  metrics=score([r['actual'] for r in rs],[r['pred'] for r in rs]) if rs else {}
  robust=float(np.mean([x['mae'] for x in fold_metrics])+np.std([x['mae'] for x in fold_metrics])) if fold_metrics else None
  totals=[dict(origin=o,actual=sum(r['actual'] for r in z),pred=sum(r['pred'] for r in z),municipalities=len(z)) for o,z in sorted(by.items())]
  total_metrics=score([r['actual'] for r in totals],[r['pred'] for r in totals]) if totals else {}
  out.append(dict(distributor_totals=totals,distributor_metrics=total_metrics,candidate=name,common_test_set=equivalent,n_predictions=len(rs),independent_origins=len(by),metrics=metrics,by_origin=fold_metrics,robust_score=robust,folds=e['folds'],failures=e['failures']))
 eligible=[r for r in out if r['common_test_set']]
 best=min(eligible,key=lambda r:(r['robust_score'],r['candidate']!='persistencia:individual')) if eligible else None
 base=next(r for r in out if r['candidate']=='persistencia:individual')
 winner='persistencia:individual';reason='insufficient independent temporal origins; baseline fallback'
 if best and best['independent_origins']>=minimum_origins and base['robust_score'] and best['robust_score']<.95*base['robust_score']:winner=best['candidate'];reason='>=5% robust individual gain on common tests'
 if not keys:reason='no eligible evaluation; baseline policy only, no measured winner'
 return dict(candidates=out,winner=winner,selection_reason=reason,best_exploratory=best['candidate'] if best else None,validated_winner=reason.startswith('>=5%'))

def investigate(input_run,dists):
 from .runner import publication_map
 inventory=publication_map();results=[]
 for item,r in inventory.items():
  if int(r.get('dist') or 0) not in dists:continue
  dates=[r.get(k,'')[:10] for k in ['publicado_em','atualizado_em'] if r.get(k)]
  results.append(dict(item=item,dist=r['dist'],year=r.get('ano','2025'),created=r.get('publicado_em'),revision=r.get('atualizado_em'),available=max(dates) if dates else None,url=r.get('url_item'),source='local inventory; current item metadata does not reconstruct former revisions'))
 return dict(publications=results,claim='No eligible earlier vintage proven in local inventory; this does not prove no such publication ever existed.',sources=[dict(path=p,sha256=digest(p)) for p in ['D:/NUCLEO_BDGD_2022_2024/inventario/inventario_historico_2022_2024.csv','D:/NUCLEO_BDGD_2025/inventario/inventario_2025.csv']])

def run(cfg,stop):
 from threadpoolctl import threadpool_limits
 import importlib.metadata,platform
 if set(cfg['dists'])!={26,6585,6600}:raise ValueError('controlled comparison requires the three-company pilot pool only')
 asset=cfg.get('asset','ucbt_quantidade')
 from .assets import ASSETS
 from . import bridges as bridge_lib,feature_registry
 spec=ASSETS[asset];bridge_list=bridge_lib.load(cfg['bridges_dir']) if cfg.get('bridges_dir') else []
 rows,quality,provenance=load_panel(cfg['comparison_input'],asset,bridge_list);provenance['asset']=asset;provenance['bridges']=[dict(id=b['id'],status=b['status'],sha=b['_sha256']) for b in bridge_list];provenance['code']=fingerprint({str(p):digest(p) for p in Path(__file__).parent.glob('*.py')})
 if cfg.get('external_manifest'):
  from .externals import attach
  rows=attach(rows,cfg['external_manifest']);provenance['external_manifest']=digest(cfg['external_manifest'])
 rows=[r for r in rows if r['dist'] in cfg['dists']];quality=[r for r in quality if r['dist'] in cfg['dists']]
 environment=dict(python=platform.python_version(),packages={name:importlib.metadata.version(name) for name in ['scikit-learn','numpy','scipy','duckdb','threadpoolctl']})
 provenance['environment']=environment
 models=[m for m in cfg['models'] if spec['count'] or m!='poisson']  # Poisson is a count model: not used for km/kVA
 signature=fingerprint([cfg,provenance]);out=Path(cfg['output'])/'comparison'/signature[:16];out.mkdir(parents=True,exist_ok=True)
 atomic(out/'manifest.json',dict(config=cfg,inputs=provenance,signature=signature));atomic(out/'coverage.json',quality);atomic(out/'historical_publications.json',investigate(cfg['comparison_input'],cfg['dists']))
 summaries=[];reused=0;executed=0
 with threadpool_limits(limits=cfg['threads']):
  for mode in MODES:
   for dist in cfg['dists']:
    experiments={}
    for model,scope in [('persistencia','individual')]+[(m,s) for m in models for s in SCOPES]:
     if stop.exists():atomic(out/'progress.json',dict(state='stopped',reused=reused,executed=executed));return out
     name=model+':'+scope;cp=out/'checkpoints'/f'{mode}_{dist}_{model}_{scope}.json'
     try:cached=read(cp) if cp.exists() else {}
     except (ValueError,OSError):cached={}
     if cached.get('signature')==signature and cached.get('sha256')==fingerprint(cached.get('result')):result=cached['result'];reused+=1
     else:
      try:result=experiment(rows,dist,mode,model,scope,cfg,stop)
      except InterruptedError:atomic(out/'progress.json',dict(state='stopped',reused=reused,executed=executed));return out
      except Exception as e:result=dict(predictions=[],folds=[],failures=[dict(reason=str(e))])
      atomic(cp,dict(signature=signature,sha256=fingerprint(result),result=result));executed+=1
     experiments[name]=result
     atomic(out/'progress.json',dict(state='running',mode=mode,dist=dist,candidate=name,reused=reused,executed=executed))
    summary=dict(dist=dist,asset=spec['ativo'],metric=spec['metrica'],unit=spec['unit'],experimental_asset=spec['experimental'],models_used=models,feature_policy=cfg.get('feature_policy') or 'strict',mode=mode,evaluation_label=label(mode),scope_limit='pool das tres distribuidoras (26, 6585, 6600); no national model',**summarise(experiments,cfg['min_independent_origins']))
    summaries.append(summary);atomic(out/f'{mode}_{dist}.json',summary)
 atomic(out/'summaries.json',summaries)
 from .externals import coverage_rows
 csv_write(out/'FEATURE_COVERAGE_BY_ORIGIN.csv',coverage_rows(rows,cfg['origins']))
 feature_registry.write(feature_registry.build(rows,asset),out)
 reconciliation=[]
 for summary in summaries:
  for c in summary['candidates']:
   for t in c['distributor_totals']:
    total=next(q['municipal_total'] for q in quality if q['dist']==summary['dist'] and q['year']==t['origin']+1)
    reconciliation.append(dict(DIST=summary['dist'],mode=summary['mode'],candidate=c['candidate'],year=t['origin']+1,**t,full_observed_stock=total,coverage=t['actual']/total if total else None,residual=t['pred']-t['actual'],rule='bottom_up_sum; no scaling to observed target; partial if uncovered municipalities'))
 csv_write(out/'DISTRIBUTOR_RECONCILIATION.csv',reconciliation)
 flat=[]
 for summary in summaries:
  for r in summary['candidates']:flat.append(dict(DIST=summary['dist'],ativo=spec['ativo'],metrica=spec['metrica'],mode=summary['mode'],candidate=r['candidate'],winner=summary['winner'],validated_winner=summary['validated_winner'],best_exploratory=summary['best_exploratory'],common_test_set=r['common_test_set'],n=r['n_predictions'],origins=r['independent_origins'],**r['metrics'],robust_score=r['robust_score'],features=json.dumps([f['selected_features'] for f in r['folds']]),hyperparameters=json.dumps([f['params'] for f in r['folds']]),blocks=json.dumps(r['failures']),reason=summary['selection_reason']))
 with open(out/'MATRIZ_COMPARATIVA.csv','w',newline='',encoding='utf-8-sig') as f:
  fields=list(dict.fromkeys(k for r in flat for k in r));w=csv.DictWriter(f,fields);w.writeheader();w.writerows(flat)
 atomic(out/'progress.json',dict(state='completed',reused=reused,executed=executed,summaries=len(summaries)))
 return out
