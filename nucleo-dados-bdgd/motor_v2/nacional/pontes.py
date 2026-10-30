"""Experimental application of an audited municipal recoding bridge to the DERIVED national panel (never to the original base).

    python -m motor_v2.nacional.pontes --aplicar MUN_RECODE_5697_2023 --autorizacao "..."

Scope: the panel copies (nacional/painel/{DIST}/{asset}/{year}/territorial.parquet) of the bridged (DIST, year) whose territorial
column is a municipality code (UCBT.MUN; UN.MUN of the TUC 565 transformers, column UNIT). Conjunto-coded assets (MT/BT network)
are read unchanged. The extraction outputs, the staging Parquet and the national contract are not touched; the panel copies
before the change are kept byte for byte in nacional/painel/_originais_ponte/{id}/ with their SHA-256.

Gates (all must hold, otherwise nothing is written): one-to-one mapping with a unique candidate per published code; no collision
(a target code already present in the same file); every target in the official IBGE list; totals of every numeric column and the
row count preserved; every non-municipality column identical row by row; only rows whose code is in the mapping change; the
municipality set and the per-municipality customers after the change continuous with the adjacent competences (each target present
in both neighbouring years). The bridge stays EXPERIMENTAL (status APLICADA_EXPERIMENTAL_NAO_HOMOLOGADA) until a specific
homologation; the record carries the authorisation text, the gates and the hashes before/after."""
import argparse
import csv
import json
import shutil
import time
from pathlib import Path

import duckdb

from . import ROOT_OUT
from .painel import PANEL
from ..runner import atomic, digest, read

AUD = ROOT_OUT / 'auditoria'
COLUMN = {'ucbt_quantidade': 'MUN', 'trafo_dist_quantidade': 'UNIT', 'trafo_dist_potencia_kva': 'UNIT'}
RECORD = ROOT_OUT / 'pontes_experimentais.json'


