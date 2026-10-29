import tempfile, unittest
from pathlib import Path
import duckdb
from motor_v2.runner import scenario_values,eligible,select,score,extract_uc
from motor_v2.ml import exposure,split

class Contracts(unittest.TestCase):
 def test_scenario_regression_crossing(self):
  with self.assertRaises(ValueError):scenario_values([100,50],[.1,0,-.1])
  v=scenario_values([100,50],[-.01,0,.01]);self.assertTrue(all(v[0][i]<=v[1][i]<=v[2][i] for i in range(2)))
 def test_release_prevents_leak(self):
  self.assertFalse(eligible({'available':'2026-09-01','value':100},'2023-12-31'))
  self.assertFalse(eligible({'available':None,'value':100},'2023-12-31'))
 def test_model_selection_same_tests(self):
  base=[dict(key=str(i),actual=100,pred=101) for i in range(3)]
  self.assertEqual(select({'persistencia':base,'ridge':[dict(key='0',actual=100,pred=100)]})[0],'persistencia')
 def test_small_sample_baseline(self):self.assertEqual(select({})[0],'persistencia')
 def test_exposure_no_state_shortcut(self):
  with self.assertRaises(ValueError):exposure({'1100015':1000},['1100015'])
  self.assertEqual(exposure({'1100015':1000},['1100015'],{'1100015':.2}),200)
 def test_group_and_date_split(self):
  rows=[dict(year=2022,released='2022-12-31',comparable=True,group='a',x=[1]),dict(year=2022,released='2026-01-01',comparable=True,group='b',x=[1]),dict(year=2023,released='2024-01-01',comparable=True,group='a',x=[1])]
  train,test=split(rows,2022,{'a'});self.assertEqual(train,[]);self.assertEqual(len(test),1)
 def test_composite_identity_and_missing_energy(self):
  with tempfile.TemporaryDirectory(dir='D:/NUCLEO_BDGD_2025/motor_v2') as td:
   p=Path(td);con=duckdb.connect();con.execute("CREATE TABLE input(COD_ID varchar,PN_CON varchar,SIT_ATIV varchar,MUN varchar,CONJ varchar,CTMT varchar,ARE_LOC varchar)")
   con.executemany('INSERT INTO input VALUES (?,?,?,?,?,?,?)',[('x','p1','AT','1200401','c','f','UB'),('x','p2','AT','1200401','c','f','UB'),('x','p1','DS','1200401','c','f','UB')]);con.execute("COPY input TO '"+(p/'UCBT.parquet').as_posix()+"' (FORMAT PARQUET)")
   qa=extract_uc(con,{'base':str(p),'year':2022},p);self.assertEqual(qa['value'],2);self.assertEqual(qa['coverage'],1);self.assertEqual(qa['energy_columns'],0)
   self.assertIsNone(con.execute("SELECT sum(energia_kwh) FROM read_parquet('"+(p/'territorial.parquet').as_posix()+"')").fetchone()[0]);con.close()
if __name__=='__main__':unittest.main()
