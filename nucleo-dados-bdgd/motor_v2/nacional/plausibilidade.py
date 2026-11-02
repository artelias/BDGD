"""Plausibility gate of the 2026-2030 scenarios (release candidate 1.0), read only on the national results.

    python -m motor_v2.nacional.plausibilidade

Why: the scenario engine (cenarios.scenarios) moves the annual log1p growth of the moderate path to the lowest / highest annual
growth observed in the series' own comparable transitions and COMPOUNDS it for five years. A single cadastral step on a tiny base
(0 -> 66 towers; 3 -> 70 sectionalizers) therefore becomes x10^9 by 2030. This gate does not retrain or change the engine: it audits
every projected series and decides, per extreme scenario, ACEITO, CORRIGIDO or BLOQUEADO; blocked values stay in a research artifact.

Reference distribution (no physical or arbitrary cap). Windows of 2 and 3 years (annualised log1p growth) and one-year steps are
pooled from the projected series, EXCLUDING every non-comparable transition (engine-excluded ruptures, fase4 cadastral evidence,
succession events, first entries from zero stock). Quantities, km and kVA are never pooled together. The pool used for a series is
the first level with >= MIN_AMOSTRA windows: (object, metric, size class) -> (unit, size class) -> (unit). The level is recorded.
  L_up / L_dn = p99 / p01 of the windows (what a series has sustained); P95 = alert; steps p90 / p10 = "relevant step".
Decision for an extreme scenario with annual growth g (Agressivo upward, Conservador downward):
  1. inside [L_dn, L_up] -> ACEITO (alert BAIXA beyond P95);
  2. beyond L: if the series itself sustained a move in the same direction in its most recent 2-3 years (window ending at the anchor,
     every one-year step beyond the relevant step of THAT direction, no non-comparable transition) the extreme is CORRIGIDO to that
     demonstrated rate (or accepted when the demonstrated rate is at least as extreme); otherwise BLOQUEADO with the cause;
  3. a zero anchor stock blocks the extremes (growth from zero is undefined).
A moderate path beyond L without the same sustained evidence blocks the whole series (BLOQUEIO_PLAUSIBILIDADE).
Intensity (units per consumer, same scenario and year, other distributors) is an ANOMALY INDICATOR only: it raises an alert, it never
blocks. Hierarchical series (UCBT, Consumidores) are only blocked, never recomputed, and a block on one blocks both."""
import csv
import gzip
import io
import json
import math
from collections import defaultdict

from . import ROOT_OUT, elegibilidade
from . import cobertura as COB
from .cenarios import NAO_FISICO, evidence
from .relatorio import write_csv
from ..metric_contract import round_count
from ..runner import atomic

OUT = ROOT_OUT / 'cobertura'
YEARS = COB.YEARS
CEN = COB.CENARIOS
CLASSES = ('PLAUSIVEL_COM_EVIDENCIA', 'EXTRAPOLACAO_EXTREMA_NAO_SUSTENTADA', 'RUPTURA_CADASTRAL', 'MUDANCA_DE_PERIMETRO', 'BASE_HISTORICA_PEQUENA',
           'HISTORICO_INSUFICIENTE', 'ERRO_DE_CALCULO', 'PENDENTE_DE_HOMOLOGACAO')
HIERARQUICAS = {('ucbt', 'quantidade'), ('consumidores', 'quantidade')}
MIN_AMOSTRA = 100
BASE_MINIMA = 10        # below this stock a percentage step is not replicable evidence (BASE_HISTORICA_PEQUENA)
TOL_MODELO = 0.25       # a fitted moderate path is accepted when the series itself demonstrated at least (1 - TOL) of its rate
lg = math.log1p


def cl(stock):
    s = stock or 0
    return 0 if s < 10 else 1 if s < 100 else 2 if s < 1000 else 3


def q(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, max(0, int(len(v) * p)))]


def nao_comparaveis(d, o, excl, evid, suc):
    """Years whose one-year step INTO that year is not comparable: engine-excluded, fase4 cadastral evidence, corporate succession."""
    ys = set(excl)
    for y in range(2023, 2026):
        f4 = evid.get((d, o, y))
        if (f4 and f4['categoria'] in NAO_FISICO) or (d, y) in suc:
            ys.add(y)
    return ys


