"""Asset registry and annual extractors for the generalized executor (Parquets only; no ZIP/GDB, no download).

trafo_dist_*  : EQTRMT/EQTRAT with TUC=565 linked bijectively to UNTRMT/UNTRAT (EQ.UNI_TR_*=UN.COD_ID). The
                territorial unit is UN.MUN. Equipment without a unique 1:1 UN link is counted in the audit total but never
                assigned to a municipality. EQ and UN are never added together. Power: UNTRMT kVA, UNTRAT MVA x 1000;
                EQ.POT_NOM is a domain code and A4 is a patrimonial range, so neither is used as power.
rede_mt_extensao_km : SSDMT.COMP metres / 1000 by SSDMT.CONJ (a field of the segment itself; no spatial inference).
rede_bt_extensao_km : SSDBT.COMP metres / 1000 by SSDBT.CONJ (same rule as the national contract `rede_bt`).
Every extracted total is compared with the national contract cell of the same concept (`contract_value`); a difference is
recorded in the QA, never corrected.
"""
import argparse
import json
import sys
import time
import traceback
from pathlib import Path
import duckdb
import pyarrow.parquet as pq
from .adapters import path as parquet_path, source
from .runner import atomic, digest, fingerprint, lit, norm, read, resolve_sources

ASSET_VERSION = 'assets-3'
ASSETS = {
    'ucbt_quantidade': dict(ativo='ucbt', metrica='quantidade', unit='clientes', count=True, unit_kind='municipality',
                            concept='consumidores', metric='quantidade', experimental=False),
    'trafo_dist_quantidade': dict(ativo='trafo_dist', metrica='quantidade', unit='itens', count=True, unit_kind='municipality',
                                  concept='trafo_dist', metric='quantidade', tuc='565', measure='count', experimental=False),
    'trafo_dist_potencia_kva': dict(ativo='trafo_dist', metrica='potencia_kva', unit='kVA', count=False, unit_kind='municipality',
                                    concept='trafo_dist', metric='quantidade', tuc='565', measure='kva', experimental=True),
    'rede_mt_extensao_km': dict(ativo='rede_mt', metrica='extensao_km', unit='km', count=False, unit_kind='conjunto',
                                concept='rede_mt', metric='extensao_km', measure='km', experimental=False),
    'rede_bt_extensao_km': dict(ativo='rede_bt', metrica='extensao_km', unit='km', count=False, unit_kind='conjunto',
                                concept='rede_bt', metric='extensao_km', measure='km', entity='SSDBT', experimental=False),
}
from .metric_contract import nature_of
for _spec in ASSETS.values():
    _spec['nature'] = nature_of(_spec['unit'])   # unclassified units fail at import: no silent default

PAIRS = (('EQTRMT', 'UNTRMT', ('UNI_TR_MT', 'UN_TR_MT'), 1.0), ('EQTRAT', 'UNTRAT', ('UNI_TR_AT', 'UN_TR_AT'), 1000.0))
MIN_LINK_COVERAGE = 0.98   # engineering floor for publishing a power series, not a regulatory value


