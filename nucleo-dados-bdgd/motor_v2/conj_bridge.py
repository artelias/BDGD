"""Evidence-based proposal for CONJ (consumer set) bridges between two consecutive publications. Parquets only.

Nothing is assumed. For each transition the module measures:
  * CTMT continuity: share of the year-y stock sitting in circuits (CTMT) that already existed at y-1. Circuit codes are the
    evidence carrier, so a low value makes any mapping `insufficient_evidence`.
  * Flow matrix old CONJ -> new CONJ through the circuits that exist in both years (SSDMT km, and UCBT customers as an independent
    second measure): how much of each new CONJ's stock comes from each old CONJ and vice versa.
  * Names and areas from the CONJ entity (NOME, Shape_Area) as supporting, never sufficient, evidence.
Classification of every new code: `one_to_one` (mutual flow >= 90% in km AND customers), `carved_from` (mostly from one old code that
persists), `merge`/`split` (several counterparts), `new_circuits` (stock in circuits absent at y-1), `insufficient_evidence`.
A persisting code whose composition changed (>= 5% of its km comes from another old code) is reported as `persisting_changed`.
The bridge is only a PROPOSAL: status PENDING_HOMOLOGATION, decision null; quarantine applies to new and changed codes.
Usage: python -m motor_v2.conj_bridge --ucbt-run <runs/..> --out <dir> [--bridges <dir>]"""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
import duckdb
from .adapters import path as parquet_path, source
from .runner import atomic, digest, norm, resolve_sources

STRONG = .90
CHANGED = .05
MIN_CTMT_CONTINUITY = .80
CASES = ((26, 2024), (6585, 2023), (6600, 2023), (6600, 2024))   # the transitions below the 95% continuity gate in the CONJ audit


def conj_year(con, src, ucbt_run, dist, year):
    """-> dict(ssd={(ctmt, conj): km}, ucbt={(ctmt, conj): clients}, entity={conj: (nome, area)})."""
    cols = source(con, src, 'SSDMT', 'net')
    if not cols or not {'CTMT', 'CONJ', 'COMP'} <= cols:
        raise ValueError('SSDMT CTMT/CONJ/COMP missing')
    ssd = {(c, j): float(v or 0) / 1000 for c, j, v in con.execute(
        f"SELECT {norm('CTMT')},{norm('CONJ')},sum(try_cast(COMP AS DOUBLE)) FROM net GROUP BY 1,2").fetchall() if j}
    f = Path(ucbt_run) / str(dist) / 'ucbt_quantidade' / str(year) / 'territorial.parquet'
    ucbt = {(c, j): float(v) for c, j, v in con.execute(
        "SELECT CTMT,CONJ,sum(clientes_ativos) FROM read_parquet(?) GROUP BY 1,2", [str(f)]).fetchall() if j} if f.exists() else {}
    entity = {}
    ec = source(con, src, 'CONJ', 'cj')
    if ec and {'COD_ID', 'NOME'} <= ec:
        area = 'Shape_Area' if 'Shape_Area' in ec else None
        for code, nome, a in con.execute(f"SELECT {norm('COD_ID')},{norm('NOME')},{('try_cast(Shape_Area AS DOUBLE)' if area else 'NULL::DOUBLE')} FROM cj").fetchall():
            entity[code] = (nome, a)
    return dict(ssd=ssd, ucbt=ucbt, entity=entity)


def flows(prev, cur):
    """Flow of stock from old CONJ to new CONJ through circuits present in both years. Returns dict(F, new_total, new_circuits, ctmt_continuity).
    F[(a, b)] = stock of new CONJ b attributed to old CONJ a (a circuit's old stock is split by its old CONJ shares)."""
    old_by_ctmt, new_by_ctmt = defaultdict(dict), defaultdict(dict)
    for (c, j), v in prev.items():
        old_by_ctmt[c][j] = old_by_ctmt[c].get(j, 0) + v
    for (c, j), v in cur.items():
        new_by_ctmt[c][j] = new_by_ctmt[c].get(j, 0) + v
    F, new_total, fresh = defaultdict(float), defaultdict(float), defaultdict(float)
    for c, news in new_by_ctmt.items():
        olds = old_by_ctmt.get(c)
        for b, v in news.items():
            new_total[b] += v
            if not olds:
                fresh[b] += v
                continue
            s = sum(olds.values())
            for a, w in olds.items():
                F[a, b] += v * (w / s) if s else 0.
    tot = sum(new_total.values())
    cont = (tot - sum(fresh.values())) / tot if tot else None
    return dict(F=dict(F), new_total=dict(new_total), fresh=dict(fresh), ctmt_continuity=cont)


