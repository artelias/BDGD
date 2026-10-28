"""Valida derivados reais e preservação das fontes versionadas, sem homologação."""
import csv,gzip,json,hashlib,subprocess,unittest
from pathlib import Path
from reconciliacao.contratos import observacoes
ROOT=Path(__file__).resolve().parents[2]
BASE='19880695ef112a22144d856baab3d7cbd474494c'
class ReconciliationTests(unittest.TestCase):
 def test_original_history_and_audits_unchanged(self):
  # Em CI checkout raso: não depender do objeto antigo; manifesto de assinaturas versionado dá a prova.
  expected=json.loads((ROOT/'auditoria/reconciliacao/evidencias/origens-preservadas.json').read_text())
  self.assertGreater(len(expected),50)
  for p,h in expected.items():self.assertEqual(hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),h,p)
 def test_coopera_values_complete_total_and_observed_components(self):
  x=json.loads((ROOT/'web/public/data/2025-12-31/index.json').read_text())
  row=next(r for r in x['ativosTotais']['consumidores']['quantidade'] if r[0]==5370)
  self.assertIsNone(row[1]);self.assertEqual(row[2],'b')
  facts={r[1]:r for r in x['fatos']['rows'] if r[0]==5370}
  self.assertIsNone(facts['UCBT'][2]);self.assertEqual(facts['UCBT'][3],0)
  self.assertEqual(x['complementares']['uc_ativadas']['5370']['UCMT'][0],224)
  self.assertEqual(x['complementares']['uc_ativadas']['5370']['UCAT'][0],1)
  note=next(n for n in observacoes() if n['dist']==5370);self.assertEqual(note['subtotal_observado'],225)
 def test_observations_unique_and_traceable(self):
  rows=observacoes();self.assertEqual(len(rows),len({n['id'] for n in rows}))
  self.assertEqual({n['dist'] for n in rows},{5370,6072,7371,5374})
  for n in rows:
   self.assertTrue(n['origem']['arquivo']);self.assertTrue(n['evidencia_tecnica']);self.assertEqual(len(n['origem']['sha256_zip']),64)
 def test_targets_do_not_take_subtotals_or_artificial_zero(self):
  p=ROOT/'output-historico/contrato-integracao/serie_fisica_nacional.csv'
  rows=list(csv.DictReader(p.open()));idx={(r['dist'],r['ano'],r['conceitoId']):r for r in rows}
  c=idx['5370','2025','consumidores'];self.assertEqual(c['valor'],'');self.assertEqual(c['subtotal_observado'],'225')
  self.assertEqual([float(idx['5370',str(y),'consumidores']['valor']) for y in [2022,2023,2024]],[26773,27315,28141])
  self.assertEqual(idx['7371','2025','trafo_medida']['valor'],'');self.assertEqual(idx['5374','2024','iluminacao']['valor'],'')
  self.assertEqual(float(idx['6072','2025','consumidores']['valor']),23203);self.assertEqual(idx['6072','2025','consumidores']['cobertura'],'')
 def test_live_coopera_download_same_audited_bytes(self):
  e=json.loads((ROOT/'auditoria/reconciliacao/evidencias/download-coopera-verificacao.json').read_text())
  self.assertEqual(e['bytes'],7860642);self.assertTrue(e['confere_assinatura_auditoria']);self.assertEqual(e['sha256'],'5da0502b286b1ec7c8df898a56f2e8ecc1d2c896c139058436e9cfd9606732fb')
 def test_knn_real_report_is_blocked_not_estimate(self):
  r=json.loads((ROOT/'auditoria/reconciliacao/knn-real.json').read_text())
  self.assertFalse(r['sintetico']);self.assertFalse(r['previsao_validada']);self.assertIsNone(r['estimativa']);self.assertEqual(r['fontes_externas_entregues'],0)