def extract_transformers(con, src, dest, tuc, measure):
    units, audit = {}, dict(eq_total=0, linked=0, unlinked=0, non_bijective=0, invalid_power=0, entities=[], tuc=tuc,
                            eq_duplicate_ids=0, eq_null_fk=0, eq_fk_not_in_un=0, un_shared_by_many_eq=0, un_duplicate_ids=0, un_rows=0, un_without_eq565=0)
    for eq, un, fks, factor in PAIRS:
        ec = source(con, src, eq, 'e0')
        if ec is None:
            continue
        uc = source(con, src, un, 'u0')
        fk = next((x for x in fks if x in ec), None)
        if not {'COD_ID', 'TUC'} <= ec:
            raise ValueError(eq + ' lacks COD_ID/TUC')
        total = con.execute(f"SELECT count(*) FROM e0 WHERE {norm('TUC')}={lit(tuc)}").fetchone()[0]
        audit['eq_total'] += total; audit['entities'].append(eq)
        if not total:
            continue
        if uc is None or not fk or not {'COD_ID', 'POT_NOM', 'MUN'} <= uc:
            audit['unlinked'] += total
            continue
        # Key uniqueness and orphan audit (EQ/UN are never added: they describe the same physical transformer)
        dup_eq, null_fk, not_in_un, shared = con.execute(f"""SELECT
            count(*) - count(DISTINCT {norm('COD_ID')}), count(*) FILTER(WHERE {norm(fk)} IS NULL),
            count(*) FILTER(WHERE {norm(fk)} IS NOT NULL AND {norm(fk)} NOT IN (SELECT {norm('COD_ID')} FROM u0 WHERE {norm('COD_ID')} IS NOT NULL)),
            count({norm(fk)}) - count(DISTINCT {norm(fk)})
            FROM e0 WHERE {norm('TUC')}={lit(tuc)}""").fetchone()
        un_rows, un_dup, un_orphan = con.execute(f"""SELECT count(*), count(*) - count(DISTINCT {norm('COD_ID')}),
            count(*) FILTER(WHERE {norm('COD_ID')} NOT IN (SELECT {norm(fk)} FROM e0 WHERE {norm('TUC')}={lit(tuc)} AND {norm(fk)} IS NOT NULL))
            FROM u0""").fetchone()
        for k, v in (('eq_duplicate_ids', dup_eq), ('eq_null_fk', null_fk), ('eq_fk_not_in_un', not_in_un), ('un_shared_by_many_eq', shared),
                     ('un_duplicate_ids', un_dup), ('un_rows', un_rows), ('un_without_eq565', un_orphan)):
            audit[k] += v
        conj_expr = norm('CONJ') if 'CONJ' in uc else 'NULL::VARCHAR'
        q = f"""WITH e AS (SELECT {norm('COD_ID')} id,{norm(fk)} fk,{norm('TUC')} tuc,
                   count(*) OVER(PARTITION BY {norm('COD_ID')}) ni,count(*) OVER(PARTITION BY {norm(fk)}) nf FROM e0),
                 u AS (SELECT {norm('COD_ID')} fk,{norm('MUN')} mun,{conj_expr} conj,try_cast(POT_NOM AS DOUBLE)*{factor} kva,
                   count(*) OVER(PARTITION BY {norm('COD_ID')}) nu FROM u0)
                 SELECT u.mun,u.conj,count(*),sum(CASE WHEN isfinite(kva) AND kva>0 THEN kva END),
                        count(*) FILTER(WHERE NOT (isfinite(kva) AND kva>0))
                 FROM e JOIN u USING(fk) WHERE tuc={lit(tuc)} AND ni=1 AND nf=1 AND nu=1 AND id IS NOT NULL GROUP BY 1,2"""
        linked = 0
        for mun, conj, n, kva, bad in con.execute(q).fetchall():
            cell = units.setdefault((mun or 'MISSING', conj or 'MISSING'), [0, 0.])
            cell[0] += n; cell[1] += kva or 0.
            linked += n; audit['invalid_power'] += bad
        audit['linked'] += linked
        audit['non_bijective'] += total - linked  # unlinked or non-unique link: not assigned to a municipality
    audit['unlinked'] = audit['eq_total'] - audit['linked']
    audit['coverage'] = audit['linked'] / audit['eq_total'] if audit['eq_total'] else None
    index = 0 if measure == 'count' else 1
    rows = [dict(UNIT=m, CONJ=c, value=float(v[index]), rows=v[0]) for (m, c), v in sorted(units.items())]
    _write(rows, dest)
    ok = audit['coverage'] is not None and (measure == 'count' or (audit['coverage'] >= MIN_LINK_COVERAGE and audit['invalid_power'] == 0))
    value = None
    if ok:
        value = float(audit['eq_total']) if measure == 'count' else sum(r['value'] for r in rows)
    return dict(value=value, coverage=audit['coverage'], territorial_conflicts=0, audit=audit,
                source=f'EQ TUC{tuc} linked to UN (bijective); unit=UN.MUN; ' + ('count' if measure == 'count' else 'kVA from UN.POT_NOM'))


def extract_network(con, src, dest, entity='SSDMT'):
    cols = source(con, src, entity, 'net')
    if not cols or not {'COD_ID', 'COMP', 'CONJ'} <= cols:
        raise ValueError(entity + ' COD_ID/COMP/CONJ missing')
    n, ids, missing, negative = con.execute("SELECT count(*),count(DISTINCT COD_ID),count(*) FILTER(WHERE try_cast(COMP AS DOUBLE) IS NULL),"
                                            "count(*) FILTER(WHERE try_cast(COMP AS DOUBLE)<0) FROM net").fetchone()
    q = f"SELECT coalesce({norm('CONJ')},'MISSING') UNIT,sum(try_cast(COMP AS DOUBLE))/1000 value,count(*) rows FROM net GROUP BY 1 ORDER BY 1"
    rows = [dict(UNIT=u, CONJ=u, value=float(v or 0.), rows=r) for u, v, r in con.execute(q).fetchall()]
    _write(rows, dest)
    total = sum(r['value'] for r in rows)
    clean = n == ids and not missing and not negative
    no_conj = next((r['value'] for r in rows if r['UNIT'] == 'MISSING'), 0.)
    return dict(value=total if clean else None, coverage=1 - no_conj / total if total else None, territorial_conflicts=0,
                audit=dict(rows=n, unique_ids=ids, missing_comp=missing, negative_comp=negative, km_without_conj=no_conj),
                source=f'{entity}.COMP metres / 1000; unit={entity}.CONJ')