def entradas_pool(h, nc):
    """-> (windows [(start stock, annualised growth)], steps [(previous stock, growth)]) of one series, comparable only (start > 0)."""
    jan, passos = [], []
    for span in (2, 3):
        for y in range(2022 + span, 2026):
            a, b = h.get(y - span), h.get(y)
            if a is not None and b is not None and a > 0 and not any(t in nc for t in range(y - span, y + 1)):
                jan.append((a, (lg(b) - lg(a)) / span))
    for y in range(2023, 2026):
        a, b = h.get(y - 1), h.get(y)
        if a is not None and b is not None and a > 0 and y not in nc:
            passos.append((a, lg(b) - lg(a)))
    return jan, passos


class Referencia:
    """Pooled reference distributions with fallback levels: (object, metric, size) -> (unit, size) -> (unit). Units are never mixed."""

    def __init__(self, series):
        self.j, self.p = defaultdict(list), defaultdict(list)
        for s in series:
            jan, passos = entradas_pool(s['h'], s['nc'])
            for a, g in jan:
                for key in (('om', s['unid'], s['o'], s['m'], cl(a)), ('up', s['unid'], cl(a)), ('u', s['unid'])):
                    self.j[key].append(g)
            for a, g in passos:
                for key in (('om', s['unid'], s['o'], s['m'], cl(a)), ('up', s['unid'], cl(a)), ('u', s['unid'])):
                    self.p[key].append(g)

    def limiar(self, unid, o, m, stock):
        c = cl(stock)
        for nivel, key in (('objeto_metrica_porte', ('om', unid, o, m, c)), ('unidade_porte', ('up', unid, c)), ('unidade', ('u', unid))):
            j, p = self.j.get(key, []), self.p.get(key, [])
            if len(j) >= MIN_AMOSTRA and len(p) >= MIN_AMOSTRA // 2:
                return dict(up=max(q(j, .99), 0.0), dn=min(q(j, .01), 0.0), p99=q(j, .99), p01=q(j, .01), p95=q(j, .95), passo_up=q(p, .90), passo_dn=q(p, .10), nivel=nivel, n=len(j))
        return None


def janela_recente(h, ancora, nc, lim, lado):
    """Annualised log1p growth the series sustained in the window ending at the anchor (3, then 2 years) in the direction `lado`
    ('up': every step >= passo_up; 'dn': every step <= passo_dn), or None. Needs a positive start and no non-comparable transition."""
    for span in (3, 2):
        ys = list(range(ancora - span + 1, ancora + 1))
        if ancora - span < 2022 or any(y in nc for y in range(ancora - span, ancora + 1)):
            continue
        a, b = h.get(ancora - span), h.get(ancora)
        if a is None or b is None or a < BASE_MINIMA or any(h.get(y) is None or h.get(y - 1) is None for y in ys):
            continue
        steps = [lg(h[y]) - lg(h[y - 1]) for y in ys]
        ok = all(x >= lim['passo_up'] for x in steps) if lado == 'up' else all(x <= lim['passo_dn'] for x in steps)
        if ok:
            return (lg(b) - lg(a)) / span
    return None


def janelas_proprias(h, ancora, nc):
    """Annualised growth of every comparable window (2-3 years, start > 0) of the series itself."""
    return [g for a, g in entradas_pool({k: v for k, v in h.items() if k <= ancora}, nc)[0]]


def passos_comparaveis(h, ancora, nc):
    return [(y, h[y - 1], lg(h[y]) - lg(h[y - 1])) for y in range(2023, ancora + 1)
            if h.get(y) is not None and h.get(y - 1) is not None and h[y - 1] > 0 and y not in nc]


