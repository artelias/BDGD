"""Todos os painéis deste arquivo são SINTÉTICOS; não representam dados externos reais."""
from copy import deepcopy
from pathlib import Path
import tempfile,unittest
from motor_universal.tests.test_motor import fixture
from motor_universal.knn import anchored_knn,backtest_knn
from motor_universal.parquet_io import write_bundle,read_bundle

def panel():
 p,r=fixture(8);base=p['rows'];p['rows']=[]
 p['feature_definitions']={'porte_externo':{'origem':'externa','tipo':'numerica','unidade':'pessoas','comparabilidade_validada':True,'evidencia_comparabilidade':'SINTETICO'}}
 for d in range(26,34):
  for b in base:
   x=deepcopy(b);y=b['ano'];x.update(DIST=str(d),territorio={'nivel':'dist','id':str(d)},valor_alvo=100+10*(d-26)+(y-2010)*(d-20))
   x['features']={'porte_externo':{'valor':1000+50*d+10*(y-2010),'unidade':'pessoas','fonte':'SINTETICO','versao':'SINTETICO-1','referencia':f'{y-1}-12-31','disponivel_em':f'{y-1}-12-31'}}
   p['rows'].append(x)
 return p,r

def forecast(p,r,k=3):return anchored_knn(p,r,dist='26',objective='consumidores',metric='quantidade',anchor_year=2016,target_year=2017,cutoff='2016-12-31',k=k)

