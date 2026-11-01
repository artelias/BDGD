"""Voltage-regulator power: own (proprio) or throughput (passante) rating, classified record by record.

    python -m motor_v2.nacional.reguladores            # reads EQRE/UNREMT/CTMT of the contract publications (minutes)
    python -m motor_v2.nacional.reguladores --resumo   # recomputes the per-DIST convention from the saved audit

EQRE.POT_NOM -> TPOTAPRT is an apparent power in kVA, but the manufacturers' nameplate of a step voltage regulator states the OWN
(self-cooled) rating, which is the throughput rating times the regulation range: a single-phase 167 kVA unit at 7.62 kV and
+-10 % carries 219 A, i.e. 1,670 kVA of throughput. Some distributors record the own rating, others the throughput, so a national
sum of POT_NOM is not a stock of anything (motor_v2/nacional/potencia.py measured it larger than all distribution transformation).

Rule per record (only fields of the BDGD itself, no external constant other than sqrt(3)):
  V  = CTMT.TEN_NOM -> TTEN (line-to-line voltage of the circuit the regulator sits on, through UNREMT.CTMT);
  I  = EQRE.COR_NOM -> TCOR (rated current, A);
  throughput = V/sqrt(3) * I    when EQRE.LIG_FAS_P is one phase plus neutral (AN, BN, CN),
               V * I            when it is two phases (AB, BC, CA: open or closed delta),
               sqrt(3) * V * I  when it is three phases (ABC, ABCN: three-phase unit);
  r  = POT_NOM / throughput.  r in [0.02, 0.30] -> PROPRIA: the regulation range (+-5 % .. +-10 %, nameplate own rating), down to
        ~0.03 when the unit is applied with extended current at a reduced range (ADD-AMP, 160 % of the rated current at +-5 %),
        and up to 0.30 for a circuit recorded at a lower voltage class than the unit;  r in [0.60, 1.70] -> PASSANTE;
  anything else (the gap between the bands is a factor of two on each side), or a missing V, I, connection or link -> INDETERMINADO.
A DIST x year has a single convention when at least 90 % of its records are classified and at least 95 % of the classified records
fall in one class. A kVA series is released (experimental) only for a DIST with >= 2 competences of the SAME convention whose
records all carry a valid power code and whose count equals the contract count (the potencia.py gate); its unit says which
rating it is. Own and throughput ratings are never added together and never converted into each other (that would need the
regulation range, which the BDGD does not carry), so there is no national total of regulator power."""
import csv
import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import duckdb

from . import CONTRACT, ROOT_OUT
from .relatorio import write_csv
from ..runner import atomic, digest, resolve_sources

KNOW = Path('C:/GEOIA/GEOIA_DATA_HUB/knowledge/BDGD_DDA_CATALOG_M10.json')
OUT = ROOT_OUT / 'potencia'
PROPRIA = (0.02, 0.30)
PASSANTE = (0.60, 1.70)
MIN_CLASSIFICADOS = 0.90
MIN_DOMINANTE = 0.95
SQ3 = math.sqrt(3)


def fases(lig):
    """-> number of phase conductors of EQRE.LIG_FAS_P and whether the neutral is the return (None when unknown)."""
    s = (lig or '').strip().upper()
    ph = sum(1 for ch in 'ABC' if ch in s)
    if not ph or any(ch not in 'ABCN' for ch in s):
        return None
    return ph, 'N' in s


def passante_kva(v_ll, corrente, lig):
    """Throughput rating in kVA from the circuit line-to-line voltage (V), the rated current (A) and the connection."""
    f = fases(lig)
    if not f or not v_ll or not corrente or v_ll <= 0 or corrente <= 0:
        return None
    ph, neutro = f
    if ph == 1 and neutro:
        return v_ll / SQ3 * corrente / 1000
    if ph == 2:
        return v_ll * corrente / 1000
    if ph == 3:
        return SQ3 * v_ll * corrente / 1000
    return None


def classificar(pot_kva, v_ll, corrente, lig):
    """-> (PROPRIA | PASSANTE | INDETERMINADO, ratio or None) for one regulator record."""
    th = passante_kva(v_ll, corrente, lig)
    if th is None or not pot_kva or pot_kva <= 0:
        return 'INDETERMINADO', None
    r = pot_kva / th
    if PROPRIA[0] <= r <= PROPRIA[1]:
        return 'PROPRIA', r
    if PASSANTE[0] <= r <= PASSANTE[1]:
        return 'PASSANTE', r
    return 'INDETERMINADO', r