def causa(h, ancora, g_ext, nc, evid, suc, dist, objetivo, anomalias):
    """-> (classe, motivo, evidencias) of the transition that determines g_ext."""
    det = None
    for y in range(2023, ancora + 1):
        a, b = h.get(y - 1), h.get(y)
        if a is not None and b is not None and abs((lg(b) - lg(a)) - g_ext) < 1e-6:
            det = (y, a, b); break
    ev = dict(transicao=None, passos_comparaveis=len(passos_comparaveis(h, ancora, nc)))
    if det:
        y, a, b = det
        ev['transicao'] = dict(ano=y, de=a, para=b)
        f4 = evid.get((dist, objetivo, y))
        if a == 0:
            return 'RUPTURA_CADASTRAL', f'primeira entrada do ativo (0 -> {b:g} em {y}): crescimento indefinido, nao comparavel', ev
        if f4 and f4['categoria'] in NAO_FISICO:
            ev['fase4'] = f4['categoria']
            return 'RUPTURA_CADASTRAL', f"evidencia fase4: {f4['categoria']} em {y}", ev
        if (dist, y) in suc:
            ev['evento'] = suc[dist, y]
            return 'MUDANCA_DE_PERIMETRO', f'sucessao societaria {suc[dist, y]} no ano da transicao', ev
        n = anomalias.get((dist, y), 0)
        ev['objetos_com_salto_no_mesmo_ano'] = n
        if n >= 3:
            return 'RUPTURA_CADASTRAL', f'{n} tipos de ativo da DIST saltam acima do P95 em {y}: mudanca sistemica de cadastro', ev
        if a < 10:
            return 'BASE_HISTORICA_PEQUENA', f'estoque anterior {a:g} < 10: o passo {a:g} -> {b:g} nao e crescimento replicavel', ev
    if ev['passos_comparaveis'] <= 1:
        return 'HISTORICO_INSUFICIENTE', 'no maximo uma transicao comparavel na serie', ev
    return 'EXTRAPOLACAO_EXTREMA_NAO_SUSTENTADA', 'taxa fora do que 99% das janelas de 2-3 anos comparaveis sustentaram, sem sustentacao recente na propria serie', ev


def decidir(lado, g, gm, A, h, ancora, nc, lim, evid, suc, dist, objetivo, anomalias):
    """Pure decision for one extreme scenario -> dict(estado, classe, severidade, motivo, g, g_pub, evidencias)."""
    if ((g - gm) <= 1e-9) if lado == 'up' else ((gm - g) <= 1e-9):
        return dict(estado='ACEITO', classe='', severidade='', motivo='sem extremo alem do moderado (cenario degenerado, registrado)', g=g, g_pub=g, evidencias={})
    if not A:
        _, mot, ev = causa(h, ancora, g, nc, evid, suc, dist, objetivo, anomalias)
        return dict(estado='BLOQUEADO', classe='HISTORICO_INSUFICIENTE', severidade='ALTA', g=g, g_pub=None, evidencias=ev,
                    motivo='estoque de ancora zero: crescimento a partir de zero e indefinido; ' + mot)
    if lim is None:
        return dict(estado='BLOQUEADO', classe='HISTORICO_INSUFICIENTE', severidade='ALTA', g=g, g_pub=None, evidencias={},
                    motivo='sem distribuicao de referencia comparavel para esta unidade')
    fora = g > lim['up'] if lado == 'up' else g < lim['dn']
    if not fora:
        alerta = lado == 'up' and g > lim['p95']
        return dict(estado='ACEITO', classe='', severidade='BAIXA' if alerta else '', g=g, g_pub=g, evidencias={},
                    motivo='dentro do suporte empirico (taxa dentro do P99/P01 das janelas comparaveis)' + ('; acima do P95: alerta' if alerta else ''))
    w = janela_recente(h, ancora, nc, lim, lado)
    if w is not None and ((w >= gm) if lado == 'up' else (w <= gm)):
        aceita_igual = (w >= g) if lado == 'up' else (w <= g)
        passo = lim['passo_up'] if lado == 'up' else lim['passo_dn']
        return dict(estado='ACEITO' if aceita_igual else 'CORRIGIDO', classe='PLAUSIVEL_COM_EVIDENCIA', severidade='MEDIA', g=g, g_pub=g if aceita_igual else w,
                    evidencias={'janela_recente': w, 'passo_relevante': passo},
                    motivo=(f'taxa {g:.3f} a.a. fora do suporte, mas a propria serie sustentou {w:.3f} a.a. nos ultimos anos' if aceita_igual else
                            f'taxa extrema {g:.3f} a.a. substituida por {w:.3f} a.a., o que a propria serie demonstrou nos ultimos anos (todos os passos alem de {passo:.3f})'))
    cl_, mot, ev = causa(h, ancora, g, nc, evid, suc, dist, objetivo, anomalias)
    return dict(estado='BLOQUEADO', classe=cl_, severidade='ALTA', g=g, g_pub=None, evidencias=ev, motivo=mot)


