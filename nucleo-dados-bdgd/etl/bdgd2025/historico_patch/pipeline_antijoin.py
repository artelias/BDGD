"""Historical adaptation of Claude's verified stages, bounded Arrow + DuckDB.

Reuses download/checksum, BASE gate, entity totals, independent reconciliation
and scoped relationship semantics. Does not import or execute the 2025 scripts.
Rev5 domain matches are diagnostics, never historical homologation.
"""
import collections
import datetime as dt
import json
import os
import re
import shutil
import time
import urllib.request
import zipfile
from pathlib import Path

import duckdb
import pyarrow.parquet as pq
import pyogrio
from common import atomic_json, check_year, csv_write, now, sha

METRIC_VERSION = 'historico-v1-catalogo-nao-homologado'
EXT = {'SSDAT', 'SSDMT', 'SSDBT', 'RAMLIG'}
POT = {'EQTRMT', 'EQTRAT', 'EQRE', 'UNTRMT', 'UNTRAT'}
FACT_FIELDS = 'dist,ano,data_base,entidade,metrica,valor,unidade,metric_version,status_qualidade,motivo_qualidade,comparavel_2025'.split(',')

def qi(name):
    return '"' + name.replace('"', '""') + '"'

def qs(value):
    return "'" + str(value).replace("'", "''") + "'"

def normalize_date(value):
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()[:10]
    value = str(value or '').strip()
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%Y/%m/%d', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'):
        try:
            return dt.datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    return None

def validate_base(records, row):
    check_year(row['ano'])
    if len(records) != 1:
        raise ValueError('BASE must contain exactly one row')
    base = records[0]
    if normalize_date(base.get('DAT_FNL')) != row['data_base']:
        raise ValueError('BASE.DAT_FNL differs from requested competence')
    if str(base.get('DIST')).strip() != str(row['dist']):
        raise ValueError('BASE.DIST differs from inventory')

def download(row, folder):
    check_year(row['ano'])
    if row['data_base'] != f"{row['ano']}-12-31":
        raise ValueError('Invalid requested date')
    expected_url = 'https://www.arcgis.com/sharing/rest/content/items/' + row['item_id'] + '/data'
    if row['url_download'] != expected_url or not re.fullmatch('[0-9a-f]{32}', row['item_id']):
        raise ValueError('Download must come from inventoried ArcGIS item endpoint')
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / (row['item_id'] + '.zip')
    meta_path = folder / 'download.json'
    if meta_path.exists() and dest.exists():
        m = json.loads(meta_path.read_text(encoding='utf-8'))
        if m.get('zip_integro') and dest.stat().st_size == m['bytes'] and sha(dest) == m['sha256']:
            return dest, m
    part = dest.with_suffix('.zip.part')
    total = int(row['tamanho_bytes'])
    for attempt in range(6):
        have = part.stat().st_size if part.exists() else 0
        if have == total:
            break
        if have > total:
            raise ValueError('Partial download exceeds expected size')
        try:
            req = urllib.request.Request(expected_url, headers={'Range': f'bytes={have}-', 'Accept-Encoding': 'identity'})
            with urllib.request.urlopen(req, timeout=120) as response:
                if response.status == 206 and not response.headers.get('Content-Range', '').startswith(f'bytes {have}-'):
                    raise ValueError('Invalid Content-Range; cannot append safely')
                with part.open('ab' if response.status == 206 else 'wb') as f:
                    while chunk := response.read(1024 * 1024):
                        f.write(chunk)
        except (OSError, TimeoutError):
            if attempt == 5:
                raise
            time.sleep(min(30, 2 ** attempt))
    if not part.exists() or part.stat().st_size != total:
        raise ValueError('Incomplete download')
    with zipfile.ZipFile(part) as archive:
        if archive.testzip() is not None:
            bad = part.with_suffix('.corrupt')
            os.replace(part, bad)
            raise ValueError('Corrupt ZIP retained for investigation')
    digest = sha(part)
    os.replace(part, dest)
    meta = dict(item_id=row['item_id'], sha256=digest, bytes=total, zip_integro=True, fetched_at=now(), url=expected_url)
    atomic_json(meta_path, meta)
    return dest, meta

