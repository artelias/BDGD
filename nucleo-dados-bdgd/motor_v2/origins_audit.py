"""Feasibility of more historical origins from competences BEFORE 2022, using only the versioned ANEEL catalog snapshot.

No file is downloaded or opened. The output lists, per DIST, the competences in the catalog with layout family and the
generation stamp in the title (`_AAAAMMDD-HHMM`), and how many forecast origins each extension would give. Title stamps
are candidate evidence of a package's generation date, NOT proof of its public availability: they are reported, not applied.
Usage: python -m motor_v2.origins_audit --catalog <catalogo_arcgis_atual.json> --out <dir>"""
import argparse
import csv
import json
import re
from pathlib import Path
from .runner import atomic, digest

TITLE = re.compile(r'(?P<name>.+?)_(?P<dist>\d+)_(?P<base>\d{4}-\d{2}-\d{2})_(?P<layout>[A-Za-z]\d+)_(?P<stamp>\d{8})-(?P<hhmm>\d{4})')
FAMILY = {'V11': 'current (2022+ layout used by the engine)', 'V10': 'adjacent older layout: compatibility unverified',
          'M10': 'older module layout: compatibility unverified', 'M6': 'oldest module layout: compatibility unverified'}


def parse(catalog):
    rows = []
    for it in json.loads(Path(catalog).read_text(encoding='utf-8'))['items']:
        m = TITLE.match(it['title'])
        if m:
            rows.append(dict(dist=int(m['dist']), empresa=m['name'], competence=m['base'], year=int(m['base'][:4]), layout=m['layout'],
                             generation_stamp=f"{m['stamp'][:4]}-{m['stamp'][4:6]}-{m['stamp'][6:]}", item_id=it['id'], title=it['title'],
                             tags_extra='Extra' in (it.get('tags') or [])))
    return rows


def origins_for(years, first_engine_year=2022, last=2025):
    """Forecast origins available when the series covers `years` (needs the origin year, one earlier year for the inner
    validation, and a target year): origins are the years y with y-1 and y+1 present, y+1<=last."""
    ys = sorted(set(years) | set(range(first_engine_year, last + 1)))
    return [y for y in ys if y - 1 in ys and y + 1 in ys and y + 1 <= last]


def feasibility(rows, dists, first=2022):
    out = []
    for d in dists:
        mine = [r for r in rows if r['dist'] == d]
        by_year = {}
        for r in mine:
            by_year.setdefault(r['year'], []).append(r)
        extra = [y for y in sorted(by_year) if y < first]
        contiguous, y = [], first - 1
        while y in by_year:
            contiguous.append(y); y -= 1
        contiguous.sort()
        out.append(dict(DIST=d, empresa=mine[0]['empresa'] if mine else None, competences_before_2022=extra,
                        contiguous_back_from_2021=contiguous, duplicates_same_competence={y: len(v) for y, v in by_year.items() if len(v) > 1},
                        layouts={y: sorted({r['layout'] for r in v}) for y, v in sorted(by_year.items()) if y < first},
                        origins_now=origins_for([]), origins_if_2021=origins_for([2021]),
                        origins_if_all_contiguous=origins_for(contiguous), minimum_required=3))
    return out


def main(catalog, out, dists):
    rows = parse(catalog)
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    sel = sorted([r for r in rows if r['dist'] in dists and r['year'] <= 2021], key=lambda r: (r['dist'], r['competence'], r['generation_stamp']))
    for r in sel:
        r['layout_family'] = FAMILY.get(r['layout'], 'unknown')
    with (out / 'EARLIER_COMPETENCES.csv').open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, list(sel[0])); w.writeheader(); w.writerows(sel)
    report = dict(catalog_sha256=digest(catalog), items=len(rows), feasibility=feasibility(rows, dists),
                  conclusion='Competences 2016-2021 exist in the catalog for all three companies, but no Parquet exists locally: using them requires '
                             'authorized downloads, GDB-to-Parquet conversion, DDA/TUC/identity compatibility checks per layout (V10, M10, M6) and a '
                             'decision on duplicated competences. Nothing was downloaded or inferred. Generation stamps in titles are candidate vintage '
                             'evidence to be verified, not applied.')
    atomic(out / 'ORIGINS_FEASIBILITY.json', report)
    return report


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--catalog', required=True); ap.add_argument('--out', required=True); ap.add_argument('--dists', nargs='*', type=int, default=[26, 6585, 6600])
    a = ap.parse_args()
    print(json.dumps(main(a.catalog, a.out, a.dists)['feasibility'], indent=1))
