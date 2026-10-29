"""Shared attribute matrix by territorial unit and year, built only from the checkpointed aggregates of the BDGD Parquets.

Units: municipality (UCBT.MUN, UNTRMT.MUN) and conjunto (UCBT.CONJ, UNTRMT.CONJ, SSDMT.CONJ). The link is a field of the
records themselves; nothing is assigned by proximity. SSDMT has no MUN, so network length is NEVER attributed to a
municipality. Every family carries the availability date of its own publication (t-1), so point-in-time gates still apply.

Cross-family model features (values at t-1, original units first, log1p afterwards):
  urban_share / energy per client   <- UCBT, available to transformer and network assets
  log_ucbt_clients                  <- UCBT customers
  log_trafo_count / log_trafo_kva   <- TUC 565 transformers (EQ->UN bijective)
  log_clients_per_trafo, log_kva_per_client <- declared ratios; a non-positive or missing denominator gives no value"""
import csv
import math
from pathlib import Path
import duckdb
from .features import FEATURES, urban_share
from .runner import digest, read

FAMILIES = ('ucbt', 'trafo_count', 'trafo_kva', 'mt_km')
CROSS = ('urban_share', 'log_energy_per_client', 'log_ucbt_clients', 'log_trafo_count', 'log_trafo_kva', 'log_clients_per_trafo', 'log_kva_per_client')
# own-lag duplicates are never offered: the target's own previous value already is log_stock
SELF = {'trafo_dist_quantidade': 'log_trafo_count', 'trafo_dist_potencia_kva': 'log_trafo_kva', 'ucbt_quantidade': 'log_ucbt_clients'}
USES_CROSS = {'trafo_dist_quantidade', 'trafo_dist_potencia_kva', 'rede_mt_extensao_km'}
VALID = {'municipality': lambda u: bool(u) and len(u) == 7 and u.isdigit(), 'conjunto': lambda u: bool(u) and u != 'MISSING'}


def _history(root, dist, asset):
    p = Path(root) / str(dist) / asset / 'result.json'
    if not p.exists():
        return None
    out = read(p)
    for h in out['history']:
        f = p.parent / str(h['year']) / 'territorial.parquet'
        if digest(f) != read(f.parent / 'checkpoint.json')['output_sha256']:
            raise ValueError('aggregate hash mismatch: ' + str(f))
    return out


def _unit_col(kind):
    return 'MUN' if kind == 'municipality' else 'CONJ'


def build(asset_root, ucbt_root, dists, kind, years=(2022, 2023, 2024, 2025)):
    """-> {(dist, year, unit): dict(values={...original units}, avail={family: date})}."""
    db = duckdb.connect()
    db.execute("SET memory_limit='512MB'; SET threads=1")
    out, check = {}, VALID[kind]
    try:
        for dist in dists:
            u = _history(ucbt_root, dist, 'ucbt_quantidade')
            for h in (u['history'] if u else []):
                if h['year'] not in years:
                    continue
                f = Path(ucbt_root) / str(dist) / 'ucbt_quantidade' / str(h['year']) / 'territorial.parquet'
                col = _unit_col(kind)
                agg = {}
                for unit, area, n, en, kwh in db.execute(f'SELECT {col},upper(trim(ARE_LOC)),sum(clientes_ativos),sum(energia_denominador),sum(energia_kwh) '
                                                         'FROM read_parquet(?) GROUP BY ALL', [str(f)]).fetchall():
                    if not check(unit):
                        continue
                    a = agg.setdefault(unit, dict(n=0, areas={}, en=0, kwh=0.))
                    a['n'] += n; a['areas'][area or 'MISSING'] = a['areas'].get(area or 'MISSING', 0) + n; a['en'] += en; a['kwh'] += kwh or 0.
                for unit, a in agg.items():
                    cell = out.setdefault((dist, h['year'], unit), dict(values={}, avail={}))
                    cell['values']['ucbt_clients'] = float(a['n'])
                    cell['values']['ucbt_urban_share'] = urban_share(a['areas'])['share']
                    cell['values']['ucbt_energy_per_client'] = a['kwh'] / a['n'] if a['n'] and a['en'] == a['n'] and a['kwh'] >= 0 else None
                    cell['avail']['ucbt'] = h['available']
            for asset, family, measure in (('trafo_dist_quantidade', 'trafo_count', 'value'), ('trafo_dist_potencia_kva', 'trafo_kva', 'value'),
                                           ('rede_mt_extensao_km', 'mt_km', 'value')):
                if family == 'mt_km' and kind != 'conjunto':
                    continue                       # SSDMT has no municipality: never attributed
                r = _history(asset_root, dist, asset)
                for h in (r['history'] if r else []):
                    if h['year'] not in years:
                        continue
                    f = Path(asset_root) / str(dist) / asset / str(h['year']) / 'territorial.parquet'
                    col = 'UNIT' if kind == 'municipality' else 'CONJ'
                    if kind == 'conjunto' and asset.startswith('trafo') and 'CONJ' not in {c[0] for c in db.execute('DESCRIBE SELECT * FROM read_parquet(?)', [str(f)]).fetchall()}:
                        continue
                    for unit, v in db.execute(f'SELECT {col},sum({measure}) FROM read_parquet(?) GROUP BY 1', [str(f)]).fetchall():
                        if not check(unit):
                            continue
                        cell = out.setdefault((dist, h['year'], unit), dict(values={}, avail={}))
                        cell['values'][family] = float(v)
                        cell['avail'][family] = h['available']
    finally:
        db.close()
    for cell in out.values():
        v = cell['values']
        c, n, k = v.get('ucbt_clients'), v.get('trafo_count'), v.get('trafo_kva')
        v['clients_per_trafo'] = c / n if c and n and c > 0 and n > 0 else None
        v['kva_per_client'] = k / c if c and k and c > 0 and k > 0 else None
        cell['avail']['ratio'] = max([cell['avail'][f] for f in ('ucbt', 'trafo_count', 'trafo_kva') if f in cell['avail']] or [None]) if cell['avail'] else None
    return out