class KnnTests(unittest.TestCase):
 def test_anchor_and_unique_other_distributors_with_traceable_interval(self):
  p,r=panel();v=forecast(p,r)
  self.assertEqual(v['ancora'],136);self.assertEqual(len(v['vizinhos']),3)
  self.assertEqual(len({n['DIST'] for n in v['vizinhos']}),3);self.assertNotIn('26',{n['DIST'] for n in v['vizinhos']})
  self.assertTrue(all(n['ano_resposta']<=2016 for n in v['vizinhos']));self.assertFalse(v['previsao_validada']);self.assertTrue(v['sintetico'])
  self.assertLessEqual(v['intervalo_indicativo'][0],v['estimativa']);self.assertGreaterEqual(v['intervalo_indicativo'][1],v['estimativa']);self.assertIsNone(v['necessidade_expansao'])
 def test_verified_zero_response_is_valid_but_not_technical_zero(self):
  p,r=panel()
  for row in p['rows']:
   if row['DIST']!='26' and row['ano']==2016:row.update(valor_alvo=0,status_qualidade='zero_verificado',evidencia_zero='SINTETICO-prova-independente')
  self.assertEqual(forecast(p,r)['estimativa'],0)
  for row in p['rows']:
   if row['DIST']!='26' and row['ano']==2016:row['status_qualidade']='zero_tecnico'
  self.assertGreater(forecast(p,r)['estimativa'],0)
 def test_latest_reliable_anchor_is_required(self):
  p,r=panel()
  with self.assertRaisesRegex(ValueError,'ULTIMA_CONFIAVEL'):
   anchored_knn(p,r,dist='26',objective='consumidores',metric='quantidade',anchor_year=2015,target_year=2017,cutoff='2016-12-31',k=3)
 def test_municipal_rows_cannot_multiply_neighbor_population(self):
  p,r=panel()
  next(x for x in r['objetivos'] if x['objetivo_id']=='consumidores')['territorios']=['dist','municipio']
  next(x for x in p['rows'] if x['DIST']=='27')['territorio']={'nivel':'municipio','id':'1100015'}
  with self.assertRaisesRegex(ValueError,'SEM_RATEIO_MUNICIPAL'):forecast(p,r)
 def test_future_targets_and_features_do_not_change_prediction_or_scaling(self):
  p,r=panel();before=forecast(p,r)
  for x in p['rows']:
   if x['ano']==2017:x['valor_alvo']=99999999;x['features']['porte_externo']['valor']=1e20
  self.assertEqual(forecast(p,r),before)
 def test_query_does_not_fit_scaler(self):
  p,r=panel();a=forecast(p,r)
  next(x for x in p['rows'] if x['DIST']=='26' and x['ano']==2016)['features']['porte_externo']['valor']=1e12
  b=forecast(p,r);self.assertEqual(a['media_treino'],b['media_treino']);self.assertEqual(a['escala_treino'],b['escala_treino'])
 def test_no_external_panel_is_concrete_block_not_fake_result(self):
  p,r=fixture(4);v=backtest_knn(p,r,objective='consumidores',metric='quantidade')
  self.assertEqual(v['status'],'bloqueado');self.assertIsNone(v['estimativa']);self.assertEqual(v['metricas_knn']['n'],0)
 def test_missing_feature_and_late_release_not_imputed(self):
  for mutation in [{'valor':None},{'disponivel_em':'2018-01-01'},{'referencia':'2017-12-31'}]:
   p,r=panel();next(x for x in p['rows'] if x['DIST']=='26' and x['ano']==2016)['features']['porte_externo'].update(mutation)
   with self.subTest(mutation=mutation),self.assertRaises(ValueError):forecast(p,r)
 def test_missing_provenance_or_comparability_is_blocked(self):
  for field,value in [('fonte',''),('versao',''),('status_comparabilidade','PENDENTE'),('ruptura',True)]:
   p,r=panel();next(x for x in p['rows'] if x['DIST']=='26' and x['ano']==2016)['features']['porte_externo'][field]=value
   with self.subTest(field=field),self.assertRaises(ValueError):forecast(p,r)
 def test_missing_zero_or_unapproved_anchor_not_used(self):
  for status,value,homo in [('ausente',None,'NAO_DISPONIVEL'),('zero_tecnico',0,'SINTETICO_NAO_HOMOLOGADO'),('observado',136,'PENDENTE_DECISAO')]:
   p,r=panel();next(x for x in p['rows'] if x['DIST']=='26' and x['ano']==2016).update(status_qualidade=status,valor_alvo=value,status_homologacao=homo)
   with self.subTest(status=status),self.assertRaisesRegex(ValueError,'ANCORA'):forecast(p,r)
 def test_unknown_anchor_availability_not_backdated(self):
  p,r=panel();next(x for x in p['rows'] if x['DIST']=='26' and x['ano']==2016)['disponivel_em']=None
  with self.assertRaisesRegex(ValueError,'ANCORA'):forecast(p,r)
 def test_break_excludes_old_regime_of_neighbor(self):
  p,r=panel();next(x for x in p['rows'] if x['DIST']=='27' and x['ano']==2016)['ruptura']=True
  self.assertNotIn('27',{n['DIST'] for n in forecast(p,r,k=6)['vizinhos']})
 def test_incompatible_units_and_duplicate_keys_rejected(self):
  for mutate in [lambda p:p['rows'][0].update(unidade='kVA'),lambda p:p['rows'].append(deepcopy(p['rows'][0]))]:
   p,r=panel();mutate(p)
   with self.assertRaises(ValueError):forecast(p,r)
 def test_more_neighbors_than_distributors_rejected(self):
  p,r=panel()
  with self.assertRaisesRegex(ValueError,'INSUFICIENTES'):forecast(p,r,k=8)
 def test_k_selection_uses_no_outer_holdout_and_metrics_have_same_n(self):
  p,r=panel();a=backtest_knn(p,r,objective='consumidores',metric='quantidade')
  self.assertLess(max(a['origens_selecao']),a['origem_auditoria'])
  for x in p['rows']:
   if x['ano']==2017:x['valor_alvo']*=1000
  b=backtest_knn(p,r,objective='consumidores',metric='quantidade');self.assertEqual(a['k'],b['k']);self.assertEqual(a['selecao'],b['selecao'])
  self.assertTrue(a['metricas_knn']['n']>0)
  for v in a['baselines'].values():self.assertEqual(v['n'],a['metricas_knn']['n']);self.assertTrue(all(v[m] is not None for m in ['mae','rmse','wape','vies']))
 def test_future_feature_only_rows_do_not_choose_audit_year_or_train(self):
  p,r=panel();a=backtest_knn(p,r,objective='consumidores',metric='quantidade')
  for x in list(p['rows']):
   if x['ano']==2017:
    future=deepcopy(x);future.update(ano=2026,competencia='2026-12-31',valor_alvo=None,status_qualidade='ausente',disponivel_em=None,status_homologacao='NAO_DISPONIVEL');p['rows'].append(future)
  self.assertEqual(a,backtest_knn(p,r,objective='consumidores',metric='quantidade'))
 def test_internal_features_are_used_and_empty_audit_is_blocked(self):
  p,r=panel();p['feature_definitions']['area']={**p['feature_definitions']['porte_externo'],'origem':'interna','unidade':'km2'}
  for row in p['rows']:row['features']['area']={**row['features']['porte_externo'],'valor':int(row['DIST'])*3,'unidade':'km2'}
  self.assertIn('area',forecast(p,r)['variaveis'])
  for row in p['rows']:
   if row['ano']==2016:row['disponivel_em']='2018-01-01'
  out=backtest_knn(p,r,objective='consumidores',metric='quantidade');self.assertEqual(out['status'],'bloqueado');self.assertIsNone(out['estimativa'])
 def test_power_target_requires_comparability_evidence_per_row(self):
  p,r=panel()
  for row in p['rows']:row.update(objetivo_id='trafo_dist',metrica='potencia_kva',unidade='kVA')
  call=lambda:anchored_knn(p,r,dist='26',objective='trafo_dist',metric='potencia_kva',anchor_year=2016,target_year=2017,cutoff='2016-12-31',k=3)
  with self.assertRaisesRegex(ValueError,'METRICA_SEM_COMPARABILIDADE'):call()
  for row in p['rows']:row.update(comparabilidade_validada=True,evidencia_comparabilidade='SINTETICO-unidades-comparaveis')
  self.assertGreater(call()['estimativa'],0)
 def test_enriched_parquet_contract_roundtrip(self):
  p,r=panel()
  with tempfile.TemporaryDirectory() as root:
   out=Path(root)/'panel';write_bundle(p,r,out);restored=read_bundle(out,r)
   self.assertEqual(forecast(p,r)['estimativa'],forecast(restored,r)['estimativa']);self.assertEqual(len(restored['rows']),len(p['rows']))
