"""Audited municipal features from existing territorial aggregates only."""
import csv
import math
from pathlib import Path
import duckdb
from .runner import read, digest, atomic, fingerprint

BASE_FEATURES = ('log_stock', 'urban_share', 'log_energy_per_client')
EXTERNAL_FEATURES = ('log_population', 'population_growth_census', 'log_gdp', 'dec', 'fec')
FEATURES = BASE_FEATURES + EXTERNAL_FEATURES


# Official TARE domain (BDGD DDA catalog M10 v1.1): UB=Urbano, NU=Nao Urbano, 0=Nao informado.
# NU is "not urban" (it is NOT labelled rural in the DDA); RU is not a TARE code and is never aliased.
AREA_DOMAIN = {'UB': 'urban', 'NU': 'nonurban', '0': 'unknown'}
URBAN_MIN_KNOWN_COVERAGE = 0.99  # engineering threshold, not a regulatory value; coverage is always reported.


def urban_share(areas):
    """Returns dict(share, known, unknown, coverage, reason).

    Coverage (known/total), unknown-domain customers and the urban share over known customers are
    separate quantities. Unknown codes (0, missing, undeclared such as RU) are never treated as NU."""
    total = sum(areas.values())
    known = sum(n for a, n in areas.items() if AREA_DOMAIN.get(a) in ('urban', 'nonurban'))
    unknown = total - known
    coverage = known / total if total else None
    if not total:
        return dict(share=None, known=0, unknown=0, coverage=None, reason='empty')
    if coverage < URBAN_MIN_KNOWN_COVERAGE:
        return dict(share=None, known=known, unknown=unknown, coverage=coverage, reason='unknown_area_codes_above_tolerance')
    return dict(share=areas.get('UB', 0) / known, known=known, unknown=unknown, coverage=coverage,
                reason='available' if not unknown else 'available_over_known_customers')


def snapshots(input_run, asset='ucbt_quantidade'):
    db = duckdb.connect()
    db.execute("SET memory_limit='512MB'; SET threads=1")
    data, metadata, provenance = {}, {}, {}
    try:
        for p in sorted(Path(input_run).glob(f'*/{asset}/result.json')):
            result = read(p); dist = int(result['dist']); provenance[str(p)] = digest(p)
            for h in result['history']:
                year = h['year']; f = p.parent / str(year) / 'territorial.parquet'
                sha = digest(f)
                if sha != read(f.parent/'checkpoint.json')['output_sha256']:
                    raise ValueError('aggregate hash mismatch: '+str(f))
                provenance[str(f)] = sha; metadata[dist, year] = h
                if asset != 'ucbt_quantidade':
                    # Generic asset aggregate: UNIT, value (count, kVA or km). No area/energy covariates exist for it.
                    for unit, value in db.execute('SELECT UNIT,sum(value) FROM read_parquet(?) GROUP BY ALL', [str(f)]).fetchall():
                        data[dist, year, unit] = dict(n=float(value), areas={}, energy_n=0, energy_sum=0., urban=None, area_known=0,
                                                      area_unknown=0, area_reason='not_applicable', energy=None)
                    continue
                query = '''SELECT MUN,upper(trim(ARE_LOC)),sum(clientes_ativos),
                           sum(energia_denominador),sum(energia_kwh)
                           FROM read_parquet(?) GROUP BY ALL'''
                for mun, area, n, en, energy in db.execute(query, [str(f)]).fetchall():
                    s = data.setdefault((dist, year, mun), dict(n=0, areas={}, energy_n=0, energy_sum=0.))
                    s['n'] += n; s['areas'][area or 'MISSING'] = s['areas'].get(area or 'MISSING', 0)+n
                    s['energy_n'] += en
                    if energy is not None: s['energy_sum'] += energy
        for s in (v for v in data.values() if v['areas']):
            u = urban_share(s['areas']); s['urban'], s['area_known'], s['area_unknown'], s['area_reason'] = u['share'], u['known'], u['unknown'], u['reason']
            s['energy'] = s['energy_sum']/s['n'] if s['n'] and s['energy_n']==s['n'] and s['energy_sum']>=0 else None
        return data, metadata, provenance
    finally:
        db.close()