def mapping(bid):
    with open(AUD / f'PONTE_{bid}_MAPEAMENTO.csv', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    return {r['codigo_publicado']: r['candidato_ibge'] for r in rows}, rows


def _mun_customers(con, dist, year):
    f = PANEL / str(dist) / 'ucbt_quantidade' / str(year) / 'territorial.parquet'
    return dict(con.execute('SELECT MUN, sum(clientes_ativos) FROM read_parquet(?) GROUP BY 1', [str(f)]).fetchall())


def check_and_write(bid, dist, year, mp, ref, dry=False):
    con = duckdb.connect(); con.execute("SET memory_limit='512MB'; SET threads=1")
    gates, files = {}, []
    targets = list(mp.values())
    gates['mapeamento_univoco'] = len(set(mp)) == len(mp) == len(set(targets)) and all(targets)
    gates['codigos_ibge_validos'] = all(t in ref for t in targets)
    adj = {y: _mun_customers(con, dist, y) for y in (year - 1, year + 1)}
    gates['alvos_presentes_nos_dois_anos_adjacentes'] = all(t in adj[year - 1] and t in adj[year + 1] for t in targets)
    for asset, col in COLUMN.items():
        src = PANEL / str(dist) / asset / str(year) / 'territorial.parquet'
        if not src.exists():
            continue
        cols = [c[0] for c in con.execute('DESCRIBE SELECT * FROM read_parquet(?)', [str(src)]).fetchall()]
        num = [c for c, t in con.execute('SELECT column_name, column_type FROM (DESCRIBE SELECT * FROM read_parquet(?))', [str(src)]).fetchall()
               if any(k in t for k in ('INT', 'DOUBLE', 'DECIMAL', 'FLOAT', 'BIGINT'))]
        con.execute('CREATE OR REPLACE TEMP TABLE m(cod VARCHAR, alvo VARCHAR)')
        con.executemany('INSERT INTO m VALUES (?, ?)', list(mp.items()))
        con.execute(f'CREATE OR REPLACE TEMP TABLE a AS SELECT row_number() OVER () rid, * FROM read_parquet(?)', [str(src)])
        others = [c for c in cols if c != col]
        sel = ', '.join(f'a."{c}"' if c != col else f'coalesce(m.alvo, a."{col}") AS "{col}"' for c in cols)
        con.execute(f'CREATE OR REPLACE TEMP TABLE b AS SELECT a.rid, {sel} FROM a LEFT JOIN m ON a."{col}" = m.cod ORDER BY a.rid')
        present = {r[0] for r in con.execute(f'SELECT DISTINCT "{col}" FROM a').fetchall()}
        coll = sorted(set(targets) & present)
        changed = con.execute(f'SELECT count(*) FROM a JOIN b USING (rid) WHERE a."{col}" IS DISTINCT FROM b."{col}"').fetchall()[0][0]
        changed_ok = con.execute(f'SELECT count(*) FROM a JOIN b USING (rid) WHERE a."{col}" IS DISTINCT FROM b."{col}" AND a."{col}" NOT IN (SELECT cod FROM m)').fetchall()[0][0] == 0
        expected = con.execute(f'SELECT count(*) FROM a WHERE "{col}" IN (SELECT cod FROM m)').fetchall()[0][0]
        same_other = con.execute('SELECT count(*) FROM a JOIN b USING (rid) WHERE ' + ' OR '.join(f'a."{c}" IS DISTINCT FROM b."{c}"' for c in others)).fetchall()[0][0] == 0
        tot_a = con.execute('SELECT count(*), ' + ', '.join(f'sum("{c}")' for c in num) + ' FROM a').fetchall()[0]
        tot_b = con.execute('SELECT count(*), ' + ', '.join(f'sum("{c}")' for c in num) + ' FROM b').fetchall()[0]
        dup = con.execute(f'SELECT count(*) FROM (SELECT {", ".join(chr(34) + c + chr(34) for c in cols if c not in num)}, count(*) n FROM b GROUP BY ALL HAVING n > 1)').fetchall()[0][0] \
            if len([c for c in cols if c not in num]) else 0
        outside = con.execute(f'SELECT count(*), coalesce(sum({"clientes_ativos" if asset == "ucbt_quantidade" else "value"}), 0) FROM b WHERE "{col}" NOT IN (SELECT unnest(?::VARCHAR[]))', [sorted(ref)]).fetchall()[0]
        if expected == 0:
            # no record carries a published (non-IBGE) code: the entity already uses official codes -> bridge not applicable, file untouched
            gates[asset] = dict(aplicavel=False, motivo='nenhum registro com codigo publicado da ponte; codigos ja oficiais neste arquivo',
                                linhas=tot_a[0], linhas_fora_ibge=outside[0], ok=True)
            continue
        g = dict(aplicavel=True, colisoes=len(coll), exemplos_colisao=coll[:5], linhas_alteradas=changed, linhas_esperadas=expected, apenas_codigos_mapeados=changed_ok,
                 demais_colunas_identicas=same_other, totais_preservados=tuple(tot_a) == tuple(tot_b), linhas=tot_a[0], chaves_duplicadas_apos=dup,
                 linhas_fora_ibge_apos=outside[0], valor_fora_ibge_apos=float(outside[1]))
        g['ok'] = not coll and changed == expected and changed_ok and same_other and g['totais_preservados'] and dup == 0
        gates[asset] = g
        files.append((asset, src, col, sel))
    # continuity after the change: municipality set and customers vs adjacent competences
    con.execute(f"CREATE OR REPLACE TEMP TABLE u AS SELECT coalesce(m.alvo, MUN) MUN, sum(clientes_ativos) n FROM read_parquet(?) a LEFT JOIN m ON a.MUN = m.cod GROUP BY 1",
                [str(PANEL / str(dist) / 'ucbt_quantidade' / str(year) / 'territorial.parquet')])
    after = dict(con.execute('SELECT MUN, n FROM u').fetchall())
    ib = lambda s: {k for k in s if k in ref}
    ratios = sorted(after[k] / adj[year - 1][k] for k in ib(after) & ib(adj[year - 1]) if adj[year - 1][k])
    gates['continuidade'] = dict(municipios_ibge_apos=len(ib(after)), municipios_ibge_ano_anterior=len(ib(adj[year - 1])), municipios_ibge_ano_seguinte=len(ib(adj[year + 1])),
                                 apenas_no_ano=sorted(ib(after) - ib(adj[year - 1]) - ib(adj[year + 1])),
                                 ausentes_no_ano=sorted((ib(adj[year - 1]) & ib(adj[year + 1])) - ib(after)),
                                 razao_clientes_vs_anterior_p01=ratios[int(.01 * (len(ratios) - 1))] if ratios else None,
                                 razao_clientes_vs_anterior_mediana=ratios[len(ratios) // 2] if ratios else None,
                                 razao_clientes_vs_anterior_p99=ratios[int(.99 * (len(ratios) - 1))] if ratios else None)
    c = gates['continuidade']
    c['ok'] = not c['apenas_no_ano'] and not c['ausentes_no_ano']
    # cross-entity evidence of the same publication: municipalities of the TUC 565 transformers (UN.MUN, official codes)
    tf = PANEL / str(dist) / 'trafo_dist_quantidade' / str(year) / 'territorial.parquet'
    if tf.exists():
        tm = {r[0] for r in con.execute('SELECT DISTINCT UNIT FROM read_parquet(?)', [str(tf)]).fetchall()}
        w = sum(n for k, n in after.items() if k in tm); tot = sum(after.values())
        gates['evidencia_cruzada_transformadores'] = dict(municipios_ucbt_apos=len(after), municipios_transformadores=len(ib(tm)),
                                                          ucbt_em_municipio_com_transformador=len(set(after) & tm),
                                                          clientes_em_municipio_com_transformador=w / tot if tot else None,
                                                          alvos_da_ponte_presentes_em_UN_MUN=sum(1 for t in targets if t in tm))
    ok = gates['mapeamento_univoco'] and gates['codigos_ibge_validos'] and gates['alvos_presentes_nos_dois_anos_adjacentes'] and c['ok'] \
        and all(gates[a]['ok'] for a, *_ in files)
    written = []
    if ok and not dry:
        keep = PANEL / '_originais_ponte' / bid
        for asset, src, col, sel in files:
            dst = keep / str(dist) / asset / str(year); dst.mkdir(parents=True, exist_ok=True)
            ck = read(src.parent / 'checkpoint.json')
            if ck.get('ponte_experimental'):
                raise ValueError(f'ponte ja aplicada em {src}')
            shutil.copyfile(src, dst / 'territorial.parquet'); shutil.copyfile(src.parent / 'checkpoint.json', dst / 'checkpoint.json')
            before = digest(src)
            tmp = src.with_suffix('.ponte.parquet')
            con.execute(f'CREATE OR REPLACE TEMP TABLE a AS SELECT row_number() OVER () rid, * FROM read_parquet(?)', [str(src)])
            cols = [x[0] for x in con.execute('DESCRIBE SELECT * FROM read_parquet(?)', [str(src)]).fetchall()]
            con.execute(f"COPY (SELECT {', '.join(chr(34) + x + chr(34) for x in cols)} FROM (SELECT a.rid, {sel} FROM a LEFT JOIN m ON a.\"{col}\" = m.cod) ORDER BY rid) TO '{tmp.as_posix()}' (FORMAT PARQUET)")
            tmp.replace(src)
            after_sha = digest(src)
            atomic(src.parent / 'checkpoint.json', dict(ck, output_sha256=after_sha, output_sha256_original=before,
                                                        ponte_experimental=dict(id=bid, coluna=col, original=str(dst / 'territorial.parquet'))))
            written.append(dict(ativo=asset, arquivo=str(src), coluna=col, sha256_antes=before, sha256_depois=after_sha, original_preservado=str(dst)))
    con.close()
    return ok, gates, written


def apply(bid, authorisation, dry=False):
    prop = read(AUD / f'PONTE_{bid}_PROPOSTA.json')
    ref = set(json.loads((ROOT_OUT / 'referencias' / 'municipios_ibge.json').read_text(encoding='utf-8')))
    mp, rows = mapping(bid)
    ok, gates, written = check_and_write(bid, prop['dist'], prop['ano'], mp, ref, dry)
    rec = read(RECORD) if RECORD.exists() else dict(pontes=[])
    entry = dict(id=bid, dist=prop['dist'], ano=prop['ano'], status='APLICADA_EXPERIMENTAL_NAO_HOMOLOGADA' if ok and not dry else 'NAO_APLICADA',
                 camada='nacional/painel (derivada); base original, extracao e contrato intactos', autorizacao=authorisation,
                 data=time.strftime('%Y-%m-%dT%H:%M:%S'), proposta_sha256=digest(AUD / f'PONTE_{bid}_PROPOSTA.json'),
                 mapeamento_sha256=digest(AUD / f'PONTE_{bid}_MAPEAMENTO.csv'), codigos=len(mp), verificacoes=gates, arquivos=written,
                 homologacao='pendente de homologacao especifica; usada apenas na camada experimental do Motor V2')
    if not dry:
        rec['pontes'] = [p for p in rec['pontes'] if p['id'] != bid] + [entry]
        atomic(RECORD, rec)
        if ok:
            q = read(ROOT_OUT / 'quarentena.json')
            q['quarentena'] = [x for x in q['quarentena'] if (x[0], x[1]) != (prop['dist'], prop['ano'])]
            q['pontes_aplicadas_experimentais'] = sorted({*q.get('pontes_aplicadas_experimentais', []), bid})
            atomic(ROOT_OUT / 'quarentena.json', q)
    return entry


def reapply_after_build():
    """painel.build() copies the aggregates again; re-apply every bridge already recorded as applied (reproducibility)."""
    if not RECORD.exists():
        return []
    out = []
    for p in read(RECORD)['pontes']:
        if p['status'] == 'APLICADA_EXPERIMENTAL_NAO_HOMOLOGADA':
            out.append(apply(p['id'], p['autorizacao'])['status'])
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--aplicar', required=True); ap.add_argument('--autorizacao', required=True)
    ap.add_argument('--simular', action='store_true')
    print(json.dumps(apply(ap.parse_args().aplicar, ap.parse_args().autorizacao, ap.parse_args().simular), ensure_ascii=False, indent=1, default=str)[:6000])
