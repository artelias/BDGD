"""Fixtures de registros exclusivamente SINTÉTICAS; fontes documentais reais somente leitura."""
from copy import deepcopy
import hashlib,json,tempfile,unittest
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
from patrimonio.engine import load_dictionary,translate,technical,enrich_record,code
from patrimonio.parquet import enrich_parquets
from patrimonio.features import to_feature

D=load_dictionary()

class DocumentTests(unittest.TestCase):
 def test_does_not_mislabel_rev2_as_rev3(self):
  self.assertEqual(D['source']['revisao_lida'],'2')
  self.assertTrue(all(x['status']=='PENDENTE_VERIFICACAO_NORMATIVA' for x in D['vigencias'].values()))
 def test_all_tables_distinct_and_no_power_in_voltage(self):
  self.assertEqual(len(D['tucs']),105)
  self.assertIn('IIIA',D['tabelas']);self.assertIn('VIII_A6',D['tabelas'])
  self.assertFalse(any('kVAR' in x['descricao'] for x in D['tabelas']['II']))
  self.assertEqual(len(D['tabelas']['VI']),7)
 def test_power_not_always_a4(self):
  self.assertEqual(D['tucs']['340']['slots']['A3']['tabela'],'IIIB')
  self.assertEqual(D['tucs']['340']['slots']['A4']['tabela'],'V')
  self.assertEqual(D['tucs']['565']['slots']['A4']['tabela'],'IIIB')
  self.assertEqual(D['tucs']['575']['slots']['A4']['tabela'],'CONDICIONAL:575:A4')
 def test_575_table_depends_on_type_of_good(self):
  a=translate(D,'575','01','A4','01',2025);b=translate(D,'575','02','A4','01',2025)
  self.assertEqual(a['tabela'],'XII');self.assertEqual(b['tabela'],'XIV')
  self.assertNotEqual(a['descricao'],b['descricao'])
  self.assertIsNone(a['valor_tecnico'])
 def test_subtype_13503_restarts_attributes(self):
  a=translate(D,'135','03','A3','01',2025)
  self.assertEqual(a['descricao'],'PORCELANA')
  b=translate(D,'135','01','A3','01',2025)
  self.assertEqual(b['descricao'],'COBRE')
 def test_material_local_code_kept_with_source_page(self):
  a=translate(D,'135','01','A3','01',2025)
  self.assertEqual(a['pagina'],174);self.assertEqual(a['codigo_original'],'01')
 def test_normative_duplicate_code_does_not_pick_first(self):
  a=translate(D,'565','01','A2','91',2025)
  self.assertEqual(a['status'],'CODIGO_AMBIGUO');self.assertIsNone(a['valor_tecnico'])
 def test_ranges_are_not_exact_power(self):
  a=translate(D,'565','01','A4','29',2025)
  self.assertEqual(a['natureza_valor'],'FAIXA');self.assertIsNone(a['valor_tecnico'])
  self.assertEqual(a['unidade'],'kVA');self.assertIn('75',a['descricao'])
  self.assertTrue(all(technical(x['descricao'])['valor_tecnico'] is None for x in D['tabelas']['IIIB']))
 def test_distinguish_missing_not_applicable_and_unknown(self):
  self.assertEqual(translate(D,'565','01','A4',None,2025)['status'],'VAZIO')
  self.assertEqual(translate(D,'565','01','A4','NA',2025)['status'],'NAO_APLICAVEL_DECLARADO')
  self.assertEqual(translate(D,'565','01','A4','ZZ',2025)['status'],'CODIGO_NAO_TRADUZIDO')
  self.assertEqual(translate(D,'580','01','A6','01',2025)['status'],'NAO_APLICAVEL_DOCUMENTAL')
 def test_unknown_tuc_and_unknown_a1_not_inferred(self):
  self.assertEqual(translate(D,'656','01','A4','29',2025)['status'],'TUC_NAO_TRADUZIDO')
  self.assertEqual(translate(D,'565','57','A4','29',2025)['status'],'A1_NAO_TRADUZIDO')
 def test_unreviewed_slots_not_numbered_by_guess(self):
  a=translate(D,'590','01','A4','29',2025)
  self.assertEqual(a['status'],'SLOT_NAO_VERIFICADO')
 def test_cannot_activate_features_on_rev2_documental_mapping(self):
  a=translate(D,'565','01','A4','29',2025)
  with self.assertRaisesRegex(ValueError,'BLOQUEADA'):
   to_feature(a,referencia='2025-12-31',disponivel_em='2026-01-01',fonte='SINTETICO',versao='SINTETICO')
 def test_zero_and_leading_zero_not_technical_zero(self):
  a=translate(D,'565','01','A4','0',2025)
  self.assertEqual(a['codigo'],'00');self.assertIsNone(a['valor_tecnico'])
  self.assertEqual(code('01',2),'01')
  for bad in [True,1.2]:
   with self.assertRaises(ValueError):code(bad,2)
 def test_exact_unit_conversion_and_compounds(self):
  self.assertEqual(technical('1,25 MVA')['valor_tecnico'],'1250.00')
  self.assertIsNone(technical('20/26,6/33,3 MVA')['valor_tecnico'])
  self.assertIsNone(technical('até 5 kA')['valor_tecnico'])
 def test_native_power_namespace_differs_from_a4(self):
  e=enrich_record(D,{'COD_ID':'SINTETICO','TUC':'565','A1':'01','A4':'29','POT_NOM':'29'},entity='EQTRMT',dist='26',year=2025,publication='SINTETICO')
  self.assertIsNone(e['potencia']['potencia_recuperada_homologada_kva'])
  self.assertIsNotNone(e['potencia']['campo_nativo'])
  self.assertNotIn('anterior',e['potencia']['campo_nativo']['descricao'])
 def test_unknown_native_power_not_zero(self):
  for v in ['0',None,'','9999']:
   e=enrich_record(D,{'COD_ID':'SINTETICO','TUC':'565','A1':'01','POT_NOM':v},entity='EQTRMT',dist='26',year=2025,publication='SINTETICO')
   self.assertIsNone(e['potencia']['campo_nativo'])
 def test_installation_power_unit_not_assumed_across_years(self):
  e=enrich_record(D,{'COD_ID':'SINTETICO','POT_NOM':25.0},entity='UNTRAT',dist='26',year=2022,publication='SINTETICO')
  self.assertIsNone(e['potencia']['campo_nativo']['valor_candidato_kva'])
  self.assertFalse(e['somavel_com_eq'])
 def test_scope_and_provenance_required(self):
  with self.assertRaisesRegex(ValueError,'Proveniência'):enrich_record(D,{'COD_ID':'SINTETICO'},entity='EQTRMT',dist='26',year=2025,publication='')
  with self.assertRaisesRegex(ValueError,'DIST'):enrich_record(D,{'COD_ID':'SINTETICO','DIST':'6600'},entity='EQTRMT',dist='26',year=2025,publication='SINTETICO')