def inspect_gdb(archive, row):
    with zipfile.ZipFile(archive) as z:
        roots = set()
        for name in z.namelist():
            if '\\' in name or '..' in Path(name).parts or name.startswith('/'):
                raise ValueError('Unsafe archive member')
            for i, segment in enumerate(name.split('/')):
                if segment.lower().endswith('.gdb'):
                    roots.add('/'.join(name.split('/')[:i+1]))
    if len(roots) != 1:
        raise ValueError('Expected exactly one GDB')
    src = f'/vsizip/{archive.as_posix()}/{next(iter(roots))}'
    layers = {}
    for name, geom in pyogrio.list_layers(src):
        ent = name.removesuffix('_tab')
        if ent in layers:
            raise ValueError('Entity normalization collision')
        info = pyogrio.read_info(src, layer=name, force_feature_count=True)
        layers[ent] = dict(layer=name, count=int(info['features']), fields=list(info['fields']), types=list(map(str, info['dtypes'])), crs=info['crs'], geometry=geom)
    if 'BASE' not in layers:
        raise ValueError('BASE missing')
    if layers['BASE']['count'] != 1:
        raise ValueError('BASE must have one record')
    base = pyogrio.read_arrow(src, layer=layers['BASE']['layer'], read_geometry=False)[1].to_pylist()
    validate_base(base, row)
    return dict(src=src, BASE=base, layers=layers)

def connect(folder, memory_mb):
    folder.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET memory_limit='{int(memory_mb)}MB'")
    con.execute('SET threads=1')
    con.execute('SET preserve_insertion_order=false')
    con.execute(f'SET temp_directory={qs(folder.as_posix())}')
    con.execute("SET max_temp_directory_size='80GB'")
    return con

def convert(src, layer, destination, expected, source_sha):
    marker = destination.with_suffix('.ok.json')
    if marker.exists() and destination.exists():
        rec = json.loads(marker.read_text(encoding='utf-8'))
        if rec['source_sha'] == source_sha and rec['rows'] == expected and pq.ParquetFile(destination).metadata.num_rows == expected and sha(destination) == rec['sha256']:
            return rec
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix('.partial.parquet')
    n = 0
    with pyogrio.open_arrow(src, layer=layer, read_geometry=False, use_pyarrow=True, batch_size=16384) as (_, reader):
        with pq.ParquetWriter(partial, reader.schema, compression='zstd') as writer:
            for batch in reader:
                writer.write_batch(batch)
                n += batch.num_rows
    if n != expected:
        raise ValueError(f'GDB-Parquet row mismatch: {layer}')
    os.replace(partial, destination)
    rec = dict(rows=n, source_sha=source_sha, sha256=sha(destination), attributes_only=True)
    atomic_json(marker, rec)
    return rec

def validate_records(con, view, fields, row):
    if 'DIST' not in fields:
        raise ValueError('Entity without DIST: cannot establish scope')
    bad = con.execute(f'SELECT count(*) FROM {view} WHERE trim(CAST(DIST AS VARCHAR)) IS DISTINCT FROM ?', [str(row['dist'])]).fetchall()[0][0]
    if bad:
        raise ValueError(f'{bad} records with incorrect/null DIST')
    if 'DATA_BASE' not in fields:
        return 'competencia_via_BASE_sem_DATA_BASE_na_entidade'
    # Group only the temporal field: a bounded set in legitimate yearly sources.
    values = con.execute(f'SELECT DISTINCT CAST(DATA_BASE AS VARCHAR) FROM {view} LIMIT 32').fetchall()
    if len(values) == 32 or any(normalize_date(v[0]) != row['data_base'] for v in values):
        raise ValueError('Incorrect/null DATA_BASE in entity records')
    return 'BASE_e_DATA_BASE_validadas'

def numeric_stats(con, view, column):
    v = f'TRY_CAST({qi(column)} AS DOUBLE)'
    return con.execute(f'SELECT sum({v}) FILTER(WHERE isfinite({v})), count(*) FILTER(WHERE {v} IS NULL OR NOT isfinite({v})), count(*) FILTER(WHERE {v} <= 0) FROM {view}').fetchall()[0]

def aggregate_entity(con, view, fields):
    expr = 'count(*), count(COD_ID), count(DISTINCT COD_ID)' if 'COD_ID' in fields else 'count(*), NULL, NULL'
    return con.execute(f'SELECT {expr} FROM {view}').fetchall()[0]

