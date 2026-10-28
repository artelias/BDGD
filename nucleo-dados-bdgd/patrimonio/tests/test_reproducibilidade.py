"""Gzip container metadata is not normative content; corruption must still fail."""
import gzip,tempfile,unittest
from pathlib import Path
from patrimonio.verify import compare_gzip,compare_file
class ReproducibilityTests(unittest.TestCase):
 def test_python_os_byte_does_not_change_payload(self):
  with tempfile.TemporaryDirectory() as tmp:
   a=Path(tmp)/'a.gz';b=Path(tmp)/'b.gz';value=gzip.compress(b'{"SINTETICO":true}',mtime=0)
   a.write_bytes(value[:9]+b'\x03'+value[10:]);b.write_bytes(value[:9]+b'\xff'+value[10:])
   self.assertNotEqual(a.read_bytes(),b.read_bytes());self.assertTrue(compare_gzip(a,b))
 def test_payload_mutation_is_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   a=Path(tmp)/'a.gz';b=Path(tmp)/'b.gz';a.write_bytes(gzip.compress(b'{"valor":null}',mtime=0));b.write_bytes(gzip.compress(b'{"valor":0}',mtime=0))
   with self.assertRaises(ValueError):compare_gzip(a,b)
 def test_parquet_value_mutation_is_rejected(self):
  import pyarrow as pa,pyarrow.parquet as pq
  with tempfile.TemporaryDirectory() as tmp:
   a=Path(tmp)/'a.parquet';b=Path(tmp)/'b.parquet';pq.write_table(pa.table({'codigo':['SINTETICO'],'valor':[1]}),a);pq.write_table(pa.table({'codigo':['SINTETICO'],'valor':[2]}),b)
   with self.assertRaises(ValueError):compare_file(a,b)