def convencao(contagens):
    """{class: records} of one DIST x year -> (PROPRIA | PASSANTE | MISTA | SEM_REGISTROS, share classified, share dominant)."""
    n = sum(contagens.values())
    if not n:
        return 'SEM_REGISTROS', None, None
    cl = contagens.get('PROPRIA', 0) + contagens.get('PASSANTE', 0)
    share = cl / n
    if not cl:
        return 'MISTA', share, None
    dom, k = max(((c, contagens.get(c, 0)) for c in ('PROPRIA', 'PASSANTE')), key=lambda x: x[1])
    if share >= MIN_CLASSIFICADOS and k / cl >= MIN_DOMINANTE:
        return dom, share, k / cl
    return 'MISTA', share, k / cl


def series_liberadas(linhas):
    """[(DIST, convention, [years])] of the DIST with >= 2 competences of one convention that also pass the potencia.py gate."""
    by = defaultdict(lambda: defaultdict(list))
    for r in linhas:
        if r['convencao'] in ('PROPRIA', 'PASSANTE') and r['gate_potencia']:
            by[int(r['DIST'])][r['convencao']].append(int(r['ano']))
    out = []
    for d, cv in sorted(by.items()):
        best = max(cv.items(), key=lambda x: (len(x[1]), max(x[1])))
        if len(best[1]) >= 2 and len(cv) == 1:      # one convention in every year that passes; a switch blocks the series
            out.append((d, best[0], sorted(best[1])))
    return out


def dda():
    d = json.loads(KNOW.read_text(encoding='utf-8'))
    t = {x['table']: x['values'] for x in d['tables']}
    pick = lambda name, col: {str(v['COD_ID']).strip(): v.get(col) for v in t[name]}
    return pick('TPOTAPRT', 'POT'), pick('TCOR', 'CORR'), pick('TTEN', 'TEN'), digest(KNOW)


def _p(src, e):
    b = Path(src['base'])
    return b / f'entidade={e}' / 'part-0.parquet' if src['year'] == 2025 else b / f'{e}.parquet'


def auditar(con, src):
    """Classified record counts and kVA by class of one publication (EQRE joined to UNREMT and CTMT)."""
    pe, pu, pc = _p(src, 'EQRE'), _p(src, 'UNREMT'), _p(src, 'CTMT')
    if not pe.exists():
        return None
    cols = {r[0] for r in con.execute('DESCRIBE SELECT * FROM read_parquet(?)', [str(pe)]).fetchall()}
    need = {'POT_NOM', 'COR_NOM', 'LIG_FAS_P', 'UN_RE'}
    if not need <= cols:
        n = con.execute('SELECT count(*) FROM read_parquet(?)', [str(pe)]).fetchall()[0][0]
        return dict(registros=n, PROPRIA=0, PASSANTE=0, INDETERMINADO=n, kva=dict(), razoes=[], faltam=sorted(need - cols))
    link = pu.exists() and pc.exists()
    q = f"""SELECT tp.pot, tc.corr, trim(CAST(e.LIG_FAS_P AS VARCHAR)) lig, {'tt.ten' if link else 'NULL::DOUBLE'} v
            FROM read_parquet(?) e
            LEFT JOIN tpot tp ON tp.cod = trim(CAST(e.POT_NOM AS VARCHAR))
            LEFT JOIN tcor tc ON tc.cod = trim(CAST(e.COR_NOM AS VARCHAR))
            {'''LEFT JOIN (SELECT DISTINCT trim(CAST(COD_ID AS VARCHAR)) k, trim(CAST(CTMT AS VARCHAR)) ct FROM read_parquet(?)) u ON u.k = trim(CAST(e.UN_RE AS VARCHAR))
            LEFT JOIN (SELECT DISTINCT trim(CAST(COD_ID AS VARCHAR)) k, trim(CAST(TEN_NOM AS VARCHAR)) tn FROM read_parquet(?)) c ON c.k = u.ct
            LEFT JOIN tten tt ON tt.cod = c.tn''' if link else ''}"""
    rows = con.execute(q, [str(pe)] + ([str(pu), str(pc)] if link else [])).fetchall()
    cnt, kva, rz = Counter(), Counter(), []
    for pot, corr, lig, v in rows:
        k, r = classificar(pot, v, corr, lig)
        cnt[k] += 1
        kva[k] += pot or 0
        if r is not None:
            rz.append(r)
    rz.sort()
    q_ = [round(rz[int(p * (len(rz) - 1))], 4) for p in (.1, .5, .9)] if rz else []
    return dict(registros=len(rows), **{k: cnt.get(k, 0) for k in ('PROPRIA', 'PASSANTE', 'INDETERMINADO')}, kva=dict(kva), razoes=q_, faltam=[] if link else ['UNREMT/CTMT'])


