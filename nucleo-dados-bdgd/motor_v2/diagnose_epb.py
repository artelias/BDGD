"""EPB 2022->2023 municipal coverage diagnostic. Reads only local Parquets (no ZIP/GDB, no download).

Separates (a) growth in municipalities present in both years, (b) municipalities that enter the coverage, and
(c) a succession hypothesis check against Energisa Borborema (EBO, DIST 6611) 2022. The hypothesis is evidence,
not proof of legal succession, and nothing here is labelled as new connections.
Usage: python -m motor_v2.diagnose_epb --run <runs/..> --ebo <EBO 2022 UCBT.parquet> --out <dir>"""
import argparse
import csv
import json
from pathlib import Path
import duckdb
from .runner import atomic, digest


def totals(db, path):
    return dict(db.execute("SELECT MUN,sum(clientes_ativos) FROM read_parquet(?) GROUP BY 1", [str(path)]).fetchall())


def diagnose(run, ebo_ucbt, out, dist=6600, ebo_dist=6611, year=2023):
    db = duckdb.connect()
    base = Path(run) / str(dist) / 'ucbt_quantidade'
    prev_f, cur_f = base / str(year-1) / 'territorial.parquet', base / str(year) / 'territorial.parquet'
    prev, cur = totals(db, prev_f), totals(db, cur_f)
    ebo = dict(db.execute("SELECT MUN,count(*) FILTER (WHERE SIT_ATIV='AT') FROM read_parquet(?) GROUP BY 1", [str(ebo_ucbt)]).fetchall())
    later = {y: totals(db, base / str(y) / 'territorial.parquet') for y in (year+1, year+2) if (base / str(y) / 'territorial.parquet').exists()}
    both = sorted(set(prev) & set(cur)); entering = sorted(set(cur) - set(prev)); leaving = sorted(set(prev) - set(cur))
    rows = []
    for m in entering:
        rows.append(dict(MUN=m, status='enters_coverage', epb_prior=None, ebo_prior=ebo.get(m), current=cur[m],
                         ratio_current_to_ebo=cur[m]/ebo[m] if ebo.get(m) else None,
                         later=json.dumps({y: v.get(m) for y, v in later.items()})))
    overlap = [m for m in both if m in ebo]
    for m in overlap:
        rows.append(dict(MUN=m, status='in_both_years_and_in_EBO', epb_prior=prev[m], ebo_prior=ebo[m], current=cur[m],
                         ratio_current_to_ebo=None, later=json.dumps({y: v.get(m) for y, v in later.items()})))
    s = lambda d, ms: sum(d[m] for m in ms if m in d)
    comparable_prev, comparable_cur = s(prev, both), s(cur, both)
    comb_cohort = [m for m in cur if m in prev or m in ebo]
    comb_prev = sum(prev.get(m, 0) + ebo.get(m, 0) for m in comb_cohort)
    summary = dict(
        dist=dist, year=year, municipalities_prior=len(prev), municipalities_current=len(cur),
        entering=len(entering), entering_stock_current=s(cur, entering), leaving=leaving,
        comparable_municipalities=len(both), comparable_prior=comparable_prev, comparable_current=comparable_cur,
        comparable_growth=comparable_cur/comparable_prev-1,
        naive_total_growth=sum(cur.values())/sum(prev.values())-1,
        entering_all_in_ebo_prior=all(m in ebo for m in entering),
        entering_ebo_prior_stock=s(ebo, entering),
        entering_vs_ebo_ratio=s(cur, entering)/s(ebo, entering) if s(ebo, entering) else None,
        ebo_municipalities=len(ebo), ebo_stock_prior=sum(ebo.values()),
        combined_prior_epb_plus_ebo=sum(prev.values())+sum(ebo.values()), current_total=sum(cur.values()),
        combined_growth=sum(cur.values())/(sum(prev.values())+sum(ebo.values()))-1,
        overlap_municipalities_with_ebo=overlap, overlap_ebo_stock=s(ebo, overlap),
        classification='perimeter_absorption_probable_NOT_proven_succession_NOT_new_connections',
        sources={'epb_prior': digest(prev_f), 'epb_current': digest(cur_f), 'ebo_ucbt_2022': digest(ebo_ucbt)},
        policy='entering municipalities have no prior snapshot: no target and no zero; the model cohort excludes them; '
               'physical expansion is measured only on comparable municipalities')
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    with (out / 'EPB_COVERAGE_2023.csv').open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, list(rows[0])); w.writeheader(); w.writerows(rows)
    atomic(out / 'EPB_COVERAGE_2023.json', summary)
    return summary


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True); ap.add_argument('--ebo', required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args(); print(json.dumps(diagnose(a.run, a.ebo, a.out), indent=1, default=str))
