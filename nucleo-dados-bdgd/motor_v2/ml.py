"""Fold-local preprocessing and bounded candidates; group split units are municipalities."""
from dataclasses import dataclass
import importlib.util, math, time
import numpy as np

@dataclass(frozen=True)
class Budget:
 trials:int=8
 seconds:int=120
 seed:int=42

REGISTRY={
 'ols':{},'ridge':{'alpha':[0.1,1.,10.,100.]},'elastic_net':{'alpha':[.01,.1,1.],'l1_ratio':[.2,.5,.8]},
 'poisson':{'alpha':[.1,1.,10.]},'negative_binomial':{'alpha':[.5,1.,2.]},
 'random_forest':{'max_depth':[3,6,None],'min_samples_leaf':[5,15]},
 'hist_gradient_boosting':{'max_leaf_nodes':[7,15],'learning_rate':[.03,.1]},
 'shared_ridge':{'alpha':[1.,10.,100.]},'peer_ridge':{'alpha':[1.,10.,100.]},
 'two_stage':{'min_samples_leaf':[5,15]}}

def build(name,params,seed):
 from sklearn.pipeline import Pipeline
 from sklearn.preprocessing import StandardScaler
 from sklearn.linear_model import LinearRegression,Ridge,ElasticNet,PoissonRegressor
 from sklearn.ensemble import RandomForestRegressor,HistGradientBoostingRegressor
 factories={'ols':LinearRegression,'ridge':Ridge,'shared_ridge':Ridge,'peer_ridge':Ridge,'elastic_net':ElasticNet,'poisson':PoissonRegressor,'random_forest':RandomForestRegressor,'hist_gradient_boosting':HistGradientBoostingRegressor}
 if name not in factories:raise ValueError('specialized target eligibility required')
 kwargs=dict(params)
 if name=='random_forest':kwargs.update(random_state=seed,n_jobs=1,n_estimators=64)
 if name=='hist_gradient_boosting':kwargs.update(random_state=seed,max_iter=80)
 if name=='elastic_net':kwargs.update(random_state=seed,max_iter=3000)
 return Pipeline([('scale',StandardScaler()),('model',factories[name](**kwargs))])

def valid_rows(rows,origin):
 return [r for r in rows if r['year']<=origin and r.get('released') and r['released']<=f'{origin}-12-31' and r.get('comparable',False) and all(v is not None and math.isfinite(v) for v in r['x'])]

def split(rows,origin,test_groups):
 train=[r for r in valid_rows(rows,origin) if r['group'] not in test_groups]
 test=[r for r in rows if r['year']==origin+1 and r['group'] in test_groups and r.get('comparable',False)]
 assert not {r['group'] for r in train}&{r['group'] for r in test}
 return train,test

def search(name,rows,origins,test_groups,budget=Budget()):
 """Random trials selected on INNER origins only. Caller reserves an outer fold."""
 rng=np.random.default_rng(budget.seed);start=time.monotonic();trials=[]
 for i in range(budget.trials):
  if time.monotonic()-start>budget.seconds:break
  params={k:values[int(rng.integers(len(values)))] for k,values in REGISTRY[name].items()};loss=[];models=[]
  for origin in origins:
   train,test=split(rows,origin,test_groups)
   if len({r['group'] for r in train})<5 or len({r['group'] for r in test})<2:continue
   X=np.asarray([r['x'] for r in train]);y=np.asarray([r['y'] for r in train]);Xt=np.asarray([r['x'] for r in test])
   if not np.isfinite(X).all() or not np.isfinite(Xt).all():continue
   model=build(name,params,budget.seed);model.fit(X,y);pred=model.predict(Xt)
   if not np.isfinite(pred).all() or (pred<0).any():continue
   # Equal municipal weight, not per-UC pseudo-replication.
   grouped={}
   for r,p in zip(test,pred):grouped.setdefault(r['group'],[]).append(abs(r['y']-p))
   loss.append(float(np.mean([np.mean(v) for v in grouped.values()])))
  trials.append(dict(params=params,loss=float(np.mean(loss)+np.std(loss)) if loss else None,folds=len(loss)))
 eligible=[x for x in trials if x['folds']>=2]
 return dict(winner=min(eligible,key=lambda x:x['loss']) if eligible else None,trials=trials,status='eligible' if eligible else 'insufficient nested temporal/territorial folds')

def exposure(municipal_values,served,shares=None):
 """Never infer an entire UF exposure or count shared municipalities in full."""
 if shares is None:raise ValueError('validated municipal population shares required')
 if set(served)-set(municipal_values) or set(served)-set(shares):raise ValueError('incomplete municipal coverage')
 if any(not 0<=shares[m]<=1 for m in served):raise ValueError('invalid territory share')
 return sum(municipal_values[m]*shares[m] for m in served)
