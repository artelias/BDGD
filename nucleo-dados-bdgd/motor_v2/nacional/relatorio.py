"""Writers for the national internal artefacts (LF line endings, UTF-8, integers stay integers)."""
import csv
import json
from pathlib import Path


def _cell(v):
    if v is None:
        return ''
    if isinstance(v, float) and v.is_integer() and abs(v) < 2**53 and False:
        return str(int(v))
    if isinstance(v, (dict, list, tuple, set)):
        return json.dumps(sorted(v) if isinstance(v, set) else v, ensure_ascii=False, default=str)
    return v


def write_csv(path, rows, fields=None):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or list(dict.fromkeys(k for r in rows for k in r))
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n', extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow({k: _cell(r.get(k)) for k in fields})
    return path


def write_parquet(path, rows):
    import pyarrow as pa
    import pyarrow.parquet as pq
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return path
    fields = list(dict.fromkeys(k for r in rows for k in r))
    norm = [{k: (json.dumps(r.get(k), ensure_ascii=False, default=str) if isinstance(r.get(k), (dict, list, tuple, set)) else r.get(k)) for k in fields} for r in rows]
    pq.write_table(pa.Table.from_pylist(norm), path, compression='zstd')
    return path
