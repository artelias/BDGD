import copy,unittest
from motor_v2.temporal import usable,label
from motor_v2.comparison import summarise,scope_pool,options
class TemporalTests(unittest.TestCase):
 def row(self):return dict(year=2023,feature_year=2022,feature_available='2022-12-31',feature_revision_available='2022-12-31',target_available='2023-12-31')
 def test_future_revision_rejected(self):
  r=self.row();r['feature_revision_available']='2025-01-01';self.assertFalse(usable(r,2023,'point_in_time'))
 def test_future_training_target_rejected(self):
  r=self.row();r['target_available']='2026-01-01';self.assertFalse(usable(r,2023,'point_in_time'))
 def test_reconciled_does_not_mutate_dates(self):
  r=self.row();r['target_available']='2026-01-01';before=copy.deepcopy(r);self.assertTrue(usable(r,2023,'reconciled_retrospective'));self.assertEqual(before,r);self.assertIn('NOT_operational',label('reconciled_retrospective'))
 def test_future_competence_blocked_in_both_modes(self):
  for mode in ['point_in_time','reconciled_retrospective']:self.assertFalse(usable(self.row(),2022,mode))
 def test_target_year_covariate_blocked(self):
  r=self.row();r['feature_year']=2023;self.assertFalse(usable(r,2024,'reconciled_retrospective'))
 def test_two_origins_are_not_three_independent_tests(self):
  rs=[dict(key=str(i),origin=2023+i%2,actual=10,pred=11) for i in range(9)]
  good=[dict(r,pred=10) for r in rs]
  e=lambda p:dict(predictions=p,folds=[],failures=[])
  result=summarise({'persistencia:individual':e(rs),'ridge:individual':e(good)},3);self.assertFalse(result['validated_winner']);self.assertEqual(result['winner'],'persistencia:individual')
 def test_unequal_test_population_not_compared(self):
  e=lambda p:dict(predictions=p,folds=[],failures=[])
  r=dict(key='a',origin=2023,actual=10,pred=11)
  result=summarise({'persistencia:individual':e([r]),'ridge:individual':e([dict(r,key='b',pred=10)])},3)
  self.assertFalse(next(c for c in result['candidates'] if c['candidate'].startswith('ridge'))['common_test_set'])
if __name__=='__main__':unittest.main()
