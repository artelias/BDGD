"""Painéis e geografia SINTÉTICOS: nenhum dado externo é inventado para produção."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from motor_universal.tests.test_motor import fixture, CATALOG, ROOT
from motor_universal.contracts import validate_panel
from motor_universal.registry import registry_from_catalog
from motor_universal.adapters import national_panel
from motor_universal.engine import run
from motor_universal.features import feature_row, FeaturePipeline
from motor_universal.models import predict, CANDIDATES
from motor_universal.parquet_io import write_bundle, read_bundle, arrow, sha, _feature_schema
from motor_universal.coverage import coverage, overlap_audit
from motor_universal.territorial import validate_municipal_mapping


def enriched(n=12):
    p, r = fixture(n)
    p['feature_definitions'] = {'populacao': {'tipo': 'numerica', 'unidade': 'pessoas',
        'comparabilidade_validada': True, 'evidencia_comparabilidade': 'SINTETICO-TESTE', 'permite_imputacao': True}}
    for row in p['rows']:
        y = row['ano']
        row['features'] = {'populacao': {'valor': 1000 + y, 'unidade': 'pessoas', 'fonte': 'SINTETICO-TESTE',
            'referencia': f'{y-1}-12-31', 'disponivel_em': f'{y-1}-12-31', 'status_comparabilidade': 'VALIDADA',
            'evidencia_comparabilidade': 'SINTETICO-TESTE', 'ruptura': False, 'versao': 'SINTETICO-v1'}}
    for y in range(2010+n, 2010+n+3):
        row = deepcopy(p['rows'][-1]); row.update(ano=y, competencia=f'{y}-12-31', valor_alvo=None,
            status_qualidade='ausente', disponivel_em=None, homologado=False, status_homologacao='NAO_DISPONIVEL')
        row['features']['populacao'].update(referencia=f'{y}-12-31', disponivel_em=f'{2009+n}-12-31', cenario_id='SINTETICO-CONDICIONAL')
        p['rows'].append(row)
    return p, r


def alter_table(bundle, name, mutate):
    pa, pq = arrow(); path = bundle/name
    table = pq.read_table(path); table = mutate(pa, table)
    pq.write_table(table, path)
    mf = bundle/'manifest.json'; m = json.loads(mf.read_text()); m['sha256'][name] = sha(path); mf.write_text(json.dumps(m))


class EnrichedIntegrationTests(unittest.TestCase):
    def test_complete_features_parquet_engine_and_stock_semantics(self):
        p, r = enriched()
        with tempfile.TemporaryDirectory() as td:
            b = Path(td)/'bundle'; manifest = write_bundle(p, r, b); restored = read_bundle(b, r)
            self.assertEqual(manifest['schema_version'], 'bdgd-parquet-2')
            self.assertEqual(len(restored['rows']), len(p['rows']))
            result = run(restored, r, base_year=2021, final_year=2024, as_of='2021-12-31', candidates=['persistencia', 'ridge'])
            s = result['series'][0]; ridge = s['candidatos'][1]
            self.assertEqual(len(ridge['futuro']), 3)
            self.assertTrue(ridge['diagnosticos']['transformacoes_ajustadas_no_treino'])
            self.assertIsNone(s['necessidade_expansao']['valor']); self.assertFalse(result['previsao_validada'])

    def test_partial_missing_features_only_train_imputation(self):
        p, r = enriched(); p['rows'][3]['features']['populacao']['valor'] = None
        p['rows'][5]['features'] = {}  # ausência integral também respeita permite_imputacao
        with tempfile.TemporaryDirectory() as td:
            b = Path(td)/'bundle'; write_bundle(p, r, b); restored = read_bundle(b, r)
            self.assertIsNone(restored['rows'][3]['features']['populacao']['valor'])
            history = restored['rows'][:12]; future = {x['ano']: x for x in restored['rows'][12:]}
            out, _ = predict(CANDIDATES['ridge'], history, [2022], p['feature_definitions'], future, '2021-12-31')
            self.assertEqual(len(out), 1)
        p['feature_definitions']['populacao']['permite_imputacao'] = False
        with self.assertRaisesRegex(ValueError, 'FEATURE_AUSENTE'):
            predict(CANDIDATES['ridge'], p['rows'][:12], [2022], p['feature_definitions'], {}, '2021-12-31')

    def test_future_covariate_missing_never_filled_with_training_mean(self):
        p, _ = enriched()
        for feature in [None, {'valor': None}]:
            with self.subTest(feature=feature):
                future = {x['ano']: deepcopy(x) for x in p['rows'][12:]}
                if feature is None: future[2022]['features'] = {}
                else: future[2022]['features']['populacao'].update(feature)
                with self.assertRaisesRegex(ValueError, 'FEATURE_AUSENTE'):
                    predict(CANDIDATES['ridge'], p['rows'][:12], [2022], p['feature_definitions'], future, '2021-12-31')

    def test_late_feature_cannot_be_imputed_or_read(self):
        p, r = enriched(); p['rows'][9]['features']['populacao']['disponivel_em'] = '2025-01-01'
        s = run(p, r, base_year=2021, final_year=2024, as_of='2021-12-31', candidates=['persistencia', 'ridge'])['series'][0]
        ridge = s['candidatos'][1]
        self.assertIn('FEATURE_INDISPONIVEL_NO_CORTE', ridge['falha_projecao'])
        self.assertTrue(any('FEATURE_INDISPONIVEL_NO_CORTE' in f['motivo'] for f in ridge['falhas']))
        self.assertEqual(s['modelo_selecionado'], 'persistencia')

    def test_known_late_target_not_used_in_any_model_fold(self):
        p, r = fixture(8); p['rows'][0]['disponivel_em'] = '2016-06-01'
        s = run(p, r, base_year=2017, final_year=2022, as_of='2017-12-31', candidates=['persistencia', 'tendencia_ols'])['series'][0]
        for model in s['candidatos']:
            self.assertTrue(all(f['origem'] >= 2016 for f in model['folds']))
            self.assertTrue(any(f['motivo'] == 'ALVO_TREINO_INDISPONIVEL_NA_ORIGEM' for f in model['falhas']))

    def test_direct_baseline_cutoff_and_invalid_horizons(self):
        p,_=fixture(4)
        with self.assertRaisesRegex(ValueError, 'INDISPONIVEL_NA_ORIGEM'):
            predict(CANDIDATES['persistencia'],p['rows'],[2014],cutoff='2012-12-31')
        for years in [[],[2013],[2015,2014],[2014,2014]]:
            with self.subTest(years=years):
                with self.assertRaisesRegex(ValueError,'HORIZONTES'):
                    predict(CANDIDATES['persistencia'],p['rows'],years)

    def test_unknown_target_availability_is_retrospective_not_pit(self):
        p, r = fixture(8)
        for row in p['rows']: row['disponivel_em'] = None
        s = run(p, r, base_year=2017, final_year=2022, candidates=['persistencia'])['series'][0]
        self.assertTrue(s['candidatos'][0]['folds'])
        self.assertTrue(all(not f['point_in_time'] for f in s['candidatos'][0]['folds']))
        self.assertEqual(s['validacao'], 'retrospectiva_limitada')

    def test_all_missing_training_feature_is_not_invented(self):
        p, _ = enriched()
        for row in p['rows']: row['features']['populacao']['valor'] = None
        with self.assertRaisesRegex(ValueError, 'sem dados de treinamento'):
            predict(CANDIDATES['ridge'], p['rows'][:12], [2022], p['feature_definitions'], {}, '2021-12-31')

    def test_imputer_fit_never_reads_future_extreme_or_categories(self):
        encoder = FeaturePipeline().fit([{'x': 10, 'tipo': 'A'}, {'x': None, 'tipo': 'B'}, {'x': 20, 'tipo': 'A'}])
        state = deepcopy((encoder.numeric, encoder.categories)); encoder.transform([{'x': 1e20, 'tipo': 'FUTURO'}])
        self.assertEqual((encoder.numeric, encoder.categories), state)
        self.assertEqual(encoder.transform([{'x': None, 'tipo': 'FUTURO'}])[0][0:2], [0.0, 0.0])

    def test_units_provenance_and_boolean_controls_rejected(self):
        for change in ({'unidade': 'MW'}, {'fonte': ''}, {'fonte': '  '}, {'ruptura': 'false'}, {'versao': ''}):
            with self.subTest(change=change):
                p, r = enriched(); p['rows'][2]['features']['populacao'].update(change)
                with self.assertRaises(ValueError): validate_panel(p, r)

    def test_feature_pending_comparability_and_break_block_candidate(self):
        for change, code in [({'status_comparabilidade': 'PENDENTE'}, 'COMPARABILIDADE'), ({'ruptura': True}, 'RUPTURA'), ({'evidencia_comparabilidade': ''}, 'COMPARABILIDADE')]:
            with self.subTest(change=change):
                p, _ = enriched(); p['rows'][3]['features']['populacao'].update(change)
                with self.assertRaisesRegex(ValueError, code):
                    predict(CANDIDATES['ridge'], p['rows'][:12], [2022], p['feature_definitions'], {}, '2021-12-31')

    def test_unapproved_series_and_target_break_remain_blocked(self):
        p, r = fixture(4)
        for row in p['rows']:
            row.update(status_qualidade='nao_homologado', valor_alvo=None, status_homologacao='PENDENTE_DECISAO')
        s = run(p, r, base_year=2013, final_year=2018)['series'][0]
        self.assertEqual(s['projecoes'], [])
        p, r = fixture(4); p['rows'][-2]['ruptura'] = True
        s = run(p, r, base_year=2013, final_year=2018)['series'][0]
        self.assertEqual(s['treino_anos'], [2012, 2013]); self.assertFalse(s['projecoes'])

    def test_future_reference_before_release_needs_scenario_even_for_lag(self):
        p, _ = enriched(); f = p['rows'][2]['features']['populacao']; f.update(disponivel_em='2010-01-01', referencia='2011-12-31')
        with self.assertRaisesRegex(ValueError, 'SEM_CENARIO'):
            feature_row(p['rows'][:2], 2012, p['rows'][2], p['feature_definitions'], '2011-12-31')

    def test_ratio_zero_denominator_not_silently_imputed(self):
        p, _ = enriched(); definitions = deepcopy(p['feature_definitions'])
        definitions['area'] = {**definitions['populacao'], 'unidade': 'km2', 'permite_imputacao': False}
        definitions['populacao']['dividir_por'] = ['area']
        source = deepcopy(p['rows'][2]); source['features']['area'] = {**source['features']['populacao'], 'valor': 0, 'unidade': 'km2'}
        with self.assertRaisesRegex(ValueError, 'DERIVADA_AUSENTE'):
            feature_row(p['rows'][:2], 2012, source, definitions, '2011-12-31')

    def test_scoped_features_and_shared_features_join_without_fanout(self):
        p, r = enriched(4); p['rows'] = p['rows'][:4]
        p['feature_definitions']['estado_ativo'] = {**p['feature_definitions']['populacao'], 'objetivos_aplicaveis': ['consumidores', 'geradores']}
        other = deepcopy(p['rows'])
        for row in p['rows']: row['features']['estado_ativo'] = {**row['features']['populacao'], 'valor': 1}
        for row in other:
            row['objetivo_id'] = 'geradores'; row['features']['estado_ativo'] = {**row['features']['populacao'], 'valor': 2}
        p['rows'] += other
        with tempfile.TemporaryDirectory() as td:
            b = Path(td)/'bundle'; write_bundle(p, r, b); restored = read_bundle(b, r)
            self.assertEqual(len(restored['rows']), 8)
            _, pq = arrow(); self.assertEqual(pq.read_table(b/'features.parquet').num_rows, 4)
            self.assertEqual(pq.read_table(b/'features_objetivo.parquet').num_rows, 8)
            for row in restored['rows']:
                self.assertEqual(row['features']['estado_ativo']['valor'], 1 if row['objetivo_id'] == 'consumidores' else 2)
                self.assertEqual(row['features']['estado_ativo']['versao'], 'SINTETICO-v1')

    def test_duplicate_scoped_key_rejected_even_with_matching_hash(self):
        p, r = enriched(4); p['feature_definitions']['populacao']['objetivos_aplicaveis'] = ['consumidores']
        with tempfile.TemporaryDirectory() as td:
            b = Path(td)/'bundle'; write_bundle(p, r, b)
            alter_table(b, 'features_objetivo.parquet', lambda pa, t: pa.concat_tables([t, t.slice(0, 1)]))
            with self.assertRaisesRegex(ValueError, 'wide duplicadas'): read_bundle(b, r)

    def test_reserved_wide_names_and_wrong_arrow_types_rejected(self):
        p, r = fixture(4)
        with self.assertRaisesRegex(ValueError, 'reservado'):
            _feature_schema({'ANO': {'tipo': 'numerica'}})
        with tempfile.TemporaryDirectory() as td:
            b = Path(td)/'bundle'; write_bundle(p, r, b)
            alter_table(b, 'features.parquet', lambda pa, t: t.set_column(0, 'ANO', pa.array([2010,2011,2012,2013], type=pa.int64())))
            with self.assertRaisesRegex(ValueError, 'Tipos Parquet'): read_bundle(b, r)

    def test_orphan_feature_dist_rejected(self):
        p, r = fixture(4)
        with tempfile.TemporaryDirectory() as td:
            b = Path(td)/'bundle'; write_bundle(p, r, b)
            alter_table(b, 'features.parquet', lambda pa, t: t.set_column(1, 'DIST', pa.array(['999']*4)))
            with self.assertRaisesRegex(ValueError, 'sem linha correspondente'): read_bundle(b, r)

    def test_future_features_join_by_series_not_global_last_year(self):
        p, r = fixture(4); second = deepcopy(p['rows'])
        for row in second: row.update(DIST='6600', territorio={'nivel':'dist', 'id':'6600'}, ano=row['ano']+1, competencia=f"{row['ano']+1}-12-31", disponivel_em=None)
        p['rows'] += second
        with tempfile.TemporaryDirectory() as td:
            b = Path(td)/'bundle'; write_bundle(p, r, b)
            def add(pa, t):
                return pa.concat_tables([t, pa.Table.from_pylist([{'ANO':2014, 'DIST':'26'}], schema=t.schema)])
            alter_table(b, 'features.parquet', add)
            restored = read_bundle(b, r)
            future = [x for x in restored['rows'] if x['DIST']=='26' and x['ano']==2014]
            self.assertEqual(len(future),1); self.assertIsNone(future[0]['valor_alvo'])
            self.assertTrue(future[0]['proveniencia']['features_only'])

    def test_legacy_parquet_v1_still_readable(self):
        p, r = enriched(4)
        with tempfile.TemporaryDirectory() as td:
            b = Path(td)/'bundle'; write_bundle(p, r, b)
            _, pq = arrow(); t = pq.read_table(b/'features.parquet')
            pq.write_table(t.select(_feature_schema(p['feature_definitions'], version=1).names), b/'features.parquet')
            mf=b/'manifest.json'; m=json.loads(mf.read_text()); m['schema_version']='bdgd-parquet-1'; m.pop('objective_feature_key'); m['sha256']['features.parquet']=sha(b/'features.parquet'); mf.write_text(json.dumps(m))
            restored = read_bundle(b, r); self.assertEqual(len(restored['rows']), len(p['rows']))

    def test_new_asset_runs_through_enriched_contract(self):
        p, r = enriched(4)
        new = {**deepcopy(r['objetivos'][0]), 'objetivo_id': 'BAY_SINTETICO', 'nome': 'Bay de teste', 'entidades': ['BAY']}
        r['objetivos'].append(new)
        for row in p['rows']: row['objetivo_id'] = 'BAY_SINTETICO'
        with tempfile.TemporaryDirectory() as td:
            b=Path(td)/'bundle'; write_bundle(p,r,b); restored=read_bundle(b,r)
            s=run(restored,r,base_year=2013,final_year=2016,candidates=['persistencia'])['series'][0]
            self.assertEqual(s['objetivo_id'],'BAY_SINTETICO'); self.assertEqual(len(s['projecoes']),3)


class TerritorialIntegrationTests(unittest.TestCase):
    def mapping(self):
        return {'schema_version':'municipios-dist-1','dataset_version':'SINTETICO-v1','rows':[
            {'ano':2025,'municipio':'2507507','DIST':dist,'peso':weight,'fonte':'SINTETICO','populacao_peso':'clientes_sinteticos','evidencia_rateio':'SINTETICO'}
            for dist, weight in [('26',0.4),('6600',0.6)]]}

    def test_multi_dist_municipality_not_duplicated_as_full_population(self):
        m=self.mapping(); self.assertFalse(validate_municipal_mapping(m)['agregacao_ativada'])
        for row in m['rows']: row['peso']=1
        with self.assertRaisesRegex(ValueError,'soma de pesos'): validate_municipal_mapping(m)

    def test_multi_dist_requires_evidence_unique_links_same_population(self):
        for change in ['evidence','duplicate','population']:
            with self.subTest(change=change):
                m=self.mapping()
                if change=='evidence': m['rows'][0].pop('evidencia_rateio')
                elif change=='duplicate': m['rows'].append(deepcopy(m['rows'][0]))
                else: m['rows'][0]['populacao_peso']='area_sintetica'
                with self.assertRaises(ValueError): validate_municipal_mapping(m)


class CoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=registry_from_catalog(CATALOG); cls.p=national_panel(ROOT/'output-historico/contrato-integracao',cls.r)
        cls.report=run(cls.p,cls.r,candidates=['persistencia'])
        cls.rows,cls.summary=coverage(cls.p,cls.r,cls.report)

    def test_real_catalog_and_missing_metrics_exactly_accounted(self):
        s=self.summary
        self.assertEqual((s['esperado'],s['observado'],s['elegivel'],s['bloqueado'],s['ausente_no_contrato']),(3306,2850,1545,1305,456))
        missing={(x['OBJETIVO_ID'],x['METRICA']) for x in self.rows if x['STATUS']=='AUSENTE_NO_CONTRATO'}
        self.assertEqual(missing,{(a,'potencia_kva') for a in ['trafo_dist','trafo_forca','trafo_medida','reguladores']})
        self.assertEqual(len({(x['DIST'],x['OBJETIVO_ID'],x['METRICA']) for x in self.rows}),3306)

    def test_every_block_has_traceable_primary_and_year_causes(self):
        blocked=[x for x in self.rows if x['STATUS']=='BLOQUEADA']
        self.assertEqual(sum(self.summary['causa_principal_exclusiva'].values()),1305)
        self.assertTrue(all(x['MOTIVO_BLOQUEIO'] and x['EVIDENCIAS_ANUAIS'] and x['RESOLUCAO']!='NAO_NECESSARIA' for x in blocked))
        self.assertTrue(all(x['MOTIVO_BLOQUEIO']!='OUTROS' for x in blocked))

    def test_catalog_overlap_not_independent_additive_stock(self):
        pairs=overlap_audit(self.r)
        self.assertTrue(any({x['objetivo_a'],x['objetivo_b']}=={'chaves','seccionalizadores'} for x in pairs))
        self.assertFalse(any({x['objetivo_a'],x['objetivo_b']}=={'trafo_dist','trafo_forca'} for x in pairs))

    def test_synthetic_blocker_taxonomy_and_boundary_year(self):
        cases = [({'valor_alvo': None, 'status_qualidade': 'ausente'}, 'AUSENCIA_OBSERVACOES'),
                 ({'valor_alvo': None, 'status_qualidade': 'nao_homologado', 'status_homologacao': 'PENDENTE_DECISAO'}, 'FALTA_HOMOLOGACAO'),
                 ({'valor_alvo': 0, 'status_qualidade': 'zero_tecnico'}, 'ZERO_TECNICO_SEM_EVIDENCIA'),
                 ({'valor_alvo': None, 'status_qualidade': 'nao_aplicavel'}, 'NAO_APLICAVEL'),
                 ({'cobertura': 0.5}, 'COBERTURA_INCOMPLETA'),
                 ({'nao_somar': True}, 'SOBREPOSICAO_ATIVOS'),
                 ({'ruptura': True}, 'RUPTURA_CADASTRAL'),
                 ({'disponivel_em': '2030-01-01'}, 'INCOMPATIBILIDADE_TEMPORAL')]
        for change, cause in cases:
            with self.subTest(cause=cause):
                p,r=fixture(4); p['rows'][-1].update(change)
                report=run(p,r,base_year=2013,final_year=2018,candidates=['persistencia'])
                rows,_=coverage(p,r,report)
                item=next(x for x in rows if x['OBJETIVO_ID']=='consumidores')
                self.assertEqual(item['MOTIVO_BLOQUEIO'],cause)
                if cause != 'INCOMPATIBILIDADE_TEMPORAL':
                    self.assertIn('HISTORICO_INSUFICIENTE',item['CAUSAS_CONTRIBUINTES'])
        p,r=fixture(2); report=run(p,r,base_year=2011,final_year=2016,candidates=['persistencia'])
        rows,_=coverage(p,r,report)
        self.assertEqual(next(x for x in rows if x['OBJETIVO_ID']=='consumidores')['MOTIVO_BLOQUEIO'],'HISTORICO_INSUFICIENTE')

    def test_feature_completeness_does_not_change_target_eligibility(self):
        p,r=enriched(4); p['rows']=p['rows'][:4]
        a=run(p,r,base_year=2013,final_year=2018,candidates=['persistencia'])
        p['feature_definitions']={}
        for row in p['rows']: row['features']={}
        b=run(p,r,base_year=2013,final_year=2018,candidates=['persistencia'])
        self.assertEqual(a['series'][0]['projecoes'],b['series'][0]['projecoes'])