def _log(x):
    return math.log1p(x) if x is not None and math.isfinite(x) and x > -1 else None


def attach(rows, matrix, asset):
    """Fill the cross-family features of each panel row from the matrix values at t-1. Own-lag duplicates are skipped.
    The availability of each feature is the availability of the publication(s) it comes from (gate for point-in-time)."""
    if asset not in USES_CROSS:
        return rows
    from .features import FEATURES as F
    index = {n: F.index(n) for n in CROSS}
    out = []
    for r in rows:
        r = dict(r, x=list(r['x']) + [None] * (len(F) - len(r['x'])), feature_meta=dict(r.get('feature_meta', {})))
        m = matrix.get((r['dist'], r['feature_year'], r['group']))
        if m:
            v, a = m['values'], m['avail']
            plan = {'urban_share': (v.get('ucbt_urban_share'), ('ucbt',)),
                    'log_energy_per_client': (_log(v.get('ucbt_energy_per_client')), ('ucbt',)),
                    'log_ucbt_clients': (_log(v.get('ucbt_clients')), ('ucbt',)),
                    'log_trafo_count': (_log(v.get('trafo_count')), ('trafo_count',)),
                    'log_trafo_kva': (_log(v.get('trafo_kva')), ('trafo_kva',)),
                    'log_clients_per_trafo': (_log(v.get('clients_per_trafo')), ('ucbt', 'trafo_count')),
                    'log_kva_per_client': (_log(v.get('kva_per_client')), ('ucbt', 'trafo_kva'))}
            for name, (value, fams) in plan.items():
                if SELF.get(asset) == name or value is None or any(f not in a for f in fams):
                    continue
                r['x'][index[name]] = value
                r['feature_meta'][name] = dict(reference_year=r['feature_year'], available=max(a[f] for f in fams), released=None,
                                               source='shared matrix (' + '+'.join(fams) + ')', cross_family=True)
        out.append(r)
    return out


def write(matrix, path, kind):
    cols = ['ucbt_clients', 'ucbt_urban_share', 'ucbt_energy_per_client', 'trafo_count', 'trafo_kva', 'mt_km', 'clients_per_trafo', 'kva_per_client']
    fams = ['ucbt', 'trafo_count', 'trafo_kva', 'mt_km']
    with Path(path).open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['DIST', 'ano', 'unit_kind', 'unit'] + cols + [f'available_{x}' for x in fams])
        for (d, y, u), c in sorted(matrix.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2])):
            w.writerow([d, y, kind, u] + [c['values'].get(k) for k in cols] + [c['avail'].get(x) for x in fams])


def coverage(matrix):
    """Share of (dist, year) units holding each value; exposes families that exist for only part of the territory."""
    cols = ['ucbt_clients', 'ucbt_urban_share', 'ucbt_energy_per_client', 'trafo_count', 'trafo_kva', 'mt_km', 'clients_per_trafo', 'kva_per_client']
    n = len(matrix)
    return {c: (sum(1 for m in matrix.values() if m['values'].get(c) is not None) / n if n else None) for c in cols}
