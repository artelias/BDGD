"""Immutable official-source snapshots. Observed vintages are never backdated."""
import argparse
import datetime as dt
import gzip
import json
import math
from pathlib import Path
import shutil
import urllib.request
import pyarrow as pa
import pyarrow.parquet as pq
from .runner import read, atomic, digest, fingerprint
from .features import FEATURES


def decode(b):
    return json.loads(gzip.decompress(b) if b[:2]==b'\x1f\x8b' else b)


def finite(value):
    if value in (None,'','-','...','X','..'):return None
    try:
        x=float(str(value).replace(',','.'))
        return x if math.isfinite(x) else None
    except (TypeError,ValueError):return None


def ingest(config):
    cfg=read(config);root=Path(cfg['output']).resolve()
    if root.drive.upper()!='D:':raise ValueError('external output must be on D:')
    raw=root/'raw';raw.mkdir(parents=True,exist_ok=True)
    records=[];catalog=[]
    for spec in cfg['sources']:
        entry=dict(spec)
        if spec.get('status')=='unavailable':catalog.append(entry);continue
        try:
            origin=Path(spec['local']) if spec.get('local') else None
            request_cache=raw/(fingerprint(spec['url'])+'.download')
            if origin is None:
                if not request_cache.exists():
                    # Explicit refresh uses a new source version/config, never overwrites snapshots.
                    with urllib.request.urlopen(spec['url'],timeout=30) as response:
                        b=response.read(20_000_001)
                    if len(b)>20_000_000:raise ValueError('source exceeds bounded download budget')
                    request_cache.write_bytes(b)
                origin=request_cache
            sha=digest(origin)
            if spec.get('expected_sha256') and sha!=spec['expected_sha256']:raise ValueError('source hash mismatch')
            stored=raw/(sha+'.json')
            if not stored.exists():shutil.copyfile(origin,stored)
            data=decode(stored.read_bytes());items=data[1:] if spec['format']=='sidra' else data['result']['records']
            if spec['format']=='ckan' and data['result']['total']!=len(items):raise ValueError('CKAN result truncated; pagination required')
            count=0;rejected=0
            for r in items:
                if spec['format']=='sidra':
                    if r['NC']!='6' or r['D2C']!=spec['variable']:continue
                    geo=r['D1C'];year=int(r['D3C']);value=finite(r['V'])
                    if r['MC']!=spec['unit_code']:raise ValueError('unexpected SIDRA unit')
                else:
                    if r['SigIndicador']!=spec['indicator'] or int(r['NumPeriodoIndice'])!=spec['annual_period']:continue
                    geo=r['SigAgente']+':'+str(int(r['IdeConjUndConsumidoras']));year=int(r['AnoIndice']);value=finite(r['VlrIndiceEnviado'])
                if value is None or (value<0 and not spec.get('allow_negative')):rejected+=1;continue
                release=spec.get('release_by_year',{}).get(str(year),spec.get('released'))
                # A current download does not prove the bytes existed at the first release.
                available=max(x for x in [release,spec['observed_at']] if x)
                records.append(dict(feature=spec['feature'],geo=geo,year=year,value=value,unit=spec['unit'],granularity=spec['granularity'],
                                    released=release,available=available,observed_at=spec['observed_at'],vintage_verified=False,
                                    version=sha,source=spec['url'],sha256=sha,period_definition=spec['period_definition']))
                count+=1
            entry.update(status='integrated',rows=count,rejected_values=rejected,sha256=sha,raw=str(stored),vintage_verified=False)
        except Exception as e:entry.update(status='unavailable',error=str(e))
        catalog.append(entry)
    for dspec in cfg.get('derived',[]):
        # Derived only from two integrated observations of the same municipality; no interpolation, no migration inferred.
        (fa,ya),(fb,yb)=dspec['start'],dspec['end']
        a={r['geo']:r for r in records if r['feature']==fa and r['year']==ya};b={r['geo']:r for r in records if r['feature']==fb and r['year']==yb}
        n=0
        for geo in sorted(a.keys()&b.keys()):
            if a[geo]['value']<=0 or b[geo]['value']<=0:continue
            released=dspec.get('released');observed=max(a[geo]['observed_at'],b[geo]['observed_at'])
            records.append(dict(feature=dspec['feature'],geo=geo,year=yb,value=(b[geo]['value']/a[geo]['value'])**(1/(yb-ya))-1,unit=dspec['unit'],
                                granularity='municipality',released=released,available=max(released,observed),observed_at=observed,vintage_verified=False,
                                version=fingerprint([a[geo]['sha256'],b[geo]['sha256']]),source=a[geo]['source']+' + '+b[geo]['source'],
                                sha256=fingerprint([a[geo]['sha256'],b[geo]['sha256']]),period_definition=dspec['period_definition']))
            n+=1
        catalog.append(dict(feature=dspec['feature'],status='integrated',rows=n,derived_from=[fa,fb],vintage_verified=False))
    unique={}
    for r in records:
        key=(r['feature'],r['geo'],r['year'])
        if key in unique and unique[key]!=r:raise ValueError('conflicting external observations')
        unique[key]=r
    identity=fingerprint([catalog,list(unique.values())]);out=root/'versions'/identity[:16];out.mkdir(parents=True,exist_ok=True)
    target=out/'observations.parquet'
    if not target.exists() and unique:pq.write_table(pa.Table.from_pylist(list(unique.values())),target,compression='zstd')
    atomic(out/'manifest.json',dict(version=identity,sources=catalog,path=str(target),sha256=digest(target) if target.exists() else None,
                                   policy='municipal context only; no automatic concession population; no future interpolation or migration addition'))
    return out/'manifest.json'