def _write(rows, dest):
    import pyarrow as pa
    schema = pa.schema([('UNIT', pa.string()), ('CONJ', pa.string()), ('value', pa.float64()), ('rows', pa.int64())])
    pq.write_table(pa.Table.from_pylist(rows, schema=schema), Path(dest) / 'territorial.parquet', compression='zstd')


def inputs(spec, src):
    entities = [spec.get('entity', 'SSDMT')] if spec['measure'] == 'km' else [e for pair in PAIRS for e in pair[:2]] if 'tuc' in spec else []
    return [parquet_path(src, e) for e in entities if parquet_path(src, e).exists()]


def run_asset(cfg, dist, asset, root, stats):
    spec = ASSETS[asset]
    if asset == 'ucbt_quantidade':
        raise ValueError('UCBT is produced by the original executor; this runner covers the new assets')
    task = Path(root) / str(dist) / asset
    task.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute('SET memory_limit=' + lit(cfg['memory']) + ';SET threads=' + str(cfg['threads']))
    con.execute('SET temp_directory=' + lit(str(Path(root) / 'tmp')) + ';SET preserve_insertion_order=false')
    history = []
    try:
        for src in resolve_sources(dist, spec['concept'], spec['metric']):
            year = src.get('year')
            dest = task / str(year)
            dest.mkdir(exist_ok=True)
            cp = dest / 'checkpoint.json'
            try:
                if 'error' in src:
                    raise ValueError(src['error'])
                files = inputs(spec, src)
                if not files:
                    raise ValueError('required Parquet entities not found')
                signature = fingerprint([src, [digest(f) for f in files], spec, ASSET_VERSION])
                old = read(cp) if cp.exists() else {}
                out = dest / 'territorial.parquet'
                if old.get('signature') == signature and out.exists() and digest(out) == old.get('output_sha256'):
                    qa = old['qa']; stats['reused'] += 1
                else:
                    qa = extract_network(con, src, dest, spec.get('entity', 'SSDMT')) if spec['measure'] == 'km' else extract_transformers(con, src, dest, spec['tuc'], spec['measure'])
                    qa['parquet_sha256'] = digest(out)
                    atomic(cp, dict(signature=signature, qa=qa, output_sha256=qa['parquet_sha256']))
                    stats['executed'] += 1
                cv = src.get('contract_value') if spec['measure'] != 'kva' else None   # the contract has no kVA cell
                qa = dict(qa, contract_value=cv, difference_vs_contract=(qa['value'] - cv) if cv is not None and qa['value'] is not None else None)
                history.append(dict(year=year, available=src['available'], value=qa['value'], rupture=src['rupture'], qa=qa, source=src))
            except Exception as e:
                atomic(dest / 'failure.json', dict(error=str(e), traceback=traceback.format_exc()))
                history.append(dict(year=year, available=src.get('available'), value=None, rupture=src.get('rupture', False),
                                    qa=dict(value=None, coverage=None, territorial_conflicts=0, source='failed', error=str(e)), source=src))
        result = dict(dist=dist, asset=asset, metric=spec['metrica'], unit=spec['unit'], experimental=spec['experimental'], history=history)
        atomic(task / 'result.json', result)
        return result
    finally:
        con.close()


def execute(cfg):
    from .resources import Sampler, guard
    out = Path(cfg['output']).resolve()
    if out.drive.upper() != 'D:':
        raise ValueError('output must be on D:')
    guard(cfg.get('min_available_gb', 3.0))
    code = {p.name: digest(p) for p in Path(__file__).parent.glob('*.py')}
    runid = fingerprint([cfg, code])[:16]
    root = out / 'asset_runs' / runid
    root.mkdir(parents=True, exist_ok=True)
    stats = dict(reused=0, executed=0)
    failures, timings = [], {}
    with Sampler() as sampler:
        for dist in cfg['dists']:
            t = time.monotonic()
            for asset in cfg['assets']:
                try:
                    guard(cfg.get('min_available_gb', 3.0))
                    run_asset(cfg, dist, asset, root, stats)
                except Exception as e:      # one company/asset never stops the others; the failure is counted and kept
                    failures.append(dict(dist=dist, asset=asset, error=str(e)))
                    atomic(root / f'failure_{dist}_{asset}.json', dict(error=str(e), traceback=traceback.format_exc()))
            timings[str(dist)] = round(time.monotonic() - t, 1)
    atomic(root / 'manifest.json', dict(config=cfg, code=code, version=ASSET_VERSION, runid=runid, stats=stats, failures=failures,
                                        seconds_by_dist=timings, resources=sampler.report()))
    return root


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--config', required=True)
    print(execute(read(ap.parse_args().config)))
