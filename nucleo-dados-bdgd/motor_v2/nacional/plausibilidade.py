"""Plausibility gate of the 2026-2030 scenarios (release candidate 1.0), read only on the national results.

    python -m motor_v2.nacional.plausibilidade

Why: the scenario engine (cenarios.scenarios) moves the annual log1p growth of the moderate path to the lowest / highest annual
growth observed in the series' own comparable transitions and COMPOUNDS it for five years. A single cadastral step on a tiny base
(0 -> 66 towers; 3 -> 70 sectionalizers) therefore becomes x10^9 by 2030. The engine screen (cenarios.classify) removes a
transition only when the cross-section proves it atypical AND persistent; first entries from zero and one-year steps in the last
year are never confirmed. This gate does not retrain or change the engine: it audits every projected series, and for each extreme
scenario decides ACEITO, CORRIGIDO (alternative rule, below) or BLOQUEADO, keeping the original values in a research artifact.

Thresholds come from the data of the run itself (no physical or arbitrary cap), pooled over every projected series:
  * L_up / L_dn: 99th / 1st percentile of the ANNUALISED growth over 2- and 3-year windows (what a series has sustained), by size
    class of the starting stock (<10, 10-99, 100-999, >=1000). A 5-year compounding at a rate beyond what 99% of the windows ever
    sustained has no empirical support. P95 is the alert level; the p90 of one-year steps is the "relevant step" of a window.
  * Peer ceiling: no distributor may end 2030 with more units per consumer than the maximum seen in 2022-2025 among the OTHER
    distributors (same object and metric). It catches absurd levels that the growth rate alone cannot (towers > consumers).
Decision for an extreme scenario with annual growth g (Agressivo upward, Conservador downward):
  1. within [L_dn, L_up] and under the peer ceiling -> ACEITO (alert BAIXA when beyond P95);
  2. beyond L: if the series itself sustained a growth in its most recent 2-3 years (window ending at the anchor, every one-year step
     >= the relevant step, no non-comparable transition), the extreme is CORRIGIDO to that demonstrated rate (classe
     PLAUSIVEL_COM_EVIDENCIA); otherwise it is BLOQUEADO with the cause: RUPTURA_CADASTRAL (first entry from zero, fase4 evidence of
     cadastral change, or >= 3 asset types of the DIST jumping in the same year), MUDANCA_DE_PERIMETRO (succession event),
     BASE_HISTORICA_PEQUENA (previous stock < 10), HISTORICO_INSUFICIENTE (<= 1 comparable transition) or
     EXTRAPOLACAO_EXTREMA_NAO_SUSTENTADA;
  3. a corrected or accepted path above the peer ceiling is BLOQUEADO.
A moderate path beyond L that is not sustained the same way blocks the whole series (BLOQUEIO_PLAUSIBILIDADE). Hierarchical series
(UCBT and Consumidores, Consumidores = UCBT + complement) are only blocked, never recomputed, and a block on one blocks both.
Blocked values are never published; they stay in PLAUSIBILIDADE_VALORES_BRUTOS.csv.gz for audit."""
import csv
import gzip
import io
import json
import math
from collections import defaultdict
from pathlib import Path

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
MIN_AMOSTRA = 40
lg = math.log1p


def cl(stock):
    s = stock or 0
    return 0 if s < 10 else 1 if s < 100 else 2 if s < 1000 else 3


def q(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, max(0, int(len(v) * p)))]


def limiares(series):
    """Pooled thresholds from every projected series: {class: dict(up, dn, p95, passo)} and the sample sizes."""
    jan, passos = defaultdict(list), defaultdict(list)
    for s in series:
        h = s['h']
        for span in (2, 3):
            for y in range(2022 + span, 2026):
                a, b = h.get(y - span), h.get(y)
                if a is not None and b is not None and a > 0:
                    jan[cl(a)].append((lg(b) - lg(a)) / span)
        for y in range(2023, 2026):
            a, b = h.get(y - 1), h.get(y)
            if a is not None and b is not None and a > 0:
                passos[cl(a)].append(lg(b) - lg(a))
    todos = [x for v in jan.values() for x in v]
    tp = [x for v in passos.values() for x in v]
    out = {}
    for c in range(4):
        j = jan[c] if len(jan[c]) >= MIN_AMOSTRA else todos
        p = passos[c] if len(passos[c]) >= MIN_AMOSTRA else tp
        out[c] = dict(up=q(j, .99), dn=q(j, .01), p95=q(j, .95), passo=q(p, .90), n_janelas=len(jan[c]), n_passos=len(passos[c]))
    return out


