import unittest, tempfile, subprocess, sys, time, json, os
from pathlib import Path
import duckdb,psutil
from motor_v2.runner import atomic,read,ROOT

class ExecutorIntegration(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir='D:/NUCLEO_BDGD_2025/motor_v2',prefix='integration-');self.p=Path(self.tmp.name);self.output=self.p/'output';self.config=self.p/'config.json'
  sources=[];con=duckdb.connect()
  for year in range(2022,2026):
   base=self.p/'inputs'/str(year);base.mkdir(parents=True);f=base/'UCBT.parquet'
   if year==2025:f=base/'entidade=UCBT/part-0.parquet';f.parent.mkdir()
   con.execute("COPY (SELECT 'id'||i COD_ID,'p' PN_CON,'AT' SIT_ATIV,'1200401' MUN,'c' CONJ,'f' CTMT,'UB' ARE_LOC FROM range(10000) t(i)) TO '"+f.as_posix()+"' (FORMAT PARQUET)")
   sources.append(dict(year=year,item='synthetic-'+str(year),base=str(base),available=f'{year}-12-31',source_sha='synthetic-test-only',rupture=False,homologation='SINTETICO_NAO_HOMOLOGADO'))
  con.close();atomic(self.p/'sources.json',{'26':sources});atomic(self.config,dict(output=str(self.output),dists=[26],memory='256MB',threads=1,min_folds=3,as_of='2026-10-28',scenario_rates=[0,0,0],seed=42,max_trials=1,task_timeout_seconds=60,sources_manifest=str(self.p/'sources.json'),synthetic=True))
 def tearDown(self):
  # Retain failures for audit rather than deleting a possibly live worker's files.
  if hasattr(self,'done') and self.done:self.tmp.cleanup()
 def control(self,action):
  return subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'motor_v2/control.ps1'),action,'-Config',str(self.config)],capture_output=True,text=True,timeout=30,check=True)
 def wait(self,launch_id=None):
  deadline=time.monotonic()+90
  while time.monotonic()<deadline:
   p=self.output/'status.json'
   if p.exists():
    r=read(p)
    if r.get('launch_id')==launch_id and r['state'] in ['completed','failed','stopped','completed_with_errors'] and not (self.output/'executor.lock').exists():
     # A final status precedes interpreter/venv-redirector teardown on Windows.
     pids=[r['pid']]
     if launch_id:pids.append(read(self.output/'launch.json')['launcher_pid'])
     for pid in pids:
      try:psutil.Process(pid).wait(timeout=10)
      except psutil.NoSuchProcess:pass
     # keep the run for audit unless it completed cleanly (a completed_with_errors run is evidence, not garbage)
     self.done=r['state']=='completed'
     if r['state']=='completed_with_errors':self.diagnose(r)
     return r
   time.sleep(.2)
  self.fail('executor did not finish')
 def diagnose(self,r):
  # A DIST that fails leaves failure_<dist>.json (RAM guard, task budget, worker exit). Show it instead of an opaque state mismatch; the 60 s budget is NOT raised.
  run=Path(r['output']);fails={f.name:read(f) for f in sorted(run.glob('failure_*.json'))};free=psutil.virtual_memory().available/2**30
  # The RAM guard refuses to start a DIST below its floor by design: that is the machine, not the executor. Only that exact case is a skip; anything else fails.
  if fails and all(x['error'].startswith('available RAM') for x in fails.values()):self.skipTest(f"resource guard refused the DIST (machine under memory pressure, {free:.2f} GiB free now): {[x['error'] for x in fails.values()]}")
  tails={f.name:f.read_text(encoding='utf-8',errors='replace')[-800:] for f in sorted(run.glob('task_*.log'))}
  self.fail(f"executor finished {r['state']} ({r.get('completed')}/{r.get('total')}); failures={ {k:(v['error'],v['traceback'][-500:]) for k,v in fails.items()} }; task_log_tail={tails}; available_ram_gib={free:.2f}; run retained at {run}")
 def test_detached_resume_and_invalidation(self):
  parent=self.control('start');receipt=json.loads(parent.stdout);pid=receipt['launcher_pid'];launcher_exited=time.time()
  self.assertTrue(psutil.pid_exists(pid),'child must remain alive after PowerShell and launch.py exit')
  first=self.wait(receipt['launch_id']);self.assertEqual(first['state'],'completed');run=Path(first['output']);files=list(run.glob('26/ucbt_quantidade/*/territorial.parquet'));self.assertEqual(len(files),4);stamps={str(p):p.stat().st_mtime_ns for p in files}
  self.assertTrue(any(p.stat().st_mtime>launcher_exited for p in files),'executor must produce outputs after its launcher exits')
  self.control('stop');self.assertTrue((self.output/'STOP').exists());receipt=json.loads(self.control('resume').stdout);second=self.wait(receipt['launch_id']);self.assertEqual(second['state'],'completed');self.assertEqual(stamps,{str(p):p.stat().st_mtime_ns for p in files})
  # Corrupt an aggregate only: resume must repair that checkpoint, not the other years.
  target=files[0];target.write_bytes(b'corrupted');receipt=json.loads(self.control('resume').stdout);third=self.wait(receipt['launch_id']);self.assertEqual(third['state'],'completed')
  self.assertNotEqual(stamps[str(target)],target.stat().st_mtime_ns)
  self.assertTrue(all(p.stat().st_mtime_ns==stamps[str(p)] for p in files if p!=target))
  self.assertTrue(list(run.glob('bundle-*/manifest.json')))
 def test_stop_gate_before_task(self):
  self.output.mkdir();(self.output/'STOP').write_text('test')
  subprocess.run([sys.executable,'-m','motor_v2.runner','--config',str(self.config)],cwd=ROOT,timeout=40,check=True,capture_output=True)
  state=self.wait();self.assertEqual(state['state'],'stopped');self.assertEqual(state['completed'],0)