def moderado_sustentado(gm, lim, proprias, tol=TOL_MODELO):
    """True when the moderate rate is inside the support (the neutral rate 0 always is) or the series itself demonstrated at least that
    rate in one of its own comparable windows (a CAGR/drift model extrapolates exactly that)."""
    if lim is None:
        return False
    if gm > lim['up']:
        return bool(proprias) and max(proprias) >= gm * (1 - tol)
    if gm < lim['dn']:
        return bool(proprias) and min(proprias) <= gm * (1 - tol)
    return True


def caminho(raw_mod, anc, gm, g_pub, conta):
    out = []
    for i, y in enumerate(YEARS):
        z = lg(raw_mod[i]) + (y - anc) * (g_pub - gm)
        x = math.expm1(z) if z > 0 else 0.0
        out.append(round_count(x) if conta else round(x, 6))
    return out


def erro_de_calculo(raw, gc, gm, ga, anc, conta):
    """Published extreme paths must follow the engine formula from the published moderate path. Physical rounding is tolerated: the
    published moderate count is rounded (+-0.5 unit), and the engine compounds from the unrounded value, so the expected extreme is
    an interval; counts also tolerate 1 unit of their own rounding, continuous values 0.1%. Scenarios must be ordered."""
    for k, g in (('Conservador', gc), ('Agressivo', ga)):
        for i, y in enumerate(YEARS):
            m = raw['Moderado'][i]
            esp = []
            for mm in ((max(m - 0.5, 0.0), m + 0.5) if conta else (m, m)):
                z = lg(mm) + (y - anc) * (g - gm)
                esp.append(math.expm1(z) if z > 0 else 0.0)
            lo, hi = min(esp), max(esp)
            tol = 1.0 if conta else max(1e-3 * hi, 1e-3)
            if raw[k][i] < lo - tol or raw[k][i] > hi + tol:
                return True
    return not all(raw['Conservador'][i] <= raw['Moderado'][i] + 1e-9 <= raw['Agressivo'][i] + 2e-9 for i in range(5))