def csv_write(path, rows):
    if not rows: return
    with Path(path).open('w', newline='', encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f, list(dict.fromkeys(k for r in rows for k in r)))
        writer.writeheader(); writer.writerows(rows)


def audit(input_run, output, municipality_catalog, prior_results=None):
    data, meta, provenance = snapshots(input_run)
    names = {str(r['id']):r['nome'] for r in read(municipality_catalog)}
    provenance[str(municipality_catalog)] = digest(municipality_catalog)
    out=Path(output)/fingerprint(provenance)[:16]; out.mkdir(parents=True,exist_ok=True)
    coverage, transitions, areas = [], [], []
    for (d,y,m),s in sorted(data.items(),key=lambda kv:str(kv[0])):
        for a,n in s['areas'].items(): areas.append(dict(DIST=d,ano=y,MUN=m,ARE_LOC=a,clientes=n,recognized=a in ('UB','NU'),domain=AREA_DOMAIN.get(a,'undeclared_code')))
        vals=[math.log1p(s['n']),s['urban'],math.log1p(s['energy']) if s['energy'] is not None else None]
        for name,v in zip(BASE_FEATURES,vals):
            reason=(s['area_reason'] if name=='urban_share' else 'available') if v is not None or name=='urban_share' else 'incomplete_or_invalid_energy'
            coverage.append(dict(DIST=d,ano=y,MUN=m,municipio=names.get(m),municipio_validado=m in names,feature=name,value=v,
                                 numerator=s['areas'].get('UB',0) if name=='urban_share' else s['energy_sum'] if name=='log_energy_per_client' else s['n'],
                                 denominator=s['n'],known_denominator=s['area_known'] if name=='urban_share' else s['energy_n'] if name=='log_energy_per_client' else s['n'],
                                 coverage=(s['area_known'] if name=='urban_share' else s['energy_n'] if name=='log_energy_per_client' else s['n'])/s['n'] if s['n'] else None,
                                 reason=reason,available=meta[d,y]['available']))
        if (d,y-1) in meta:
            prior=data.get((d,y-1,m))
            transitions.append(dict(DIST=d,ano=y,MUN=m,municipio=names.get(m),prior_stock=prior['n'] if prior else None,current_stock=s['n'],
                                    status='matched' if prior else 'absent_in_prior_snapshot_NOT_proven_entry'))
        if (d,y+1) in meta and (d,y+1,m) not in data:
            transitions.append(dict(DIST=d,ano=y+1,MUN=m,municipio=names.get(m),prior_stock=s['n'],current_stock=None,status='absent_in_current_snapshot_NOT_proven_exit'))
    historical=[]
    if prior_results:
        for summary in read(prior_results):
            if summary['mode']!='reconciled_retrospective':continue
            for c in summary['candidates']:
                for f in c['folds']:
                    for t in f['trials']:
                        historical.append(dict(DIST=summary['dist'],candidate=c['candidate'],origin=f['origin'],part=f['part'],
                                               features=str(t['features']),status=t['status'],mae=t['mae'],energy_trial=2 in t['features'],
                                               selected_energy='log_energy_per_client' in f['selected_features']))
    csv_write(out/'FEATURE_COVERAGE_MUNICIPAL.csv',coverage)
    csv_write(out/'AREA_CODES.csv',areas)
    csv_write(out/'MUNICIPAL_TRANSITIONS.csv',transitions)
    csv_write(out/'PRIOR_FEATURE_TRIALS.csv',historical)
    atomic(out/'manifest.json',dict(inputs=provenance,area_rule='TARE (DDA M10 v1.1): UB urban; NU not-urban (not proven rural); 0/missing/undeclared unknown; share over known customers if coverage>=%s'%URBAN_MIN_KNOWN_COVERAGE,
                                   training_population='municipal contextual covariates; not concession demographic exposure'))
    return out
