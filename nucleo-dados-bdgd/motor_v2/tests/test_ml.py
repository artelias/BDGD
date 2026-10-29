import unittest
import numpy as np
from motor_v2.ml import build,search,Budget
class ML(unittest.TestCase):
 def test_scaler_fits_training_only(self):
  model=build('ridge',{'alpha':1},42);model.fit(np.array([[1.],[2.],[3.]]),[2.,4.,6.]);before=model.named_steps['scale'].mean_.copy();model.predict([[10000.]])
  np.testing.assert_array_equal(before,model.named_steps['scale'].mean_)
 def test_search_requires_nested_folds(self):
  result=search('ridge',[],[2022,2023],{'x'},Budget(trials=2,seconds=5));self.assertIsNone(result['winner'])
if __name__=='__main__':unittest.main()
