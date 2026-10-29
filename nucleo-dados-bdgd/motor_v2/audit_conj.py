"""CONJ (consumer set) continuity 2022-2025 across UCBT, UNTRMT and SSDMT. Reads Parquets only.

For each DIST and year: how many CONJ codes each entity carries, how much of each entity's stock falls in CONJ present in
the other entities (consistency of the key), and how much of the stock sits in CONJ that already existed in the previous
year (continuity). Codes that appear/disappear with a large stock are possible renames or merges and are listed.
A CONJ key with weak continuity must not be used as a territorial unit for the model; this audit says whether it can.
Usage: python -m motor_v2.audit_conj --ucbt-run <runs/..> --out <dir> [--dists 26 6585 6600]"""
import argparse
import csv
import json
from pathlib import Path
import duckdb
from .adapters import path as parquet_path, source
from .runner import atomic, norm, resolve_sources

YEARS = (2022, 2023, 2024, 2025)


def conj_maps(con, src):
    """-> dict entity -> {conj: stock}; SSDMT km, UNTRMT transformers (all rows), None when the entity or field is absent."""
    out = {}
    cols = source(con, src, 'SSDMT', 'net')
    if cols and {'CONJ', 'COMP'} <= cols:
        out['ssdmt'] = {k: float(v or 0) / 1000 for k, v in con.execute(f"SELECT coalesce({norm('CONJ')},'MISSING'),sum(try_cast(COMP AS DOUBLE)) FROM net GROUP BY 1").fetchall()}
    cols = source(con, src, 'UNTRMT', 'un')
    if cols and 'CONJ' in cols:
        out['untrmt'] = {k: float(v) for k, v in con.execute(f"SELECT coalesce({norm('CONJ')},'MISSING'),count(*) FROM un GROUP BY 1").fetchall()}
    return out


def ucbt_map(con, ucbt_run, dist, year):
    f = Path(ucbt_run) / str(dist) / 'ucbt_quantidade' / str(year) / 'territorial.parquet'
    if not f.exists():
        return None
    return {k: float(v) for k, v in con.execute("SELECT coalesce(CONJ,'MISSING'),sum(clientes_ativos) FROM read_parquet(?) GROUP BY 1", [str(f)]).fetchall()}


def share(stock, keys):
    total = sum(stock.values())
    return sum(v for k, v in stock.items() if k in keys) / total if total else None


def audit(dists, ucbt_run, out, years=YEARS):
    con = duckdb.connect()
    con.execute("SET memory_limit='768MB'; SET threads=1")
    maps, rows, events = {}, [], []
    try:
        for d in dists:
            srcs = {s['year']: s for s in resolve_sources(d, 'rede_mt', 'extensao_km') if 'error' not in s}
            for y in years:
                if y not in srcs:
                    continue
                m = conj_maps(con, srcs[y]); u = ucbt_map(con, ucbt_run, d, y)
                if u is not None:
                    m['ucbt'] = u
                maps[d, y] = m
        for (d, y), m in sorted(maps.items()):
            prev = maps.get((d, y - 1), {})
            row = dict(DIST=d, ano=y)
            for e, stock in m.items():
                keys = set(stock) - {'MISSING'}
                row[f'{e}_n_conj'] = len(keys)
                row[f'{e}_stock_without_conj'] = stock.get('MISSING', 0.)
                row[f'{e}_code_lengths'] = '|'.join(sorted({str(len(k)) for k in keys}))
                for other, ostock in m.items():
                    if other != e:
                        row[f'{e}_stock_in_{other}'] = share(stock, set(ostock) - {'MISSING'})
                if e in prev:
                    pk = set(prev[e]) - {'MISSING'}
                    row[f'{e}_continuity'] = share(stock, pk)                  # stock this year sitting in CONJ that existed last year
                    row[f'{e}_new_conj'] = len(keys - pk); row[f'{e}_gone_conj'] = len(pk - keys)
                    for k in sorted(keys - pk, key=lambda k: -stock[k])[:5]:
                        events.append(dict(DIST=d, ano=y, entity=e, event='new', conj=k, stock=stock[k], share=stock[k] / sum(stock.values())))
                    for k in sorted(pk - keys, key=lambda k: -prev[e][k])[:5]:
                        events.append(dict(DIST=d, ano=y, entity=e, event='gone', conj=k, stock=prev[e][k], share=prev[e][k] / sum(prev[e].values())))
            rows.append(row)
    finally:
        con.close()
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    for name, data in (('CONJ_CONTINUITY.csv', rows), ('CONJ_EVENTS.csv', events)):
        if data:
            with (out / name).open('w', newline='', encoding='utf-8-sig') as f:
                w = csv.DictWriter(f, list(dict.fromkeys(k for r in data for k in r)))
                w.writeheader(); w.writerows(data)
    worst = [(r['DIST'], r['ano'], e, r[f'{e}_continuity']) for r in rows for e in ('ssdmt', 'untrmt', 'ucbt') if r.get(f'{e}_continuity') is not None]
    summary = dict(rows=len(rows), min_continuity=min((w[3] for w in worst), default=None),
                   verdict='usable_as_territorial_unit' if worst and min(w[3] for w in worst) >= .95 else 'continuity_below_95pct_review_required',
                   lowest=sorted(worst, key=lambda w: w[3])[:5])
    atomic(out / 'CONJ_SUMMARY.json', summary)
    return summary


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--ucbt-run', required=True); ap.add_argument('--out', required=True); ap.add_argument('--dists', nargs='*', type=int, default=[26, 6585, 6600])
    a = ap.parse_args()
    print(json.dumps(audit(a.dists, a.ucbt_run, a.out), indent=1, default=str))