def gate_potencia():
    """{(DIST, year): (gate, contract count)} of the regulator family from the potencia.py audit (valid code + count = contract)."""
    out = {}
    with open(OUT / 'POTENCIA_POR_DIST_ANO.csv', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r['familia'] == 'reguladores':
                out[int(r['DIST']), int(r['ano'])] = (r['gate_liberacao_experimental'] == 'True', r['quantidade_contrato'])
    return out


def run():
    t0 = time.monotonic()
    tpot, tcor, tten, dsha = dda()
    con = duckdb.connect(); con.execute("SET memory_limit='768MB'; SET threads=1")
    for name, m in (('tpot', tpot), ('tcor', tcor), ('tten', tten)):
        con.execute(f'CREATE TEMP TABLE {name}(cod VARCHAR, {"pot" if name == "tpot" else "corr" if name == "tcor" else "ten"} DOUBLE)')
        con.executemany(f'INSERT INTO {name} VALUES (?, ?)', [(k, v) for k, v in m.items() if v is not None])
    gate = gate_potencia()
    dists = sorted({d for d, _ in gate})
    linhas, erros = [], []
    for d in dists:
        for s in resolve_sources(d, 'reguladores'):
            if s.get('error'):
                continue
            try:
                a = auditar(con, s)
            except Exception as e:      # recorded, never silently dropped
                erros.append(dict(DIST=d, ano=s['year'], erro=str(e))); continue
            if a is None:
                continue
            cv, share, dom = convencao({k: a[k] for k in ('PROPRIA', 'PASSANTE', 'INDETERMINADO')})
            g, cq = gate.get((d, s['year']), (False, None))
            linhas.append(dict(DIST=d, ano=s['year'], item=s['item'], registros=a['registros'], propria=a['PROPRIA'], passante=a['PASSANTE'],
                               indeterminado=a['INDETERMINADO'], share_classificado=share, share_dominante=dom, convencao=cv,
                               kva_propria=round(a['kva'].get('PROPRIA', 0), 3), kva_passante=round(a['kva'].get('PASSANTE', 0), 3),
                               kva_indeterminado=round(a['kva'].get('INDETERMINADO', 0), 3), razao_p10_p50_p90=json.dumps(a['razoes']),
                               campos_ausentes='|'.join(a['faltam']), quantidade_contrato=cq, gate_potencia=g))
        print(d, len(linhas), round(time.monotonic() - t0), flush=True)
    con.close()
    write_csv(OUT / 'REGULADORES_CONVENCAO_POR_DIST_ANO.csv', linhas)
    return resumo(linhas, dict(dda_sha256=dsha, contrato_sha256=digest(CONTRACT), erros=erros, segundos=round(time.monotonic() - t0, 1)))


def ler():
    conv = lambda k, v: (int(v) if k in ('DIST', 'ano', 'registros', 'propria', 'passante', 'indeterminado') else
                         v == 'True' if k == 'gate_potencia' else float(v) if k.startswith(('kva_', 'share_')) and v != '' else v)
    with open(OUT / 'REGULADORES_CONVENCAO_POR_DIST_ANO.csv', encoding='utf-8') as f:
        return [{k: conv(k, v) for k, v in r.items()} for r in csv.DictReader(f)]


def resumo(linhas, extra=None):
    lib = series_liberadas(linhas)
    m = dict(regra=dict(propria=PROPRIA, passante=PASSANTE, min_classificados=MIN_CLASSIFICADOS, min_dominante=MIN_DOMINANTE),
             dist_ano=len(linhas), convencoes=dict(Counter(r['convencao'] for r in linhas)),
             series_liberadas=[dict(DIST=d, convencao=c, anos=ys) for d, c, ys in lib],
             por_convencao=dict(Counter(c for _, c, _ in lib)), total_nacional='nao_definido (proprio e passante nao sao somaveis)', **(extra or {}))
    atomic(OUT / 'MANIFESTO_REGULADORES.json', m)
    return m


if __name__ == '__main__':
    m = resumo(ler()) if '--resumo' in sys.argv else run()
    print(json.dumps({k: v for k, v in m.items() if k != 'series_liberadas'}, ensure_ascii=False, indent=1), len(m['series_liberadas']))