def process(row, root, memory_mb=384):
    year = check_year(row['ano'])
    key = Path(str(year)) / str(row['dist']) / row['item_id']
    out = root / 'proc' / key
    out.mkdir(parents=True, exist_ok=True)
    archive, dl = download(row, root / 'raw' / key)
    ins = inspect_gdb(archive, row)
    atomic_json(out / 'inspection.json', ins)
    con = connect(root / 'tmp_duckdb' / key, memory_mb)
    facts, recon, alerts, schema, links, diagnostics = [], [], [], [], [], []
    views, info = {}, {}
    def reconcile(ent, metric, source, aggregated, tolerance=0):
        status = 'ok' if source is not None and aggregated is not None and abs(source-aggregated) <= tolerance else 'falha'
        recon.append(dict(dist=row['dist'], ano=year, entidade=ent, metrica=metric, valor_origem=source, valor_agregado=aggregated, diferenca=None if source is None or aggregated is None else aggregated-source, tolerancia=tolerance, status=status))
        if status != 'ok':
            raise ValueError(f'Reconciliation failed: {ent}/{metric}')
    try:
        for ent, layer in ins['layers'].items():
            if ent == 'BASE':
                continue
            dest = root / 'parquet' / key / f'{ent}.parquet'
            convert(ins['src'], layer['layer'], dest, layer['count'], dl['sha256'])
            view = qi('e_' + ent)
            con.execute(f'CREATE VIEW {view} AS SELECT * FROM read_parquet({qs(dest.as_posix())}, hive_partitioning=false)')
            views[ent] = view
            fields = layer['fields']
            date_status = validate_records(con, view, fields, row)
            n, nn, nd = aggregate_entity(con, view, fields)
            info[ent] = dict(n=n, nn=nn, nd=nd, fields=fields)
            reconcile(ent, 'gdb_parquet_registros', layer['count'], n)
            # A second, independent GDB stream checks counts/distincts (no in-memory ID set).
            selected = [x for x in ['COD_ID', 'DIST', 'COMP', 'POT_NOM'] if x in fields]
            with pyogrio.open_arrow(ins['src'], layer=layer['layer'], columns=selected, read_geometry=False, use_pyarrow=True, batch_size=16384) as (_, reader):
                con.register('source_stream', reader)
                src_n, src_nn, src_nd = aggregate_entity(con, 'source_stream', fields)
                con.unregister('source_stream')
            reconcile(ent, 'quantidade_registros', src_n, n)
            if nd is not None:
                reconcile(ent, 'quantidade_cod_id_distinto', src_nd, nd)
            reason = []
            if nn is not None and nn < n:
                reason.append(f'COD_ID_nulos={n-nn}')
            if nd is not None and nd < nn:
                reason.append(f'COD_ID_repetidos={nn-nd}; registros preservados')
            if date_status.startswith('competencia_via'):
                reason.append(date_status)
            for r in reason:
                alerts.append(dict(dist=row['dist'], ano=year, entidade=ent, tipo='chave_ou_data', detalhe=r))
            base = dict(dist=row['dist'], ano=year, data_base=row['data_base'], entidade=ent, metric_version=METRIC_VERSION, comparavel_2025='parcial')
            for metric, value, unit in [('quantidade_registros', n, 'registros'), ('quantidade_cod_id_distinto', nd, 'COD_ID distintos')]:
                facts.append(dict(base, metrica=metric, valor=value, unidade=unit, status_qualidade=('nao_aplicavel' if value is None else 'alerta' if reason else 'aprovado'), motivo_qualidade='; '.join(reason) if value is not None else 'campo COD_ID ausente'))
            facts.append(dict(base, metrica='quantidade', valor=None, unidade='unidades', status_qualidade='em_validacao', motivo_qualidade='Regra de ativo fisico/UC ainda nao homologada para layout historico', comparavel_2025='nao'))
            for metric, column, unit, applies, factor in [('extensao_km','COMP','km',ent in EXT,0.001), ('potencia_kva','POT_NOM','kVA',ent in POT,1)]:
                if applies and column in fields:
                    total, nulls, nonpositive = numeric_stats(con, view, column)
                    diagnostics.append(dict(dist=row['dist'], ano=year, entidade=ent, campo=column, soma_original=total, nulos_ou_invalidos=nulls, nao_positivos=nonpositive, status='unidade_historica_nao_homologada'))
                    with pyogrio.open_arrow(ins['src'], layer=layer['layer'], columns=[column], read_geometry=False, use_pyarrow=True, batch_size=16384) as (_, reader):
                        con.register('source_stream', reader)
                        original = numeric_stats(con, 'source_stream', column)
                        con.unregister('source_stream')
                    if total is not None:
                        reconcile(ent, f'{column}_soma_original', original[0], total, max(1e-5, abs(total)*1e-9))
                    reconcile(ent, f'{column}_invalidos', original[1], nulls)
                facts.append(dict(base, metrica=metric, valor=None, unidade=unit, status_qualidade='em_validacao' if applies else 'nao_aplicavel', motivo_qualidade='Unidade/DDA historico pendente; soma original auditada separadamente' if applies else 'Metrica nao aplicavel; UG/SIGFI nao convertidos para kVA', comparavel_2025='nao'))
            for field, dtype in zip(fields, layer['types']):
                schema.append(dict(dist=row['dist'], ano=year, entidade=ent, campo=field, tipo=dtype, crs=layer['crs'], layout_versao=row['layout_versao']))
            print(f"{year}/{row['dist']} {ent}: {n} registros", flush=True)
        # Links are existence checks against deduplicated alternative targets, not fan-out joins.
        relation_file = root / 'knowledge' / 'BDGD_RELATIONSHIPS_AND_DDA_REFS_REV5.json'
        rel = json.loads(relation_file.read_text(encoding='utf-8'))
        grouped = collections.defaultdict(list)
        for link in rel['entity_links']:
            grouped[(link['source_entity'], link['source_field'])].append((link['target_entity'], link['target_field']))
        for (ent, field), targets in grouped.items():
            if ent not in info or field not in info[ent]['fields']:
                continue
            available = [(e, f) for e, f in targets if e in info and f in info[e]['fields']]
            rr = dict(dist=row['dist'], ano=year, entidade=ent, campo=field, destinos='|'.join(e+'.'+f for e,f in targets), homologacao='referencia_Rev5_nao_homologada_historicamente')
            if not available:
                links.append(dict(rr, status='destino_ausente', preenchidos=None, orfaos=None, duplicados_destino=None))
                continue
            union = ' UNION '.join(f'SELECT trim(CAST({qi(f)} AS VARCHAR)) k FROM {views[e]}' for e,f in available)
            # anti-join por LEFT JOIN contra chaves distintas: mesmo resultado do NOT IN (destinos sem NULL), mas o
            # DISTINCT e o hash join podem usar disco; o NOT IN (mark join) estourava 768 MB em Enel SP e Light
            query = (f"WITH t AS (SELECT DISTINCT k FROM ({union}) u WHERE k IS NOT NULL), s AS (SELECT trim(CAST({qi(field)} AS VARCHAR)) k FROM {views[ent]}) "
                     f"SELECT count(*), count(*) FILTER(WHERE t.k IS NULL) FROM s LEFT JOIN t ON s.k = t.k WHERE s.k IS NOT NULL AND s.k NOT IN ('','0')")
            filled, orphans = con.execute(query).fetchall()[0]
            duplicates = sum(con.execute(f'SELECT count({qi(f)})-count(DISTINCT {qi(f)}) FROM {views[e]}').fetchall()[0][0] for e,f in available)
            links.append(dict(rr, status='alerta' if orphans or duplicates else 'verificado_estruturalmente', preenchidos=filled, orfaos=orphans, duplicados_destino=duplicates))
        dda = json.loads((root/'knowledge'/'BDGD_DDA_CATALOG_M10.json').read_text(encoding='utf-8'))
        domains = {t['table']: {str(v['COD_ID']) for v in t['values']} for t in dda['tables']}
        dda_qa = []
        for ref in rel['dda_references']:
            ent, field, domain = ref['source_entity'], ref['source_field'], ref['dda_table']
            if ent not in info or field not in info[ent]['fields']:
                continue
            matched = None
            if domain in domains:
                codes = ','.join(qs(v) for v in sorted(domains[domain]))
                matched = con.execute(f'SELECT count(*) FROM {views[ent]} WHERE trim(CAST({qi(field)} AS VARCHAR)) IN ({codes})').fetchall()[0][0]
            dda_qa.append(dict(dist=row['dist'], ano=year, entidade=ent, campo=field, dominio=domain, registros=info[ent]['n'], casam_catalogo_atual=matched, status='nao_homologado_historicamente', motivo='Rev5/M10 atual nao comprova vigencia historica; facetas bloqueadas'))
        csv_write(out/'facts.csv', facts, FACT_FIELDS)
        csv_write(out/'reconciliation.csv', recon)
        csv_write(out/'relationships.csv', links)
        csv_write(out/'dda.csv', dda_qa)
        csv_write(out/'schema.csv', schema)
        csv_write(out/'original_metrics.csv', diagnostics, ['dist','ano','entidade','campo','soma_original','nulos_ou_invalidos','nao_positivos','status'])
        csv_write(out/'alerts.csv', alerts, ['dist','ano','entidade','tipo','detalhe'])
        summary = dict(dist=row['dist'], ano=year, item_id=row['item_id'], data_base=row['data_base'], source_sha256=dl['sha256'], url=row['url_download'], rows=sum(i['n'] for i in info.values()), entities=len(info), reconciliations=len(recon), reconciliation_failures=0, quality_status='processado_sem_homologacao_semantica', completed_at=now(), pipeline_sha256=sha(Path(__file__)), files={p.name:sha(p) for p in out.glob('*.csv')})
        atomic_json(out/'checkpoint.json', summary)
        return summary
    finally:
        con.close()