def avaliar(linhas, valores, hist_fn, evid=None, suc=None, decs=None):
    """Applies the gate. Returns (linhas, valores, audit rows, brutos rows, resumo). Mutates linhas/valores in place."""
    evid = evid if evid is not None else evidence()
    suc = suc if suc is not None else dict(elegibilidade.sucessoes())
    if decs is None:
        decs = ({(int(r['DIST']), r['conceito']): r for r in COB._csv(ROOT_OUT / 'distribuidora' / 'DECISOES_B.csv')},
                {(int(r['DIST']), r['ativo'], r['metrica']): r for r in COB._csv(ROOT_OUT / 'projecao' / 'DECISOES_A.csv')},
                {(int(r['DIST']), r['conceito']): r for r in COB._csv(ROOT_OUT / 'distribuidora_potencia' / 'DECISOES_B.csv')})
    decB, decA, decP = decs
    vals = defaultdict(dict)
    for v in valores:
        if v['valor'] != '':
            vals[v['DIST'], v['objetivo'], v['metrica']][v['cenario'], v['ano']] = float(v['valor'])
    S = []
    for i, r in enumerate(linhas):
        if r['estado'] not in COB.PROJETADOS or (r['DIST'], r['objetivo'], r['metrica']) not in vals:
            continue
        d, o, m = r['DIST'], r['objetivo'], r['metrica']
        h = {a: v for a, v, _ in hist_fn(r) if v is not None}
        dec = (decP.get((d, r['variante'])) if r['variante'] else decB.get((d, o)) if r['fonte'] == 'nivel_B' else
               decA.get((d, 'ucbt', 'quantidade')) if r['fonte'] == 'consumidores_reconciliado' else decA.get((d, o, m))) or {}
        try:
            gc, gm, ga = (float(dec['cenario_crescimento_log1p_' + k]) for k in ('conservador', 'moderado', 'agressivo'))
        except (KeyError, ValueError):
            continue
        ex = dec.get('cenario_transicoes_atipicas_excluidas') or ''
        excl = {x['ano'] for x in json.loads(ex)} if ex.startswith('[') else set()
        S.append(dict(i=i, row=r, d=d, o=o, m=m, unid=r['unidade'], h=h, nc=nao_comparaveis(d, o, excl, evid, suc), v=vals[d, o, m],
                      ancora=int(r['ano_ancora']), A=float(r['valor_ancora']), gc=gc, gm=gm, ga=ga, dec=dec))
    ref = Referencia(S)
    anom = defaultdict(int)
    for s in S:
        s['lim'] = ref.limiar(s['unid'], s['o'], s['m'], s['A'])
        for y, a, g in passos_comparaveis(s['h'], s['ancora'], s['nc']):
            if s['lim'] and g > s['lim']['p95']:
                anom[s['d'], y] += 1
    cons30 = {s['d']: s['v'].get(('Moderado', 2030)) for s in S if s['o'] == 'consumidores'}
    audit, brutos = [], []
    for s in S:
        r, d, o, m, h, v, anc, A, lim, nc = s['row'], s['d'], s['o'], s['m'], s['h'], s['v'], s['ancora'], s['A'], s['lim'], s['nc']
        conta = r['natureza'] == 'discrete_count'
        raw = {k: [v.get((k, y)) for y in YEARS] for k in CEN}
        s['raw'] = raw
        s['erro_calc'] = r['fonte'] != 'consumidores_reconciliado' and erro_de_calculo(raw, s['gc'], s['gm'], s['ga'], anc, conta)
        s['w_up'] = janela_recente(h, anc, nc, lim, 'up') if lim else None
        s['w_dn'] = janela_recente(h, anc, nc, lim, 'dn') if lim else None
        s['mod_fora'] = bool(A) and not moderado_sustentado(s['gm'], lim, janelas_proprias(h, anc, nc))
        s['mod_bloq'] = False
        if s['mod_fora']:       # a fitted trend beyond the support is only blocked when non-comparable evidence drives it; otherwise it is an alert
            cm, mm, evm = causa(h, anc, s['gm'], nc, evid, suc, d, o, anom)
            s['mod_classe'], s['mod_motivo'] = cm, mm
            s['mod_bloq'] = cm != 'EXTRAPOLACAO_EXTREMA_NAO_SUSTENTADA'
        res = {k: decidir(lado, g, s['gm'], A, h, anc, nc, lim, evid, suc, d, o, anom)
               for k, g, lado in (('Conservador', s['gc'], 'dn'), ('Agressivo', s['ga'], 'up'))}
        for k in res:
            if res[k]['estado'] == 'CORRIGIDO':
                res[k]['path'] = caminho(raw['Moderado'], anc, s['gm'], res[k]['g_pub'], conta)
        s['res'] = res
    por_dist = defaultdict(dict)
    for s in S:
        if (s['o'], s['m']) in HIERARQUICAS:
            por_dist[s['d']][s['o']] = s
    for dd, pr in por_dist.items():
        for s in pr.values():
            for k in ('Conservador', 'Agressivo'):
                if s['res'][k]['estado'] == 'CORRIGIDO':
                    s['res'][k].update(estado='BLOQUEADO', severidade='ALTA', g_pub=None, path=None, classe='EXTRAPOLACAO_EXTREMA_NAO_SUSTENTADA',
                                       motivo='serie hierarquica (UCBT/Consumidores): nao se recalcula; ' + s['res'][k]['motivo'])
        if len(pr) == 2:
            a, b = pr['ucbt'], pr['consumidores']
            for k in ('Conservador', 'Agressivo'):
                for x, y in ((a, b), (b, a)):
                    if x['res'][k]['estado'] == 'BLOQUEADO' and y['res'][k]['estado'] != 'BLOQUEADO':
                        y['res'][k].update(estado='BLOQUEADO', classe=x['res'][k]['classe'], severidade='ALTA', g_pub=None, path=None,
                                           motivo='bloqueado por coerencia com ' + ('UCBT' if x is a else 'Consumidores') + ' (Consumidores = UCBT + complemento): ' + x['res'][k]['motivo'])
            if a['mod_bloq'] or b['mod_bloq']:
                a['mod_bloq'] = b['mod_bloq'] = True
    inten = defaultdict(list)       # anomaly indicator: same scenario, same year (2030), other distributors
    for s in S:
        c = cons30.get(s['d'])
        if s['o'] in ('consumidores', 'ucbt') or not c:
            continue
        x = s['raw']['Agressivo'][-1]
        if x is not None:
            inten[s['o'], s['m']].append((s['d'], x / c))
    idx = {(v['DIST'], v['objetivo'], v['metrica'], v['ano'], v['cenario']): v for v in valores}
    ordem = {'ALTA': 3, 'MEDIA': 2, 'BAIXA': 1, '': 0}
    for s in S:
        r = linhas[s['i']]
        res, A = s['res'], s['A']
        bloq, corr = [], []
        r['plaus_alerta_intensidade'] = ''
        c = cons30.get(s['d'])
        if c and s['o'] not in ('consumidores', 'ucbt') and s['raw']['Agressivo'][-1] is not None:
            pares = [x for dd, x in inten.get((s['o'], s['m']), []) if dd != s['d']]
            x = s['raw']['Agressivo'][-1] / c
            if len(pares) >= 20 and x > q(pares, .99):
                r['plaus_alerta_intensidade'] = f'2030 Agressivo: {x * 1000:.1f} por mil consumidores, acima do P99 das demais ({q(pares, .99) * 1000:.1f}); indicador de anomalia, sem bloqueio'
        if s['mod_bloq']:
            r['estado_original'] = r['estado']; r['estado'] = 'BLOQUEIO_PLAUSIBILIDADE'; r['entra_em_totais'] = False
            for k in CEN:
                bloq.append(k)
                for y in YEARS:
                    x = idx[s['d'], s['o'], s['m'], y, k]; x['valor'] = ''; x['estado'] = 'BLOQUEIO_PLAUSIBILIDADE'; x['estado_cenario'] = 'BLOQUEADO'
            for k in ('Conservador', 'Agressivo'):
                res[k]['estado'] = 'BLOQUEADO'
            r['plaus_motivo'] = f"trajetoria moderada ({s['gm']:.3f} a.a.) fora do suporte empirico e determinada por evidencia nao comparavel: serie bloqueada; {s['mod_motivo']}"
            r['plaus_classe'] = s['mod_classe']
            r['plaus_severidade'] = 'ALTA'
        else:
            for k in ('Conservador', 'Agressivo'):
                rk = res[k]
                if rk['estado'] == 'BLOQUEADO':
                    bloq.append(k)
                    for y in YEARS:
                        x = idx[s['d'], s['o'], s['m'], y, k]; x['valor'] = ''; x['estado_cenario'] = 'BLOQUEADO'
                elif rk['estado'] == 'CORRIGIDO':
                    corr.append(k)
                    for i, y in enumerate(YEARS):
                        x = idx[s['d'], s['o'], s['m'], y, k]; x['valor'] = rk['path'][i]; x['estado_cenario'] = 'CORRIGIDO'
            sev = [res[k]['severidade'] for k in ('Conservador', 'Agressivo') if res[k]['severidade']]
            r['plaus_severidade'] = max(sev, key=lambda x: ordem[x]) if sev else ('BAIXA' if r['plaus_alerta_intensidade'] else '')
            cl_ = [res[k]['classe'] for k in ('Agressivo', 'Conservador') if res[k]['classe']]
            r['plaus_classe'] = cl_[0] if cl_ else ''
            r['plaus_motivo'] = ' | '.join(f"{k}: {res[k]['estado']} {res[k]['classe']} {res[k]['motivo']}" for k in ('Conservador', 'Agressivo') if res[k]['estado'] != 'ACEITO' or res[k]['severidade'])
            if s.get('mod_fora'):
                r['plaus_motivo'] = (r['plaus_motivo'] + ' | ' if r['plaus_motivo'] else '') + f"Moderado {s['gm']:.3f} a.a. acima do suporte (P99), sem janela propria equivalente: alerta, serie mantida"
                r['plaus_severidade'] = max([r['plaus_severidade'], 'MEDIA'], key=lambda x: ordem[x])
        if s['erro_calc']:
            r['plaus_classe'] = 'ERRO_DE_CALCULO'; r['plaus_severidade'] = 'ALTA'
        r['cenarios_bloqueados'] = '|'.join(bloq); r['cenarios_corrigidos'] = '|'.join(corr)
        r['plaus_json'] = json.dumps({k: {x: res[k].get(x) for x in ('estado', 'classe', 'severidade', 'motivo', 'g', 'g_pub', 'evidencias')} for k in ('Conservador', 'Agressivo')},
                                     ensure_ascii=False, default=str)
        raw = s['raw']
        a30, m30, c30_ = raw['Agressivo'][-1], raw['Moderado'][-1], raw['Conservador'][-1]
        passos = passos_comparaveis(s['h'], s['ancora'], s['nc'])
        ga_ = res['Agressivo']['g']
        cres = []
        for i in range(5):
            prev = raw['Agressivo'][i - 1] if i else A
            cres.append(round(raw['Agressivo'][i] / prev - 1, 4) if prev else None)
        audit.append(dict(DIST=s['d'], empresa=r['empresa'], objetivo=s['o'], metrica=s['m'], unidade=r['unidade'], ano_ancora=s['ancora'], estoque_ancora=A,
                          historico=json.dumps({a: v for a, v in sorted(s['h'].items())}), modelo=r['modelo_projecao'],
                          crescimento_log1p_conservador=res['Conservador']['g'], crescimento_log1p_moderado=s['gm'], crescimento_log1p_agressivo=ga_,
                          cagr_moderado=math.expm1(s['gm']), cagr_agressivo=math.expm1(ga_),
                          cresc_acum_2030_moderado=(m30 / A - 1) if A else '', cresc_acum_2030_agressivo=(a30 / A - 1) if A else '',
                          razao_agressivo_moderado=(a30 / m30) if m30 else '', razao_conservador_moderado=(c30_ / m30) if m30 else '', razao_agressivo_estoque=(a30 / A) if A else '',
                          crescimento_anual_agressivo=json.dumps(cres),
                          transicoes_comparaveis=len(passos), nivel_referencia=(s['lim'] or {}).get('nivel', ''), n_janelas_referencia=(s['lim'] or {}).get('n', ''),
                          limiar_up=(s['lim'] or {}).get('up', ''), limiar_dn=(s['lim'] or {}).get('dn', ''), limiar_p95=(s['lim'] or {}).get('p95', ''),
                          janela_recente_alta=s['w_up'] if s['w_up'] is not None else '', janela_recente_queda=s['w_dn'] if s['w_dn'] is not None else '',
                          estado_conservador=res['Conservador']['estado'], estado_agressivo=res['Agressivo']['estado'], estado_serie=r['estado'],
                          classe=r['plaus_classe'], severidade=r['plaus_severidade'], motivo=r['plaus_motivo'], alerta_intensidade=r['plaus_alerta_intensidade'],
                          evidencias=json.dumps({k: res[k].get('evidencias') for k in ('Conservador', 'Agressivo') if res[k].get('evidencias')}, ensure_ascii=False, default=str),
                          excesso_agressivo=(a30 - m30) if a30 is not None and m30 is not None else 0))
        if bloq or corr or r['plaus_severidade'] or s['erro_calc']:
            for k in CEN:
                brutos.append(dict(DIST=s['d'], empresa=r['empresa'], objetivo=s['o'], metrica=s['m'], unidade=r['unidade'], cenario=k,
                                   **{f'v{y}': raw[k][i] for i, y in enumerate(YEARS)}, estado_publicado='BLOQUEADO' if k in bloq else 'CORRIGIDO' if k in corr else 'ACEITO'))
    tot, exc = defaultdict(float), defaultdict(float)
    for a in audit:
        k = (a['objetivo'], a['metrica'])
        if a['razao_agressivo_estoque'] != '':
            tot[k] += a['razao_agressivo_estoque'] * a['estoque_ancora']
        exc[k] += max(0, a['excesso_agressivo'])
    for a in audit:
        k = (a['objetivo'], a['metrica'])
        a['participacao_total_agressivo_2030'] = (a['razao_agressivo_estoque'] * a['estoque_ancora'] / tot[k]) if tot[k] and a['razao_agressivo_estoque'] != '' else ''
        a['participacao_excesso_agressivo'] = (max(0, a['excesso_agressivo']) / exc[k]) if exc[k] else ''
    resumo = dict(series_auditadas=len(S), alertas=sum(1 for a in audit if a['severidade']),
                  por_severidade={k: sum(1 for a in audit if a['severidade'] == k) for k in ('ALTA', 'MEDIA', 'BAIXA')},
                  cenarios_bloqueados=sum(len(r['cenarios_bloqueados'].split('|')) for r in linhas if r.get('cenarios_bloqueados')),
                  cenarios_corrigidos=sum(len(r['cenarios_corrigidos'].split('|')) for r in linhas if r.get('cenarios_corrigidos')),
                  series_bloqueadas_inteiras=sum(1 for r in linhas if r['estado'] == 'BLOQUEIO_PLAUSIBILIDADE'),
                  series_com_extremo_bloqueado=sum(1 for r in linhas if r.get('cenarios_bloqueados') and r['estado'] != 'BLOQUEIO_PLAUSIBILIDADE'),
                  series_com_15_valores=sum(1 for r in linhas if r['estado'] in COB.PROJETADOS and not r.get('cenarios_bloqueados')),
                  por_classe={k: sum(1 for a in audit if a['classe'] == k) for k in CLASSES if any(a['classe'] == k for a in audit)},
                  niveis_de_referencia={n or 'sem_referencia': sum(1 for a in audit if a['nivel_referencia'] == n) for n in ('objeto_metrica_porte', 'unidade_porte', 'unidade', '')},
                  erros_de_calculo=sum(1 for a in audit if a['classe'] == 'ERRO_DE_CALCULO'))
    return linhas, valores, audit, brutos, resumo