def lookup(records,feature,geo,year):
    eligible=[r for r in records.get((feature,geo),[]) if r['year']<=year]
    return max(eligible,key=lambda r:(r['year'],r['available'])) if eligible else None


def feature_allowed(row,index,mode):
    if index<3:return True  # BDGD publication checks are performed by temporal.usable.
    meta=row.get('feature_meta',{}).get(FEATURES[index])
    if not meta or meta['reference_year']>=row['year']:return False
    if mode=='reconciled_retrospective':return True
    return bool(meta.get('available') and meta['available']<=f"{row['feature_year']}-12-31")


def attach(rows,manifest_path):
    manifest=read(manifest_path);path=Path(manifest['path'])
    if digest(path)!=manifest['sha256']:raise ValueError('external normalized hash mismatch')
    by={}
    for r in pq.read_table(path).to_pylist():by.setdefault((r['feature'],r['geo']),[]).append(r)
    out=[]
    for r in rows:
        r=dict(r,x=list(r['x'][:3]),feature_meta={})
        if r.get('unit_kind','municipality')!='municipality':
            r['x'].extend([None]*5);out.append(r);continue   # municipal covariates are undefined for other territorial units
        for feature,source_feature in [('log_population','population'),('population_growth_census','population_growth_census'),('log_gdp','gdp'),('dec','dec_municipal_context'),('fec','fec_municipal_context')]:
            z=lookup(by,source_feature,r['group'] if feature not in ('dec','fec') else str(r['dist'])+':'+r['group'],r['feature_year'])
            value=None
            if z:
                value=math.log1p(z['value']) if feature.startswith('log_') else z['value']
                r['feature_meta'][feature]=dict(reference_year=z['year'],available=z['available'],released=z['released'],sha256=z['sha256'],source=z['source'],unit=z['unit'],age_years=r['feature_year']-z['year'])
            r['x'].append(value)
        out.append(r)
    return out


def coverage_rows(rows,origins):
    from .temporal import usable
    result=[]
    for r in rows:
        for origin in origins:
            if r['year']>origin+1:continue
            role='train' if r['year']<=origin else 'test'
            for i,value in enumerate(r['x']):
                meta=r.get('feature_meta',{}).get(FEATURES[i],{})
                result.append(dict(DIST=r['dist'],ano=r['year'],MUN=r['group'],origin=origin,role=role,feature=FEATURES[i],value=value,
                                   available=meta.get('available',r['feature_available']),reference_year=meta.get('reference_year',r['feature_year']),
                                   point_in_time=value is not None and usable(r,origin,'point_in_time',role=='train') and feature_allowed(r,i,'point_in_time'),
                                   retrospective=value is not None and feature_allowed(r,i,'reconciled_retrospective'),reason='missing' if value is None else 'present; release and revision gates apply'))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True)
    print(ingest(parser.parse_args().config))
