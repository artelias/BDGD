"""Audit of the conservative / aggressive scenarios (both levels): implied growth, accumulated change 2025-2030, extreme series,
DIST shares of the totals, the transitions each screen excludes and the sensitivity of the national totals to the screen.

    python -m motor_v2.nacional.auditoria_cenarios

The moderate path is read from the saved projections and never changed. For every series the envelopes are recomputed from that
path under each screen variant (cenarios.scenarios, same formula):
  sem_triagem               every comparable transition of the series;
  v1_mad_nacional           first run: median +- 5 MAD of all companies (object x year);
  v2                        official from this revision: fase4 evidence, object x year x size tercile, temporal pattern;
  v2_com_nao_verificaveis   v2 also keeping the atypical last steps that cannot be verified yet;
  v2_k3 / v2_k8             v2 with K = 3 / 8 MAD;
  v2_sem_evidencia          v2 without the fase4 evidence layer.
The thresholds used to FLAG series (x2 / x0.5 accumulated 2025-2030) are reporting thresholds only; nothing is capped."""
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq

from . import LEVEL_A, ROOT_OUT
from . import distribuidora as B
from .cenarios import (MAD_K, YEARS, evidence, hist_growth, scenarios, screen_table, screen_table_v2, screened_growth,
                       screened_growth_v2)
from .elegibilidade import CONCEITO_A
from .relatorio import write_csv
from ..runner import ROOT, atomic

OUT = ROOT_OUT / 'auditoria_cenarios'
VARIANTS = ('sem_triagem', 'v1_mad_nacional', 'v2', 'v2_com_nao_verificaveis', 'v2_k3', 'v2_k8', 'v2_sem_evidencia')


def families():
    out = {}
    p = ROOT_OUT / 'MATRIZ_ELEGIBILIDADE_CATALOGO.csv'
    for r in csv.DictReader(open(p, encoding='utf-8')):
        out.setdefault(r['objetivo_id'], r['familia'])
    return out


def growths(variant, pts, breaks, t1, t2, ev):
    if variant == 'sem_triagem':
        return hist_growth(pts, breaks), []
    if variant == 'v1_mad_nacional':
        kept, exc = screened_growth(pts, breaks, t1)
        return kept, [dict(x, classe='v1_atipica') for x in exc]
    k = 3.0 if variant == 'v2_k3' else 8.0 if variant == 'v2_k8' else MAD_K
    kept, cls = screened_growth_v2(pts, breaks, t2, None if variant == 'v2_sem_evidencia' else ev,
                                   incluir_nao_verificaveis=variant == 'v2_com_nao_verificaveis', k=k)
    return kept, cls


def series_b():
    cells, meta = B.load()
    dists = sorted({d for d, _, _ in cells}); concepts = sorted(k for k in meta if isinstance(k, str))
    t1, t2 = {}, {}
    for c in concepts:
        ser, br = {}, {}
        for d in dists:
            ser[d], br[d] = B.series_points(cells, d, c)
        t1[c], t2[c] = screen_table(ser, br), screen_table_v2(ser, br)
    proj = pq.read_table(ROOT_OUT / 'distribuidora' / 'PROJECOES_B_INTERNO.parquet').to_pylist()
    mod = defaultdict(dict)
    for r in proj:
        if r['cenario'] == 'Moderado':
            mod[r['DIST'], r['conceito']][r['ano']] = r['valor_bruto']
    out = []
    for dec in csv.DictReader(open(ROOT_OUT / 'distribuidora' / 'DECISOES_B.csv', encoding='utf-8')):
        if dec['status_projecao'] != 'gerada':
            continue
        d, c, anchor = int(dec['DIST']), dec['conceito'], int(dec['ano_ancora'])
        pts, breaks = B.series_points(cells, d, c, anchor)
        out.append(dict(nivel='B', DIST=d, objeto=c, conceito=c, unidade=meta[c]['unidade'], ancora=anchor, valor_ancora=float(dec['valor_ancora']),
                        moderado=mod[d, c], pts=pts, breaks=breaks, t1=t1[c], t2=t2[c]))
    return out