class ParquetTests(unittest.TestCase):
 def inputs(self,root,rows=None,entity='EQTRMT'):
  path=Path(root)/'synthetic-input.parquet';pq.write_table(pa.Table.from_pylist(rows or [{'COD_ID':'SINTETICO','DIST':'26','TUC':'565','A1':'01','A4':'29','A6':None}]),path)
  m={'schema_version':'parquets-patrimonio-1','dataset_version':'SINTETICO-1','sintetico':True,'files':[{'path':str(path),'ANO':2025,'DIST':'26','ENTIDADE':entity,'PUBLICACAO':'SINTETICO','status_fonte':'PENDENTE_DECISAO','sha256':hashlib.sha256(path.read_bytes()).hexdigest()}]}
  return path,m
 def test_roundtrip_no_source_modification_or_target_activation(self):
  with tempfile.TemporaryDirectory() as root:
   path,m=self.inputs(root);before=path.read_bytes();r=enrich_parquets(m,D,Path(root)/'out')
   self.assertEqual(path.read_bytes(),before);self.assertFalse(r['targets_modificados']);self.assertFalse(r['agregacao_eq_un'])
   table=pq.read_table(Path(root)/'out/enriquecido-00000.parquet').to_pylist()
   self.assertEqual(len(table),1);self.assertFalse(table[0]['ELEGIVEL_MODELO']);self.assertIsNone(table[0]['POTENCIA_HOMOLOGADA_KVA'])
   self.assertFalse((Path(root)/'out/_cardinalidade.sqlite').exists())
 def test_duplicates_not_silently_deduplicated(self):
  with tempfile.TemporaryDirectory() as root:
   row={'COD_ID':'SINTETICO','TUC':'565','A1':'01'};_,m=self.inputs(root,[row,row])
   with self.assertRaisesRegex(ValueError,'duplicada'):enrich_parquets(m,D,Path(root)/'out')
 def test_eq_and_un_remain_separate_even_same_cod_id(self):
  with tempfile.TemporaryDirectory() as root:
   _,m=self.inputs(root);other=deepcopy(m['files'][0]);other['ENTIDADE']='UNTRMT';m['files'].append(other)
   r=enrich_parquets(m,D,Path(root)/'out');self.assertEqual(len(r['inventario']),2);self.assertFalse(r['agregacao_eq_un'])
 def test_tampered_hash_rejected_and_existing_output_preserved(self):
  with tempfile.TemporaryDirectory() as root:
   _,m=self.inputs(root);m['files'][0]['sha256']='BAD'
   with self.assertRaisesRegex(ValueError,'Hash'):enrich_parquets(m,D,Path(root)/'out')
   with self.assertRaises(FileExistsError):enrich_parquets(m,D,Path(root)/'out')
 def test_cross_publication_rows_not_merged_or_approved(self):
  with tempfile.TemporaryDirectory() as root:
   _,m=self.inputs(root);other=deepcopy(m['files'][0]);other['PUBLICACAO']='SINTETICO-DIVERGENTE';m['files'].append(other)
   r=enrich_parquets(m,D,Path(root)/'out');self.assertEqual(len(r['inventario']),2)
   self.assertTrue(all(x['status_fonte']=='PENDENTE_DECISAO' for x in r['inventario']))

if __name__=='__main__':unittest.main()