class DiagnoseFailure(unittest.TestCase):
 """diagnose() on fabricated run folders: only the RAM guard is a skip, every other failure stays a failure with its evidence (no timeout is raised)."""
 def run_dir(self,error):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);run=Path(tmp.name)
  atomic(run/'failure_26.json',dict(error=error,traceback='Traceback ... sentinel-traceback'));(run/'task_26.log').write_text('worker log sentinel',encoding='utf-8')
  return dict(state='completed_with_errors',completed=0,total=1,output=str(run))
 def test_resource_guard_is_an_explicit_skip(self):
  with self.assertRaises(unittest.SkipTest) as c:ExecutorIntegration.diagnose(self,self.run_dir('available RAM 0.3 GiB below the 0.5 GiB floor; close applications and retry'))
  self.assertIn('resource guard',str(c.exception))
 def test_task_budget_exceeded_is_a_failure_with_evidence(self):
  with self.assertRaises(AssertionError) as c:ExecutorIntegration.diagnose(self,self.run_dir('task budget exceeded; annual checkpoints retained'))
  m=str(c.exception);self.assertIn('task budget exceeded',m);self.assertIn('sentinel-traceback',m);self.assertIn('worker log sentinel',m);self.assertIn('available_ram_gib',m)
 def test_mixed_failures_are_not_masked_by_the_guard(self):
  r=self.run_dir('available RAM 0.3 GiB below the 0.5 GiB floor');atomic(Path(r['output'])/'failure_31.json',dict(error='worker failed; inspect task log',traceback='x'))
  with self.assertRaises(AssertionError):ExecutorIntegration.diagnose(self,r)
 def test_no_failure_file_is_a_failure_not_a_skip(self):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
  with self.assertRaises(AssertionError):ExecutorIntegration.diagnose(self,dict(state='completed_with_errors',completed=0,total=1,output=tmp.name))

if __name__=='__main__':unittest.main()