def propose(dist, year, prev, cur, predecessor_names=None):
    """Bridge proposal for the transition (year-1 -> year) of one distributor."""
    fk, fu = flows(prev['ssd'], cur['ssd']), flows(prev['ucbt'], cur['ucbt']) if prev['ucbt'] and cur['ucbt'] else dict(F={}, new_total={}, fresh={}, ctmt_continuity=None)
    prev_codes = {j for (_, j) in prev['ssd']}; cur_codes = {j for (_, j) in cur['ssd']}
    names_prev = {c: n for c, (n, _) in prev['entity'].items()}; names_cur = {c: n for c, (n, _) in cur['entity'].items()}
    area_prev = {c: a for c, (_, a) in prev['entity'].items()}; area_cur = {c: a for c, (_, a) in cur['entity'].items()}
    total_new = sum(fk['new_total'].values())
    mapping, entering, changed = [], [], []
    ok_evidence = fk['ctmt_continuity'] is not None and fk['ctmt_continuity'] >= MIN_CTMT_CONTINUITY
    by_new_in = defaultdict(dict)
    for (a, b), v in fk['F'].items():
        by_new_in[b][a] = v
    out_total = defaultdict(float)
    for (a, b), v in fk['F'].items():
        out_total[a] += v
    for b in sorted(cur_codes):
        stock = fk['new_total'].get(b, 0.)
        into = by_new_in.get(b, {})
        fresh = fk['fresh'].get(b, 0.)
        top = max(into, key=into.get) if into else None
        in_share = into[top] / stock if top and stock else 0.
        out_share = into[top] / out_total[top] if top and out_total.get(top) else 0.
        cust = None
        if fu['new_total'].get(b):
            ci = {a: v for (a, bb), v in fu['F'].items() if bb == b}
            if ci:
                ct = max(ci, key=ci.get); cust = dict(top=ct, share=ci[ct] / fu['new_total'][b])
        name_eq = bool(top and names_prev.get(top) and names_prev.get(top) == names_cur.get(b))
        sources = {a: round(v / stock, 4) for a, v in sorted(into.items(), key=lambda kv: -kv[1]) if stock and v / stock >= .01}
        persists = b in prev_codes
        other_share = 1 - (into.get(b, 0) / stock) if stock else None
        if not ok_evidence:
            kind = 'insufficient_evidence'
        elif persists:
            kind = 'persisting_unchanged' if (other_share is not None and other_share < CHANGED and fresh / stock < CHANGED) else 'persisting_changed'
        elif stock and fresh / stock >= .5:
            kind = 'new_circuits'
        elif in_share >= STRONG and out_share >= STRONG and (cust is None or (cust['top'] == top and cust['share'] >= STRONG)):
            kind = 'one_to_one'
        elif in_share >= STRONG:
            kind = 'carved_from'
        elif len(sources) > 1:
            kind = 'merge'
        else:
            kind = 'insufficient_evidence'
        if not persists:
            entering.append(b)
        if kind == 'persisting_changed':
            changed.append(b)
        mapping.append(dict(new_code=b, kind=kind, name_new=names_cur.get(b), best_old_code=top, name_old=names_prev.get(top) if top else None, name_equal=name_eq,
                            km_new=round(stock, 3), share_from_best_old_km=round(in_share, 4), share_of_old_in_new=round(out_share, 4),
                            customers_best_old=cust, sources_km=sources, share_new_circuits=round(fresh / stock, 4) if stock else None,
                            area_ratio_new_over_old=(area_cur[b] / area_prev[top]) if top and area_prev.get(top) and area_cur.get(b) else None,
                            name_in_predecessor=bool(predecessor_names and names_cur.get(b) in predecessor_names)))
    gone = sorted(prev_codes - cur_codes)
    for a in gone:
        dest = {b: round(v / out_total[a], 4) for (aa, b), v in sorted(fk['F'].items(), key=lambda kv: -kv[1]) if aa == a and out_total.get(a) and v / out_total[a] >= .01}
        mapping.append(dict(old_code=a, kind='gone', name_old=names_prev.get(a), km_old=round(sum(v for (c, j), v in prev['ssd'].items() if j == a), 3),
                            destinations_km=dest, name_continues_as=sorted(b for b in cur_codes if names_cur.get(b) and names_cur.get(b) == names_prev.get(a))))
    strong = sum(fk['new_total'][m['new_code']] for m in mapping if 'new_code' in m and m['kind'] in ('one_to_one', 'persisting_unchanged'))
    partial = sum(fk['new_total'][m['new_code']] for m in mapping if 'new_code' in m and m['kind'] in ('carved_from', 'merge', 'persisting_changed', 'new_circuits'))
    coverage = dict(ctmt_continuity=fk['ctmt_continuity'], km_total_new=total_new, share_strong=strong / total_new if total_new else None,
                    share_partial=partial / total_new if total_new else None, share_insufficient=1 - (strong + partial) / total_new if total_new else None,
                    customers_ctmt_continuity=fu['ctmt_continuity'], codes_new=len(entering), codes_gone=len(gone), codes_changed=len(changed))
    return dict(id=f'CONJ_{dist}_{year}', version=1, kind='conjunto_redefinition', unit_kind='conjunto', successor_dist=dist, predecessor_dist=dist,
                effective_year=year, entering_units=sorted(entering), overlap_units=sorted(changed), status='PENDING_HOMOLOGATION', decision=None,
                evidence=dict(coverage=coverage, rule=dict(strong_flow=STRONG, changed_share=CHANGED, min_ctmt_continuity=MIN_CTMT_CONTINUITY,
                                                           evidence='SSDMT km and UCBT customers through shared CTMT codes; NOME and Shape_Area are supporting only')),
                mapping=mapping,
                policy='proposal only: no equivalence between old and new codes is assumed; new and changed codes are quarantined for the effective year; '
                       'a human decision is required before any comparable-perimeter series is built')