def series_a():
    from ..assets import ASSETS
    from ..bridges import load as load_bridges
    from ..comparison import load_panel
    from .painel import PANEL
    from .projecao import physical_series, _breaks
    from ..runner import read
    q = read(ROOT_OUT / 'quarentena.json')
    vm = set(json.loads(Path(q['municipios_validos']).read_text(encoding='utf-8')))
    proj = pq.read_table(ROOT_OUT / 'projecao' / 'PROJECOES_A_DISTRIBUIDORA_INTERNO.parquet').to_pylist()
    mod = defaultdict(dict)
    for r in proj:
        if r['cenario'] == 'Moderado':
            mod[r['DIST'], r['ativo'], r['metrica']][r['ano']] = r['valor_bruto']
    decs = list(csv.DictReader(open(ROOT_OUT / 'projecao' / 'DECISOES_A.csv', encoding='utf-8')))
    out = []
    for asset in LEVEL_A:
        spec = ASSETS[asset]
        _, quality, _ = load_panel(str(PANEL), asset, load_bridges(ROOT / 'motor_v2/bridges'), 0.98, 0.95 if asset.startswith('rede_') else None,
                                   valid_municipalities=vm, quarantine=q['quarentena'])
        ser, br = physical_series(quality)
        t1, t2 = screen_table(ser, br), screen_table_v2(ser, br)
        for dec in decs:
            if dec.get('status_projecao') != 'gerada' or dec['ativo'] != spec['ativo'] or dec['metrica'] != spec['metrica']:
                continue
            d = int(dec['DIST']); anchor = int(dec['ano_ancora'])
            pts = {y: v for y, v in ser.get(d, {}).items() if y <= anchor}
            out.append(dict(nivel='A', DIST=d, objeto=asset, conceito=CONCEITO_A[asset], unidade=spec['unit'], ancora=anchor,
                            valor_ancora=float(dec['total_ancora']), moderado=mod[d, spec['ativo'], spec['metrica']], pts=pts,
                            breaks={y for y in br.get(d, set()) if y <= anchor}, t1=t1, t2=t2))
    return out


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    ev = evidence(); fam = families()
    allser = series_b() + series_a()
    srows, trows, sens = [], [], defaultdict(float)
    sens_n = defaultdict(set)
    paths2 = {}
    for s in allser:
        e = {y: ev[s['DIST'], s['conceito'], y] for y in s['pts'] if (s['DIST'], s['conceito'], y) in ev}
        res = {}
        for v in VARIANTS:
            kept, cls = growths(v, s['pts'], s['breaks'], s['t1'], s['t2'], e)
            sc, meta = scenarios(s['ancora'], s['valor_ancora'], s['moderado'], kept)
            res[v] = (sc, meta, cls)
            if s['ancora'] == 2025:
                for name, path in sc.items():
                    sens[s['nivel'], s['objeto'], v, name] += path[2030]; sens_n[s['nivel'], s['objeto'], v, name].add(s['DIST'])
        sc, meta, cls = res['v2']; paths2[s['nivel'], s['objeto'], s['DIST']] = (s, sc)
        _, _, c1 = res['v1_mad_nacional']
        v1x = {x['ano'] for x in c1}
        h = 2030 - s['ancora']; a0 = s['valor_ancora']
        cagr = {k: ((sc[k][2030] / a0) ** (1 / h) - 1) if a0 > 0 and sc[k][2030] > 0 else None for k in sc}
        acc = {k: (sc[k][2030] / a0 - 1) if a0 > 0 else None for k in sc}
        ntr = len(hist_growth(s['pts'], s['breaks']))
        srows.append(dict(nivel=s['nivel'], DIST=s['DIST'], objeto=s['objeto'], familia=fam.get(s['conceito']), unidade=s['unidade'], ancora=s['ancora'],
                          valor_ancora=a0, transicoes_comparaveis=ntr, transicoes_no_envelope_v2=meta['transicoes_historicas'],
                          classes_v2=json.dumps(Counter(x['classe'] for x in cls)), cagr_conservador=cagr['Conservador'], cagr_moderado=cagr['Moderado'],
                          cagr_agressivo=cagr['Agressivo'], var_acum_conservador=acc['Conservador'], var_acum_moderado=acc['Moderado'], var_acum_agressivo=acc['Agressivo'],
                          agressivo_2030_v1=res['v1_mad_nacional'][0]['Agressivo'][2030], agressivo_2030_v2=sc['Agressivo'][2030],
                          agressivo_2030_sem_triagem=res['sem_triagem'][0]['Agressivo'][2030],
                          conservador_2030_v1=res['v1_mad_nacional'][0]['Conservador'][2030], conservador_2030_v2=sc['Conservador'][2030],
                          expansao_extrema_x2=bool(a0 > 0 and sc['Agressivo'][2030] >= 2 * a0), retracao_extrema_x05=bool(a0 > 0 and sc['Conservador'][2030] <= .5 * a0),
                          ate_duas_transicoes=ntr <= 2, cenarios_degenerados=meta['cenarios_degenerados']))
        for x in cls:
            trows.append(dict(nivel=s['nivel'], DIST=s['DIST'], objeto=s['objeto'], familia=fam.get(s['conceito']), ano=x['ano'], crescimento_log1p=x['crescimento_log1p'],
                              variacao_pct=math.expm1(x['crescimento_log1p']) * 100, estoque_anterior=x['estoque_anterior'], classe_v2=x['classe'],
                              no_envelope_v2=x['no_envelope'], nao_verificavel=x['nao_verificavel'], evidencia_fase4=x['evidencia'], referencia_v2=x.get('referencia'),
                              mediana_ref=x.get('mediana'), mad_ref=x.get('mad'), excluida_v1=x['ano'] in v1x))
    write_csv(OUT / 'AUDITORIA_CENARIOS_SERIES.csv', srows)
    write_csv(OUT / 'AUDITORIA_CENARIOS_TRANSICOES.csv', trows)
    srow = [dict(nivel=k[0], objeto=k[1], variante=k[2], cenario=k[3], total_2030=v, dist=len(sens_n[k])) for k, v in sorted(sens.items())]
    write_csv(OUT / 'AUDITORIA_CENARIOS_SENSIBILIDADE.csv', srow)
    # DIST shares (official v2, anchor 2025)
    part = []
    tot = defaultdict(float)
    for (lvl, obj, d), (s, sc) in paths2.items():
        if s['ancora'] == 2025:
            for k in sc:
                tot[lvl, obj, k] += sc[k][2030]
            tot[lvl, obj, 'delta_agr'] += sc['Agressivo'][2030] - sc['Moderado'][2030]
            tot[lvl, obj, 'delta_cons'] += sc['Moderado'][2030] - sc['Conservador'][2030]
    for (lvl, obj, d), (s, sc) in paths2.items():
        if s['ancora'] != 2025:
            continue
        g = lambda k, v: v / tot[lvl, obj, k] if tot[lvl, obj, k] else None
        part.append(dict(nivel=lvl, objeto=obj, DIST=d, participacao_moderado_2030=g('Moderado', sc['Moderado'][2030]),
                         participacao_agressivo_2030=g('Agressivo', sc['Agressivo'][2030]),
                         participacao_no_excesso_agressivo=g('delta_agr', sc['Agressivo'][2030] - sc['Moderado'][2030]),
                         participacao_na_folga_conservadora=g('delta_cons', sc['Moderado'][2030] - sc['Conservador'][2030])))
    write_csv(OUT / 'AUDITORIA_CENARIOS_PARTICIPACAO_DIST.csv', part)
    v1x = [t for t in trows if t['excluida_v1']]
    summary = dict(
        series=len(srows), series_ancora_2025=sum(1 for r in srows if r['ancora'] == 2025),
        transicoes=len(trows), classes_v2=Counter(t['classe_v2'] for t in trows),
        excluidas_v1=dict(total=len(v1x), por_nivel=Counter(t['nivel'] for t in v1x), classe_v2_das_excluidas_v1=Counter(t['classe_v2'] for t in v1x),
                          por_familia=Counter(t['familia'] for t in v1x).most_common(), geradores=Counter(t['classe_v2'] for t in v1x if t['objeto'] == 'geradores')),
        excluidas_v2=dict(total=sum(1 for t in trows if not t['no_envelope_v2']), por_classe=Counter(t['classe_v2'] for t in trows if not t['no_envelope_v2'])),
        expansao_extrema_x2=sum(r['expansao_extrema_x2'] for r in srows), retracao_extrema_x05=sum(r['retracao_extrema_x05'] for r in srows),
        series_ate_duas_transicoes=sum(r['ate_duas_transicoes'] for r in srows),
        top_excesso_agressivo={f'{lvl}/{obj}': sorted([(p['DIST'], round(p['participacao_no_excesso_agressivo'] or 0, 4)) for p in part if (p['nivel'], p['objeto']) == (lvl, obj)], key=lambda x: -x[1])[:5]
                               for lvl, obj in sorted({(p['nivel'], p['objeto']) for p in part})})
    atomic(OUT / 'AUDITORIA_CENARIOS_RESUMO.json', summary)
    return summary


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False, indent=1, default=str)[:6000])