def montar_final():
    """cobertura.montar + gate. Returns (linhas, valores, contract, suc, audit, brutos, resumo)."""
    from . import exportar_web as EW
    linhas, valores, contract, suc = COB.montar(False)
    hist, hpot, _ = EW.historicos(contract)

    def hist_fn(r):
        return sorted(hpot.get((r['DIST'], r['variante']), [])) if r['variante'] else sorted(hist.get((r['DIST'], r['objetivo'], r['metrica']), []))
    for v in valores:
        v.setdefault('estado_cenario', '')
    for r in linhas:
        for k in ('cenarios_bloqueados', 'cenarios_corrigidos', 'plaus_classe', 'plaus_severidade', 'plaus_motivo', 'plaus_json', 'plaus_alerta_intensidade'):
            r.setdefault(k, '')
    linhas, valores, audit, brutos, resumo = avaliar(linhas, valores, hist_fn)
    return linhas, valores, contract, suc, audit, brutos, resumo


def gravar(audit, brutos, resumo):
    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / 'PLAUSIBILIDADE_SERIES.csv', audit)
    write_csv(OUT / 'PLAUSIBILIDADE_ALERTAS.csv', sorted([a for a in audit if a['severidade'] or a['estado_agressivo'] != 'ACEITO' or a['estado_conservador'] != 'ACEITO'],
                                                       key=lambda a: -(a['razao_agressivo_estoque'] if a['razao_agressivo_estoque'] != '' else 0)))
    buf = io.StringIO()
    if brutos:
        w = csv.DictWriter(buf, fieldnames=list(brutos[0]), lineterminator='\n'); w.writeheader(); w.writerows(brutos)
    with gzip.GzipFile(OUT / 'PLAUSIBILIDADE_VALORES_BRUTOS.csv.gz', 'wb', mtime=0) as gz:
        gz.write(buf.getvalue().encode('utf-8'))
    atomic(OUT / 'PLAUSIBILIDADE_RESUMO.json', resumo)


def run():
    linhas, valores, contract, suc, audit, brutos, resumo = montar_final()
    gravar(audit, brutos, resumo)
    return resumo


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False, indent=1))
