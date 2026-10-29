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
     self.done=True;return r
   time.sleep(.2)
  self.fail('executor did not finish')
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

if __name__=='__main__':unittest.main()