def main(ucbt_run, out, bridges_dir=None, cases=CASES):
    con = duckdb.connect(); con.execute("SET memory_limit='768MB'; SET threads=1")
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    results, rows = [], []
    try:
        for dist, year in cases:
            srcs = {s['year']: s for s in resolve_sources(dist, 'rede_mt', 'extensao_km') if 'error' not in s}
            prev = conj_year(con, srcs[year - 1], ucbt_run, dist, year - 1); cur = conj_year(con, srcs[year], ucbt_run, dist, year)
            pred_names = None
            if dist == 6600 and year == 2023:                                   # EBO (6611) 2022: names of its consumer sets, for the absorption hypothesis
                ebo = [s for s in resolve_sources(6611, 'rede_mt', 'extensao_km') if s.get('year') == 2022 and 'error' not in s]
                if ebo:
                    ec = source(con, ebo[0], 'CONJ', 'cj')
                    if ec and 'NOME' in ec:
                        pred_names = {r[0] for r in con.execute(f"SELECT {norm('NOME')} FROM cj").fetchall()}
            b = propose(dist, year, prev, cur, pred_names)
            b['evidence']['sources'] = {k: digest(parquet_path(srcs[y], 'SSDMT')) for k, y in (('ssdmt_prev', year - 1), ('ssdmt_cur', year))}
            results.append(b)
            for m in b['mapping']:
                rows.append(dict(DIST=dist, ano=year, **{k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in m.items()}))
            if bridges_dir:
                atomic(Path(bridges_dir) / f"{b['id']}.json", b)
    finally:
        con.close()
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with (out / 'CONJ_BRIDGE_EVIDENCE.csv').open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fields); w.writeheader(); w.writerows(rows)
    atomic(out / 'CONJ_BRIDGE_SUMMARY.json', [dict(id=b['id'], status=b['status'], entering=b['entering_units'], changed=b['overlap_units'], coverage=b['evidence']['coverage']) for b in results])
    return results


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--ucbt-run', required=True); ap.add_argument('--out', required=True); ap.add_argument('--bridges')
    for b in main(ap.parse_args().ucbt_run, ap.parse_args().out, ap.parse_args().bridges):
        c = b['evidence']['coverage']
        print(b['id'], 'novos', b['entering_units'], 'alterados', b['overlap_units'], {k: (round(v, 3) if isinstance(v, float) else v) for k, v in c.items()})
