"""Selective re-run of Level B after the eligibility policy change (elegibilidade-v2): only the series whose inputs changed.

    python -m motor_v2.nacional.revisao_b

A series (DIST, concept) is AFFECTED when the signature of everything its computation reads differs between the legacy rule of
the first run (d4982e8) and the v2 policy: its own cells, the consumer and MV-network cells used as features, the test row and
the training / inner-validation / projection pools of every scope and origin (rows with their features and targets). Unaffected
series are deterministic functions of identical inputs, so their saved candidates, decisions and moderate paths are kept; the
scenario envelopes of ALL series are recomputed afterwards (the national cross-section of each concept changed).
The previous outputs stay in nacional/_v1_d4982e8; this module writes the merged outputs and a before/after record."""
import hashlib
import json
from collections import defaultdict

from . import ROOT_OUT
from . import distribuidora as B
from .relatorio import write_csv, write_parquet
from ..runner import atomic

V1 = ROOT_OUT / '_v1_d4982e8' / 'distribuidora'


def _h(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def _rows(pool_rows):
    return sorted((r['dist'], r['year'], r['stock'], r['y'], tuple(r['x'])) for r in pool_rows)


def signatures(regra):
    cells, meta = B.load(regra)
    grp, _ = B.groups()
    concepts = sorted(k for k in meta if isinstance(k, str))
    dists = sorted({d for d, _, _ in cells})
    rows = B.panel(cells, concepts, dists)
    by_c = defaultdict(list)
    for r in rows:
        by_c[r['concept']].append(r)
    out = {}
    for c in concepts:
        rc = by_c[c]
        for d in dists:
            own = [(y, (cells.get((d, cc, y)) or {}).get('value'), (cells.get((d, cc, y)) or {}).get('usable'), (cells.get((d, cc, y)) or {}).get('rupture'))
                   for cc in (c, 'consumidores', 'rede_mt') for y in range(2022, 2026)]
            parts = [own]
            for o in B.ORIGINS:
                if not B.comparable(cells, d, c, o + 1):
                    parts.append((o, None)); continue
                test = B.row(cells, d, c, o + 1)
                parts.append((o, test['stock'], test['y'], test['x'], B.segment(cells, d, c, o)))
                for scope in B.SCOPES:
                    tr, why = B.pool(rc, c, d, o, scope, grp, test)
                    inner, _ = B.pool(rc, c, d, o - 1, scope, grp, test)
                    parts.append((scope, why, _rows(tr), _rows(inner)))
            anchor = max((y for y in range(2022, 2026) if (cells.get((d, c, y)) or {}).get('usable')), default=None)
            parts.append(('ancora', anchor))
            if anchor is not None:
                parts.append(B.segment(cells, d, c, anchor))
                try:
                    prow = dict(B.row(cells, d, c, anchor + 1), y=None)
                    for scope in B.SCOPES:
                        tr, why = B.pool(rc, c, d, anchor, scope, grp, prow)
                        inner, _ = B.pool(rc, c, d, anchor - 1, scope, grp, prow)
                        parts.append(('proj', scope, why, _rows(tr), _rows(inner), prow['x']))
                except (KeyError, TypeError) as e:
                    parts.append(('proj_erro', str(e)))
            out[d, c] = _h(parts)
    return out


def run(old_rule='legado', base=V1, record='REVISAO_ELEGIBILIDADE_B.json', label='elegibilidade-v2: recalculo seletivo'):
    """old_rule/base: the rule and the saved outputs the merge starts from (first run by default; 'v2_sem_sucessao' with a snapshot of
    the first revision for the succession rule)."""
    old, new = signatures(old_rule), signatures('v2')
    affected = {k for k in new if old.get(k) != new[k]}
    res = B.run(only=affected)
    keep = lambda r: (int(r['DIST']), r['conceito']) not in affected
    import csv
    import pyarrow.parquet as pq
    results = [r for r in csv.DictReader(open(base / 'RESULTADOS_CANDIDATOS_B.csv', encoding='utf-8')) if keep(r)] + res['results']
    decisions = [r for r in csv.DictReader(open(base / 'DECISOES_B.csv', encoding='utf-8')) if keep(r)] + res['decisions']
    projections = [r for r in pq.read_table(base / 'PROJECOES_B_INTERNO.parquet').to_pylist() if keep(r)] + res['projections']
    unavailable = [r for r in csv.DictReader(open(base / 'INDISPONIVEIS_B.csv', encoding='utf-8')) if keep(r)] + res['unavailable']
    order = lambda r: (r['conceito'], int(r['DIST']))
    B.write(dict(results=sorted(results, key=order), decisions=sorted(decisions, key=order),
                 projections=sorted(projections, key=lambda r: (r['conceito'], int(r['DIST']), r['cenario'], int(r['ano']))),
                 unavailable=sorted(unavailable, key=order),
                 provenance=dict(res['provenance'], revisao=label, series_recalculadas=len(affected),
                                 series_mantidas_da_base=len(new) - len(affected), base=str(base))))
    env = B.reenvelope()
    rec = dict(regra=label, regra_anterior=old_rule, base=str(base), series_total=len(new), series_afetadas=len(affected),
               afetadas_por_dist=dict(sorted(((str(d), n) for d, n in _count(affected).items()), key=lambda x: -x[1])),
               reenvelope=env, segundos_recalculo=res['provenance']['segundos'],
               candidatos_recalculados=len(res['results']))
    atomic(ROOT_OUT / 'distribuidora' / record, dict(rec, afetadas=sorted(f'{d}/{c}' for d, c in affected)))
    return rec


def _count(keys):
    n = defaultdict(int)
    for d, _ in keys:
        n[d] += 1
    return n


if __name__ == '__main__':
    import sys
    if '--sucessao' in sys.argv:
        import shutil
        snap = ROOT_OUT / '_v2a_pre_sucessao' / 'distribuidora'
        if not snap.exists():
            shutil.copytree(ROOT_OUT / 'distribuidora', snap)
        r = run('v2_sem_sucessao', snap, 'REVISAO_SUCESSAO_B.json', 'sucessao societaria nao comparavel: recalculo seletivo')
    else:
        r = run()
    print(json.dumps(r, ensure_ascii=False, indent=1, default=str)[:4000])