def passos_validos(h, ancora, excl):
    """[(year, previous stock, log1p growth)] of the comparable one-year steps up to the anchor (value on both ends, previous > 0)."""
    out = []
    for y in range(2023, (ancora or 2025) + 1):
        a, b = h.get(y - 1), h.get(y)
        if a is not None and b is not None and y not in excl:
            out.append((y, a, lg(b) - lg(a)))
    return out


def janela_recente(h, ancora, excl, passo_min, L):
    """Annualised growth the series itself sustained in the window ending at the anchor (3 then 2 years), or None.
    Requires every one-year step >= passo_min, a positive start and no excluded (non-comparable) transition. The longer window wins."""
    for span in (3, 2):
        ys = range(ancora - span + 1, ancora + 1)
        if ancora - span < 2022 or any(y in excl for y in ys):
            continue
        a, b = h.get(ancora - span), h.get(ancora)
        if a is None or b is None or a <= 0:
            continue
        steps = [lg(h[y]) - lg(h[y - 1]) for y in ys if h.get(y) is not None and h.get(y - 1) is not None]
        if len(steps) == span and all(x >= passo_min for x in steps):
            return (lg(b) - lg(a)) / span
    return None


def serie_f(linha, h, dec):
    return dict(hist=h, ancora=int(linha['ano_ancora']) if linha['ano_ancora'] else None)


def causa(linha, h, dec, g_ext, anomalias, lim, evid, suc, dist, objetivo):
    """-> (classe, motivo, evidencias) of the transition that determines g_ext."""
    excl = {x['ano'] for x in json.loads(dec.get('cenario_transicoes_atipicas_excluidas') or '[]')} if isinstance(dec.get('cenario_transicoes_atipicas_excluidas'), str) and (dec.get('cenario_transicoes_atipicas_excluidas') or '').startswith('[') else set()
    anc = int(linha['ano_ancora'])
    det = None
    for y in range(2023, anc + 1):
        a, b = h.get(y - 1), h.get(y)
        if a is not None and b is not None and abs((lg(b) - lg(a)) - g_ext) < 1e-6:
            det = (y, a, b); break
    ev = dict(transicao=None, passos_validos=len(passos_validos(h, anc, excl)))
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
    if ev['passos_validos'] <= 1:
        return 'HISTORICO_INSUFICIENTE', 'no maximo uma transicao comparavel na serie', ev
    return 'EXTRAPOLACAO_EXTREMA_NAO_SUSTENTADA', 'taxa acima do que 99% das janelas de 2-3 anos jamais sustentaram, sem sustentacao recente na propria serie', ev


def avaliar(linhas, valores, hist_fn, evid=None, suc=None):
    """Applies the gate. Returns (linhas, valores, auditoria rows, brutos rows, resumo). Mutates linhas/valores in place."""
    evid = evid if evid is not None else evidence()
    suc = suc if suc is not None else {k: v for k, v in elegibilidade.sucessoes().items()}
    decB = {(int(r['DIST']), r['conceito']): r for r in COB._csv(ROOT_OUT / 'distribuidora' / 'DECISOES_B.csv')}
    decA = {(int(r['DIST']), r['ativo'], r['metrica']): r for r in COB._csv(ROOT_OUT / 'projecao' / 'DECISOES_A.csv')}
    decP = {(int(r['DIST']), r['conceito']): r for r in COB._csv(ROOT_OUT / 'distribuidora_potencia' / 'DECISOES_B.csv')}
    vals = defaultdict(dict)
    for v in valores:
        if v['valor'] != '':
            vals[v['DIST'], v['objetivo'], v['metrica']][v['cenario'], v['ano']] = float(v['valor'])
    S = []
    for i, r in enumerate(linhas):
        if r['estado'] not in COB.PROJETADOS or (r['DIST'], r['objetivo'], r['metrica']) not in vals:
            continue
        d, o, m = r['DIST'], r['objetivo'], r['metrica']
        h = {a: v for a, v, _ in hist_fn(r)}
        h = {a: v for a, v in h.items() if v is not None}
        dec = (decP.get((d, r['variante'])) if r['variante'] else decB.get((d, o)) if r['fonte'] == 'nivel_B' else
               decA.get((d, 'ucbt', 'quantidade')) if r['fonte'] == 'consumidores_reconciliado' else decA.get((d, o, m))) or {}
        if not dec:
            continue
        S.append(dict(i=i, row=r, d=d, o=o, m=m, h=h, dec=dec, v=vals[d, o, m], ancora=int(r['ano_ancora']), A=float(r['valor_ancora'])))
    L = limiares(S)
    # peer ceiling: units per consumer, same object and metric, other distributors
    cons = {s['d']: s['h'] for s in S if s['o'] == 'consumidores'}
    cons30 = {s['d']: s['v'].get(('Moderado', 2030)) for s in S if s['o'] == 'consumidores'}
    inten = defaultdict(list)
    for s in S:
        if s['o'] in ('consumidores', 'ucbt'):
            continue
        for y, v in s['h'].items():
            c = cons.get(s['d'], {}).get(y)
            if c and c > 0:
                inten[s['o'], s['m']].append((s['d'], v / c))
    teto = {}
    for k, lst in inten.items():
        teto[k] = lst
    for s in S:        # peers' moderate 2030 intensity joins the ceiling (same horizon, no unfair comparison with the past)
        c = cons30.get(s['d'])
        if s['o'] not in ('consumidores', 'ucbt') and c and c > 0 and s['v'].get(('Moderado', 2030)) is not None:
            teto.setdefault((s['o'], s['m']), []).append((s['d'], s['v'][('Moderado', 2030)] / c))
    def teto_par(o, m, d):
        xs = [x for dd, x in teto.get((o, m), []) if dd != d]
        return max(xs) if xs else None
    # systemic jumps: asset types of one DIST above P95 in one year
    anom = defaultdict(int)
    for s in S:
        for y, a, g in passos_validos(s['h'], s['ancora'], set()):
            if a > 0 and g > L[cl(a)]['p95']:
                anom[s['d'], y] += 1
    audit, brutos, mudou = [], [], {}
    for s in S:
        r, d, o, m, h, dec, v, anc = s['row'], s['d'], s['o'], s['m'], s['h'], s['dec'], s['v'], s['ancora']
        try:
            gc, gm, ga = (float(dec['cenario_crescimento_log1p_' + k]) for k in ('conservador', 'moderado', 'agressivo'))
        except (KeyError, ValueError):
            continue
        ex = dec.get('cenario_transicoes_atipicas_excluidas') or ''
        excl = {x['ano'] for x in json.loads(ex)} if ex.startswith('[') else set()
        c = cl(s['A'])
        lim = L[c]
        A = s['A']
        raw = {k: [v.get((k, y)) for y in YEARS] for k in CEN}
        # calculation check: the published extreme path must follow the engine formula from the moderate path
        erro_calc = False
        if r['fonte'] != 'consumidores_reconciliado':       # the reconciled path is UCBT + complement, not the engine formula
            conta = r['natureza'] == 'discrete_count'
            for k, g in (('Conservador', gc), ('Agressivo', ga)):
                for i, y in enumerate(YEARS):
                    z = lg(raw['Moderado'][i]) + (y - anc) * (g - gm)
                    esp = math.expm1(z) if z > 0 else 0.0
                    tol = max(2.0, 0.01 * esp) if conta else max(1e-3 * esp, 1e-3)
                    if abs(raw[k][i] - esp) > tol:
                        erro_calc = True
        w_rec = janela_recente(h, anc, excl, lim['passo'], L)
        res = {}
        mod_bloq = False
        # moderate path
        if gm > lim['up'] or gm < lim['dn']:
            if w_rec is None:
                mod_bloq = True
        # extremes
        for k, g, lado in (('Conservador', gc, 'dn'), ('Agressivo', ga, 'up')):
            extremo = (g - gm) > 1e-9 if lado == 'up' else (gm - g) > 1e-9
            if not extremo:
                res[k] = dict(estado='ACEITO', classe='', severidade='', motivo='sem extremo alem do moderado (cenario degenerado, registrado)', g=g, g_pub=g)
                continue
            fora = g > lim['up'] if lado == 'up' else g < lim['dn']
            alerta = g > lim['p95'] if lado == 'up' else False
            est, classe, sev, mot, gpub, evid_ = 'ACEITO', '', ('BAIXA' if alerta else ''), 'dentro do suporte empirico (taxa <= P99 sustentado do porte)', g, {}
            if fora:
                if w_rec is not None and ((w_rec >= gm) if lado == 'up' else (w_rec <= gm)):
                    est, classe, sev, gpub = 'CORRIGIDO', 'PLAUSIVEL_COM_EVIDENCIA', 'MEDIA', w_rec
                    mot = f'taxa extrema {g:.3f} a.a. reduzida a {w_rec:.3f} a.a., o crescimento que a propria serie sustentou nos ultimos anos (passos >= {lim["passo"]:.3f})'
                else:
                    classe, mot, evid_ = causa(r, h, dec, g, anom, lim, evid, suc, d, o)
                    est, sev, gpub = 'BLOQUEADO', 'ALTA', None
            res[k] = dict(estado=est, classe=classe, severidade=sev, motivo=mot, g=g, g_pub=gpub, evidencias=evid_)
        # path recomputation + peer ceiling
        for k in CEN:
            if k == 'Moderado':
                continue
            rk = res[k]
            if rk['estado'] == 'CORRIGIDO':
                path = []
                for i, y in enumerate(YEARS):
                    z = lg(raw['Moderado'][i]) + (y - anc) * (rk['g_pub'] - gm)
                    x = math.expm1(z) if z > 0 else 0.0
                    path.append(round_count(x) if r['natureza'] == 'discrete_count' else round(x, 6))
                rk['path'] = path
            elif rk['estado'] == 'ACEITO':
                rk['path'] = raw[k]
        # peer ceiling on each extreme path: other distributors' maximum units per consumer, observed 2022-2025 or projected (moderate) for 2030
        c30 = cons30.get(d) or (cons.get(d, {}).get(2025))
        pc = teto_par(o, m, d) if o not in ('consumidores', 'ucbt') else None
        if pc and c30:
            for k in ('Conservador', 'Agressivo'):
                rk = res[k]
                if rk['estado'] in ('ACEITO', 'CORRIGIDO') and rk.get('path') and rk['path'][-1] / c30 > pc and rk['path'][-1] > raw['Moderado'][-1]:
                    cls_, mot_, ev_ = causa(r, h, dec, rk['g'], anom, L[c], evid, suc, d, o)
                    rk.update(estado='BLOQUEADO', classe=cls_, severidade='ALTA', g_pub=None, path=None, evidencias=ev_,
                              motivo=f'2030 = {raw[k][-1] / c30 * 1000:.1f} por mil consumidores, acima do maximo de qualquer outra distribuidora ({pc * 1000:.1f}); ' + mot_)
        s['res'], s['mod_bloq'], s['raw'], s['erro_calc'], s['lim'], s['w_rec'], s['gm'] = res, mod_bloq, raw, erro_calc, lim, w_rec, gm
    # hierarchical series: block only, and a block on UCBT blocks Consumidores of the same DIST (and vice versa)
    por_dist = defaultdict(dict)
    for s in S:
        if (s['o'], s['m']) in HIERARQUICAS:
            por_dist[s['d']][s['o']] = s
    for dd, pr in por_dist.items():
        for s in pr.values():
            for k in ('Conservador', 'Agressivo'):
                if s['res'][k]['estado'] == 'CORRIGIDO':     # never recompute a hierarchical series: keep the engine value or block
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
    # apply to linhas / valores and build the audit
    idx = {(v['DIST'], v['objetivo'], v['metrica'], v['ano'], v['cenario']): v for v in valores}
    for s in S:
        r = linhas[s['i']]
        res, A = s['res'], s['A']
        bloq, corr = [], []
        if s['mod_bloq']:
            r['estado_original'] = r['estado']; r['estado'] = 'BLOQUEIO_PLAUSIBILIDADE'; r['entra_em_totais'] = False
            for k in CEN:
                bloq.append(k)
                for y in YEARS:
                    idx[s['d'], s['o'], s['m'], y, k]['valor'] = ''; idx[s['d'], s['o'], s['m'], y, k]['estado'] = 'BLOQUEIO_PLAUSIBILIDADE'; idx[s['d'], s['o'], s['m'], y, k]['estado_cenario'] = 'BLOQUEADO'
            r['plaus_motivo'] = 'trajetoria moderada fora do suporte empirico e sem sustentacao recente: serie bloqueada'
            r['plaus_classe'] = 'EXTRAPOLACAO_EXTREMA_NAO_SUSTENTADA' if s['gm'] > 0 else 'HISTORICO_INSUFICIENTE'
            r['plaus_severidade'] = 'ALTA'
            for k in ('Conservador', 'Agressivo'):
                res[k]['estado'] = 'BLOQUEADO'
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
            ordem = {'ALTA': 3, 'MEDIA': 2, 'BAIXA': 1, '': 0}
            r['plaus_severidade'] = max(sev, key=lambda x: ordem[x]) if sev else ''
            cl_ = [res[k]['classe'] for k in ('Agressivo', 'Conservador') if res[k]['classe'] and res[k]['estado'] != 'ACEITO']
            r['plaus_classe'] = cl_[0] if cl_ else ''
            r['plaus_motivo'] = ' | '.join(f"{k}: {res[k]['estado']} {res[k]['classe']} {res[k]['motivo']}" for k in ('Conservador', 'Agressivo') if res[k]['estado'] != 'ACEITO' or res[k]['severidade'])
        if s['erro_calc']:
            r['plaus_classe'] = 'ERRO_DE_CALCULO'; r['plaus_severidade'] = 'ALTA'
        r['cenarios_bloqueados'] = '|'.join(bloq); r['cenarios_corrigidos'] = '|'.join(corr)
        r['plaus_json'] = json.dumps({k: {x: res[k].get(x) for x in ('estado', 'classe', 'severidade', 'motivo', 'g', 'g_pub', 'evidencias')} for k in ('Conservador', 'Agressivo')}, ensure_ascii=False, default=str)
        # audit row (all series)
        a30 = s['raw']['Agressivo'][-1]; m30 = s['raw']['Moderado'][-1]; c30_ = s['raw']['Conservador'][-1]
        passos = passos_validos(s['h'], s['ancora'], set())
        audit.append(dict(DIST=s['d'], empresa=r['empresa'], objetivo=s['o'], metrica=s['m'], unidade=r['unidade'], ano_ancora=s['ancora'], estoque_ancora=A,
                          historico=json.dumps({a: v for a, v in sorted(s['h'].items())}), modelo=r['modelo_projecao'],
                          crescimento_log1p_conservador=res['Conservador']['g'], crescimento_log1p_moderado=s['gm'], crescimento_log1p_agressivo=res['Agressivo']['g'],
                          cagr_moderado=math.expm1(s['gm']) if s['gm'] > -1 else '', cagr_agressivo=math.expm1(res['Agressivo']['g']),
                          cresc_acum_2030_moderado=(m30 / A - 1) if A else '', cresc_acum_2030_agressivo=(a30 / A - 1) if A else '',
                          razao_agressivo_moderado=(a30 / m30) if m30 else '', razao_conservador_moderado=(c30_ / m30) if m30 else '', razao_agressivo_estoque=(a30 / A) if A else '',
                          anual_agressivo=json.dumps([round(s['raw']['Agressivo'][i] / (s['raw']['Agressivo'][i - 1] if i else A) - 1, 4) if (s['raw']['Agressivo'][i - 1] if i else A) else None for i in range(5)]),
                          transicoes_comparaveis=len(passos), limiar_up=s['lim']['up'], limiar_dn=s['lim']['dn'], limiar_p95=s['lim']['p95'], passo_relevante=s['lim']['passo'],
                          janela_recente_sustentada=s['w_rec'] if s['w_rec'] is not None else '',
                          estado_conservador=res['Conservador']['estado'], estado_agressivo=res['Agressivo']['estado'], estado_serie=r['estado'],
                          classe=r['plaus_classe'], severidade=r['plaus_severidade'], motivo=r['plaus_motivo'],
                          evidencias=json.dumps({k: res[k].get('evidencias') for k in ('Conservador', 'Agressivo') if res[k].get('evidencias')}, ensure_ascii=False, default=str),
                          excesso_agressivo=a30 - m30))
        if bloq or corr or r['plaus_severidade'] or s['erro_calc']:
            for k in CEN:
                brutos.append(dict(DIST=s['d'], empresa=r['empresa'], objetivo=s['o'], metrica=s['m'], cenario=k, **{f'v{y}': s['raw'][k][i] for i, y in enumerate(YEARS)},
                                   estado_publicado='BLOQUEADO' if (k in bloq) else 'CORRIGIDO' if k in corr else 'ACEITO'))
    # shares
    tot = defaultdict(float); exc = defaultdict(float)
    for a in audit:
        tot[a['objetivo'], a['metrica']] += a['razao_agressivo_estoque'] * a['estoque_ancora'] if a['estoque_ancora'] else 0
        exc[a['objetivo'], a['metrica']] += max(0, a['excesso_agressivo'])
    for a in audit:
        k = (a['objetivo'], a['metrica'])
        a['participacao_total_agressivo_2030'] = (a['razao_agressivo_estoque'] * a['estoque_ancora'] / tot[k]) if tot[k] and a['estoque_ancora'] else ''
        a['participacao_excesso_agressivo'] = (max(0, a['excesso_agressivo']) / exc[k]) if exc[k] else ''
    resumo = dict(series_auditadas=len(S), limiares={str(c): L[c] for c in L},
                  alertas=sum(1 for a in audit if a['severidade']), por_severidade={k: sum(1 for a in audit if a['severidade'] == k) for k in ('ALTA', 'MEDIA', 'BAIXA')},
                  cenarios_bloqueados=sum(len(r['cenarios_bloqueados'].split('|')) for r in linhas if r.get('cenarios_bloqueados')),
                  cenarios_corrigidos=sum(len(r['cenarios_corrigidos'].split('|')) for r in linhas if r.get('cenarios_corrigidos')),
                  series_bloqueadas_inteiras=sum(1 for r in linhas if r['estado'] == 'BLOQUEIO_PLAUSIBILIDADE'),
                  series_com_extremo_bloqueado=sum(1 for r in linhas if r.get('cenarios_bloqueados') and r['estado'] != 'BLOQUEIO_PLAUSIBILIDADE'),
                  por_classe={k: sum(1 for a in audit if a['classe'] == k) for k in CLASSES if any(a['classe'] == k for a in audit)},
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
        for k in ('cenarios_bloqueados', 'cenarios_corrigidos', 'plaus_classe', 'plaus_severidade', 'plaus_motivo', 'plaus_json'):
            r.setdefault(k, '')
    linhas, valores, audit, brutos, resumo = avaliar(linhas, valores, hist_fn)
    return linhas, valores, contract, suc, audit, brutos, resumo


def run():
    linhas, valores, contract, suc, audit, brutos, resumo = montar_final()
    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / 'PLAUSIBILIDADE_SERIES.csv', audit)
    write_csv(OUT / 'PLAUSIBILIDADE_ALERTAS.csv', sorted([a for a in audit if a['severidade'] or a['estado_agressivo'] != 'ACEITO' or a['estado_conservador'] != 'ACEITO'],
                                                       key=lambda a: -(a['razao_agressivo_estoque'] or 0)))
    buf = io.StringIO()
    if brutos:
        w = csv.DictWriter(buf, fieldnames=list(brutos[0]), lineterminator='\n'); w.writeheader(); w.writerows(brutos)
    with gzip.GzipFile(OUT / 'PLAUSIBILIDADE_VALORES_BRUTOS.csv.gz', 'wb', mtime=0) as gz:
        gz.write(buf.getvalue().encode('utf-8'))
    atomic(OUT / 'PLAUSIBILIDADE_RESUMO.json', resumo)
    return resumo


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False, indent=1))
