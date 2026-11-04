"""Compact, pre-computed product of the Motor V2 for the dashboard (homologation build only), read only.

    python -m motor_v2.nacional.exportar_web --saida <repo>/nucleo-dados-bdgd/web/data-motor-v2

Writes indice.json (catalogue, states, coverage, totals with their PARCIAL/COMPLETO label, limitations) and dist/<DIST>.json
(every objective x metric of one DIST: state and reason, observed history with its contract state, chosen model, baselines and
errors, the 15 scenario values, scenario metadata). Nothing is trained here, except one documented exception: the coefficients of
the linear models of Level B were not persisted by the national run, so they are recovered by refitting the same deterministic
selection on the same pool and are published ONLY when the refit reproduces the stored moderate path (otherwise N/D with the
reason). Missing values stay null (never 0); a zero is published only when the contract says zero_verificado.

The folder is NOT public: web/scripts/motor-v2-gate.mjs copies it into public/ only for a homologation build
(NEXT_PUBLIC_MOTOR_V2=homologacao or a Vercel preview). Production stays behind the final authorization gate."""
import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

from . import CONTRACT, GROUPS, ROOT_OUT
from . import cobertura as COB
from ..runner import digest

SCHEMA = 'motor-v2-homologacao/1'
LIMITACOES = [
    'Resultados experimentais internos em homologação: nenhum modelo é cientificamente homologado.',
    'Há apenas 2 origens temporais independentes (2023 e 2024) e nenhuma é point-in-time elegível; a regra exige 3.',
    'Horizontes acima de 1 ano não foram validados retrospectivamente; 2027–2030 são extrapolações com fórmula explícita.',
    'Conservador e Agressivo são hipóteses de crescimento extremo observado na própria série, não intervalos de confiança.',
    'Totais que não cobrem todas as DIST do universo ou todo o estoque de 2025 são rotulados PARCIAL.',
    'Publicações extraordinárias nunca entram automaticamente; só a publicação ordinária selecionada no contrato.',
    'Séries com âncora anterior a 2025 (SEM_ANCORA_2025) nunca entram em totais que exigem âncora 2025.',
    'Potência própria e passante de reguladores não são somáveis: não há total nacional de potência de reguladores.',
]
ROTULOS = {
    'PROJETADA_EXPERIMENTAL': ('Projetada · modelo escolhido', 'Modelo escolhido pela comparação retrospectiva (ML ou tendência) com âncora 2025.'),
    'PROJETADA_BASELINE': ('Projetada · baseline', 'Baseline por política (persistência, deriva ou CAGR) com âncora 2025: nenhum modelo superou o baseline de forma estável.'),
    'SEM_ANCORA_2025': ('Projetada · âncora anterior', 'Projeção interna a partir da última competência utilizável anterior a 2025; fora dos totais.'),
    'HISTORICO_INSUFICIENTE': ('Histórico insuficiente', 'Há estoque, mas não há trajetória definida.'),
    'DADO_NAO_HOMOLOGADO': ('Dado não homologado', 'Há registro, mas ele não passa as regras do contrato ou de consistência física.'),
    'SEM_PUBLICACAO': ('Sem publicação', 'A distribuidora não tem publicação localizada nas competências.'),
    'SUCESSAO_SOCIETARIA': ('Sucessão societária', 'O código não é perímetro independente (incorporado ou reportado por outra DIST).'),
    'NAO_APLICAVEL': ('Não aplicável', 'O ativo não existe na distribuidora ou a métrica não tem sentido físico.'),
    'SEM_SEMANTICA_FISICA_HOMOGENEA': ('Sem semântica física homogênea', 'O campo mistura grandezas físicas diferentes.'),
    'BLOQUEIO_PLAUSIBILIDADE': ('Bloqueada · plausibilidade', 'A trajetória moderada não é sustentada por evidência comparável; nenhum cenário é publicado como previsão utilizável. O valor original fica só no artefato de auditoria.'),
    'BLOQUEIO_TECNICO': ('Bloqueio técnico', 'Limitação do código; deve ser zero.'),
}
BASELINES = ('persistencia', 'deriva', 'cagr')


def _csv(p):
    return COB._csv(p)


def _n(v):
    x = COB._num(v)
    return None if x is None or (isinstance(x, float) and not math.isfinite(x)) else x


def _r(v, nd=4):
    x = _n(v)
    return None if x is None else round(x, nd)


def _inteiro(v, onde):
    """Contagem física publicada como inteiro JSON (123, nunca 123.0). Valor fracionário é erro de contrato, não é arredondado aqui."""
    if v is None:
        return None
    if isinstance(v, bool) or not float(v).is_integer() or v < 0:
        raise ValueError(f'contagem fracionaria ou negativa em {onde}: {v!r}')
    return int(v)


def contagens_inteiras(serie):
    """Histórico, âncora e cenários de uma série de contagem saem como inteiros; extensão e potência ficam como estão."""
    if serie['natureza'] != 'discrete_count':
        return serie
    onde = f"{serie['objetivo']}/{serie['metrica']}"
    serie['historico'] = [[a, _inteiro(v, f'{onde}/{a}'), e] for a, v, e in serie['historico']]
    serie['valor_ancora'] = _inteiro(serie['valor_ancora'], f'{onde}/ancora')
    if serie['cenarios']:
        serie['cenarios'] = {c: None if xs is None else [_inteiro(x, f'{onde}/{c}') for x in xs] for c, xs in serie['cenarios'].items()}
    return serie


def completude(serie):
    """Quantos dos três cenários a série publica e, para cada um que falta, o motivo. COMPLETA = os três com os 5 anos;
    PARCIAL = Moderado publicado sem um ou os dois extremos; SEM_PREVISAO = nenhum cenário publicável (estado da série explica)."""
    cen = serie['cenarios'] or {}
    pub = [c for c in COB.CENARIOS if cen.get(c) and all(v is not None for v in cen[c])]
    pl = (serie.get('plausibilidade') or {}).get('cenarios') or {}
    falta = {c: (pl.get(c) or {}).get('motivo') or serie['motivo'] for c in COB.CENARIOS if c not in pub}
    estado = 'COMPLETA' if len(pub) == 3 else 'PARCIAL' if 'Moderado' in pub else 'SEM_PREVISAO'
    if estado == 'SEM_PREVISAO' and pub:
        raise ValueError(f"cenario extremo sem Moderado em {serie['objetivo']}/{serie['metrica']}: {pub}")
    return dict(estado=estado, publicados=pub, nao_publicados=falta)


def agregado_extremos(series, total_2030):
    """Total nacional de um cenário extremo = soma dos extremos individuais das séries do conjunto comum: não é um cenário nacional
    (as distribuidoras não atingem o extremo ao mesmo tempo). Compara o crescimento anual implícito de cada total com o crescimento
    nacional observado no MESMO conjunto de séries (anos em que todas têm valor). Fora da faixa observada => alerta, sem teto arbitrário."""
    conj = [x for x in series if x['entra_em_totais'] and x['completude_cenarios']['estado'] == 'COMPLETA']
    if not conj or not total_2030:
        return None
    # crescimento nacional encadeado: em cada transição t−1→t, só as séries do conjunto com valor nos dois anos (mesma coorte)
    val = [{a: v for a, v, _ in x['historico'] if v is not None} for x in conj]
    gs = []
    for t in (2023, 2024, 2025):
        a = sum(h[t - 1] for h in val if t - 1 in h and t in h); b = sum(h[t] for h in val if t - 1 in h and t in h)
        if a > 0 and b > 0:
            gs.append(math.log(b / a))
    base = sum(h[2025] for h in val if 2025 in h) if all(2025 in h for h in val) else None
    if not gs or not base:
        return dict(n_series=len(conj), motivo='sem historico nacional comparavel no conjunto comum')
    g = {c: math.log(total_2030[c] / base) / 5 if total_2030.get(c) and total_2030[c] > 0 else None for c in COB.CENARIOS}
    acima = g['Agressivo'] is not None and g['Agressivo'] > max(gs)
    abaixo = g['Conservador'] is not None and g['Conservador'] < min(gs)
    return dict(n_series=len(conj), estoque_2025=base, crescimento_nacional_observado_min=round(min(gs), 6), crescimento_nacional_observado_max=round(max(gs), 6),
                transicoes_observadas=len(gs), crescimento_implicito={c: None if v is None else round(v, 6) for c, v in g.items()},
                agressivo_acima_do_observado=acima, conservador_abaixo_do_observado=abaixo, alerta=acima or abaixo)


def historicos(contract):
    """{(DIST, objective, metric): [[year, value|null, state]]} for the contract concepts, the power stocks and the Level A assets."""
    h = defaultdict(list)
    for (d, c, y), r in sorted(contract.items()):
        v = r['valor']
        h[d, c, r['metrica']].append([y, float(v) if v != '' and r['estado'] in ('observado', 'zero_verificado') else None, r['estado'] + (':' + r['tipo_lacuna'] if r['tipo_lacuna'] else '')])
    pot = {'trafo_forca_kva': ('trafo_forca', 'potencia_kva'), 'reguladores_kva_propria': ('reguladores', 'potencia_kva'), 'reguladores_kva_passante': ('reguladores', 'potencia_kva')}
    hp = defaultdict(list)
    for r in _csv(ROOT_OUT / 'distribuidora_potencia' / 'ESTOQUES_POTENCIA_B.csv'):
        hp[int(r['DIST']), r['conceito']].append([int(r['ano']), _n(r['valor']) if r['utilizavel'] == 'True' else None, 'utilizavel' if r['utilizavel'] == 'True' else (r['motivo'] or 'nao_utilizavel')])
    a = {'ucbt_quantidade': ('ucbt', 'quantidade'), 'trafo_dist_potencia_kva': ('trafo_dist', 'potencia_kva')}
    for r in _csv(ROOT_OUT / 'final' / 'INVENTARIO_NACIONAL.csv'):
        if r['nivel'] == 'A_territorial' and r['ativo'] in a:
            h[(int(r['DIST']),) + a[r['ativo']]].append([int(r['ano']), _n(r['valor']) if r['status'] == 'extraido' else None, r['status']])
    return h, hp, pot


def candidatos(path):
    """{(DIST, concept): {candidate: metrics}} of Level B (baselines and ML) with the retrospective errors."""
    out = defaultdict(dict)
    for r in _csv(path):
        if r['origens'] in ('', '0'):
            continue
        out[int(r['DIST']), r['conceito']][r['candidato']] = dict(mae=_r(r['mae']), rmse=_r(r['rmse']), wape=_r(r['wape'], 6), vies=_r(r['vies']),
                                                                    origens=int(r['origens']), previsoes=int(r['previsoes'] or 0),
                                                                    mae_por_origem=json.loads(r['mae_por_origem'] or '{}'))
    return out


def erros_reconciliados():
    """{DIST: (errors of the reconciled path, baselines)} from the end-to-end cells (origins 2023 and 2024, horizon 1)."""
    by = defaultdict(list)
    for r in _csv(ROOT_OUT / 'hierarquia_consumidores' / 'ERRO_RETROSPECTIVO_CONSUMIDORES_CELULAS.csv'):
        by[int(r['DIST'])].append(r)
    def m(rows, pre):
        e = [_n(r[pre + '_erro']) for r in rows]; a = [_n(r['real_consumidores']) for r in rows]
        if any(x is None for x in e) or not rows:
            return None
        return dict(mae=round(sum(abs(x) for x in e) / len(e), 4), rmse=round(math.sqrt(sum(x * x for x in e) / len(e)), 4),
                    wape=round(sum(abs(x) for x in e) / sum(a), 6) if sum(a) else None, vies=round(sum(e) / len(e), 4), origens=len(rows),
                    previsoes=len(rows), mae_por_origem={r['origem']: abs(_n(r[pre + '_erro'])) for r in rows})
    def b_indep(rows):      # only the absolute error of the independent B choice is recorded per cell
        e = [_n(r['B_escolhido_erro_abs']) for r in rows]; a = sum(_n(r['real_consumidores']) or 0 for r in rows)
        if not rows or any(x is None for x in e):
            return None
        return dict(mae=round(sum(e) / len(e), 4), rmse=round(math.sqrt(sum(x * x for x in e) / len(e)), 4), wape=round(sum(e) / a, 6) if a else None,
                    vies=None, origens=len(rows), previsoes=len(rows))
    return {d: (m(rr, 'E2E_reconciliado_escolhido'), {'persistencia': m(rr, 'E2E_persistencia'), 'B_independente': b_indep(rr)}) for d, rr in by.items()}


def coeficientes(series):
    """Refit of the Level B linear models (same pool, same inner selection) -> {(DIST, concept): coefficient record}; published only
    when the refit moderate path equals the stored one (relative difference <= 1e-9)."""
    from . import distribuidora as B
    from .cenarios import ml_path
    if not series:
        return {}
    cells, meta = B.load()
    grp, _ = B.groups()
    concepts = sorted(k for k in meta if isinstance(k, str))
    rows = B.panel(cells, concepts, sorted({d for d, _, _ in cells}))
    out = {}
    for (d, c), (model, scope, anchor, moderado) in series.items():
        try:
            prow = dict(B.row(cells, d, c, anchor + 1), y=None)
            tr, why = B.pool(rows, c, d, anchor, scope, grp, prow)
            if why:
                raise ValueError(why)
            feats, p, how, _ = B.select(rows, c, d, anchor, scope, model, grp, prow)
            g = B.fit_predict(model, p, feats, tr, [prow])[0]
            path = ml_path(cells[d, c, anchor]['value'], B.level(cells[d, c, anchor]['value'], g), anchor)
            ok = all(abs(path[y] - moderado[y]) <= 1e-9 * max(1.0, abs(moderado[y])) for y in moderado)
            if not ok:
                out[d, c] = dict(status='N/D', motivo='o reajuste nao reproduziu a trajetoria armazenada (versao de biblioteca ou dados); coeficientes nao publicados')
                continue
            import numpy as np
            trc = [r for r in tr if all(r['x'][i] is not None for i in feats)]
            X = np.array([[r['x'][i] for i in feats] for r in trc]); gg = np.array([B.lg(r['y']) - B.lg(r['stock']) for r in trc])
            m = B.build(model, p); m.fit(X, np.exp(gg) if model == 'poisson' else gg)
            sc, est = m.named_steps['scale'], m.named_steps['model']
            beta = est.coef_ / sc.scale_
            b0 = float(est.intercept_ - float(np.sum(est.coef_ * sc.mean_ / sc.scale_)))
            out[d, c] = dict(status='recuperado_e_verificado', forma='d = b0 + soma(b_i * x_i)' + (' (log da media de Poisson)' if model == 'poisson' else ''),
                             intercepto=round(b0, 8), termos=[dict(variavel=B.FEATURES[i], coeficiente=round(float(b), 8), valor_na_ancora=_r(prow['x'][i], 6))
                                                               for i, b in zip(feats, beta)],
                             padronizados=[dict(variavel=B.FEATURES[i], coeficiente=round(float(b), 8)) for i, b in zip(feats, est.coef_)],
                             parametros=p, selecao=how, linhas_treino=len(trc), dist_no_pool=len({r['dist'] for r in trc}), crescimento_log1p_um_passo=round(g, 8))
        except ValueError as e:
            out[d, c] = dict(status='N/D', motivo=f'reajuste impossivel: {e}')
    return out


MECANISMO = {
    'random_forest': 'Random Forest: media de 64 arvores de regressao (profundidade 3, folha >= 2) sobre o crescimento log1p; nao ha equacao linear nem coeficientes.',
    'hist_gradient_boosting': 'HistGradientBoosting: soma de 80 arvores rasas ajustadas em sequencia (7 folhas, taxa 0,1); nao ha equacao linear nem coeficientes.',
    'persistencia': 'Persistencia: y(T+h) = y(T).',
    'deriva': 'Deriva: y(T+h) = y(T) + h x inclinacao media do segmento comparavel terminado em T.',
    'cagr': 'CAGR: y(T+h) = y(T) x g^h, g = taxa geometrica do segmento comparavel.',
}
for _m in ('ols', 'ridge', 'elastic_net', 'poisson'):
    MECANISMO[_m] = f'{_m}: d = b0 + soma(b_i x_i) sobre as features em T; y(T+h) = expm1(log1p y(T) + h x d) (passo mantido constante: nao ha covariaveis futuras).'


def run(saida):
    saida = Path(saida)
    (saida / 'distribuidoras').mkdir(parents=True, exist_ok=True)
    from . import plausibilidade as PL
    linhas, valores, contract, suc, audit, brutos, plres = PL.montar_final()
    COB.PLAUS_RESUMO = plres
    res = COB.resumo(linhas, valores, contract)
    hist, hpot, _ = historicos(contract)
    candB = candidatos(ROOT_OUT / 'distribuidora' / 'RESULTADOS_CANDIDATOS_B.csv')
    candP = candidatos(ROOT_OUT / 'distribuidora_potencia' / 'RESULTADOS_CANDIDATOS_B.csv')
    decB = {(int(r['DIST']), r['conceito']): r for r in _csv(ROOT_OUT / 'distribuidora' / 'DECISOES_B.csv')}
    decP = {(int(r['DIST']), r['conceito']): r for r in _csv(ROOT_OUT / 'distribuidora_potencia' / 'DECISOES_B.csv')}
    decA = {(int(r['DIST']), r['ativo'], r['metrica']): r for r in _csv(ROOT_OUT / 'projecao' / 'DECISOES_A.csv')}
    vals = defaultdict(dict)
    for v in valores:
        if v['valor'] != '':
            vals[v['DIST'], v['objetivo'], v['metrica']].setdefault(v['cenario'], {})[v['ano']] = v['valor']
    lin = {}
    for r in linhas:
        if r['fonte'] == 'nivel_B' and r['estado'] in COB.PROJETADOS and ':' in (r['modelo_projecao'] or '') and r['modelo_projecao'].split(':')[0] in ('ols', 'ridge', 'elastic_net', 'poisson'):
            lin[r['DIST'], r['objetivo']] = (r['modelo_projecao'].split(':')[0], r['modelo_projecao'].split(':')[1], int(r['ano_ancora']), None)
    # the stored moderate path is rounded for counts: compare with the unrounded internal values
    import pyarrow.parquet as pq
    bruto = defaultdict(dict)
    for p in pq.read_table(ROOT_OUT / 'distribuidora' / 'PROJECOES_B_INTERNO.parquet', columns=['DIST', 'conceito', 'ano', 'cenario', 'valor_bruto']).to_pylist():
        if p['cenario'] == 'Moderado':
            bruto[p['DIST'], p['conceito']][p['ano']] = p['valor_bruto']
    lin = {k: (a, b, c, bruto[k]) for k, (a, b, c, _) in lin.items() if k in bruto}
    coefs = coeficientes(lin)
    e2e = erros_reconciliados()
    por_dist = defaultdict(list)
    for r in linhas:
        d, o, m = r['DIST'], r['objetivo'], r['metrica']
        modelo = r['modelo_projecao'] or None
        mid = (modelo or '').split(':')[0] if modelo else None
        dec = (decP.get((d, r['variante'])) if r['variante'] else decB.get((d, o)) if r['fonte'] in ('nivel_B', 'consumidores_reconciliado') else
               decA.get((d, 'ucbt' if o == 'ucbt' else o, m)) if r['fonte'] == 'nivel_A' else None) or {}
        if r['variante']:
            h = sorted(hpot.get((d, r['variante']), []))
        else:
            h = sorted(hist.get((d, o, m), []))
        cands = (candP.get((d, r['variante'])) if r['variante'] else candB.get((d, o)) if r['fonte'] in ('nivel_B', 'consumidores_reconciliado') else None) or {}
        escolhido = cands.get(modelo) if modelo else None
        bl = {b: cands[b] for b in BASELINES if b in cands}
        if r['fonte'] == 'consumidores_reconciliado':      # errors of the reconciled path itself, not of the independent B series
            er, eb = e2e.get(d, (None, {}))
            escolhido, bl = er, {k: v for k, v in eb.items() if v}
        best_b = min(bl.items(), key=lambda kv: (kv[1]['mae'] is None, kv[1]['mae'] or 0))[0] if bl else None
        e = escolhido or (dict(mae=_r(r['mae']), rmse=_r(r['rmse']), wape=_r(r['wape'], 6), vies=_r(r['vies']), origens=int(r['origens'] or 0))
                          if r['mae'] != '' and r['fonte'] != 'consumidores_reconciliado' else None)
        ganho = None
        if e and best_b and e.get('mae') is not None and bl[best_b]['mae']:
            ganho = round(1 - e['mae'] / bl[best_b]['mae'], 6)
        projetada = r['estado'] in COB.PROJETADOS
        serie = dict(
            objetivo=o, metrica=m, nome=r['nome'], familia=r['familia'], unidade=r['unidade'], natureza=r['natureza'], variante=r['variante'] or None,
            estado=r['estado'], classe=r['classe_auditoria'] or None, motivo=(r['plaus_motivo'] if r['estado'] == 'BLOQUEIO_PLAUSIBILIDADE' else r['motivo']), fonte=r['fonte'],
            plausibilidade=(dict(severidade=r['plaus_severidade'] or None, classe=r['plaus_classe'] or None, motivo=r['plaus_motivo'] or None, alerta_intensidade=r['plaus_alerta_intensidade'] or None,
                                 cenarios=json.loads(r['plaus_json'])) if r['plaus_json'] and (r['plaus_severidade'] or r['cenarios_bloqueados'] or r['cenarios_corrigidos']) else None),
            historico=h, ancora=int(r['ano_ancora']) if r['ano_ancora'] else None, horizonte_real=r['horizonte_real'] or None,
            valor_ancora=_n(r['valor_ancora']), entra_em_totais=bool(r['entra_em_totais']),
            modelo=None if not projetada else dict(
                id=modelo, algoritmo=mid, escopo=modelo.split(':')[1] if modelo and ':' in modelo else ('individual' if mid in BASELINES else None),
                tipo='baseline' if mid in BASELINES else 'reconciliacao' if r['fonte'] == 'consumidores_reconciliado' else 'ml',
                base_da_projecao=r['base_da_projecao'] or None, mecanismo=MECANISMO.get(mid) if mid else None,
                justificativa=dec.get('motivo_experimental') if r['base_da_projecao'] == 'melhor_modelo_experimental' else
                '; '.join(x for x in (dec.get('motivo_fallback'), f"ML nao escolhido: {dec['motivo_experimental']}" if dec.get('motivo_experimental') else None) if x) or None,
                nota=dec.get('nota_projecao') or None, melhor_baseline=r['melhor_baseline'] or None, melhor_ml=r['melhor_ml'] or None,
                homologado=False, motivo_nao_homologado=dec.get('motivo_nao_homologado') or '2 origens independentes < 3 exigidas; point-in-time sem vintage comprovada',
                coeficientes=coefs.get((d, o)) if r['fonte'] == 'nivel_B' and mid in ('ols', 'ridge', 'elastic_net', 'poisson') else
                (dict(status='N/D', motivo='modelo nao parametrico: sem coeficientes; ver mecanismo') if mid in ('random_forest', 'hist_gradient_boosting') else
                 dict(status='N/D', motivo='baseline sem coeficientes estimados; formula no mecanismo') if mid in BASELINES else
                 dict(status='N/D', motivo='coeficientes nao persistidos para este nivel'))),
            erros=e, baselines=bl or None, melhor_baseline_medido=best_b, ganho_vs_melhor_baseline=ganho,
            cenarios={s: ([vals[d, o, m].get(s, {}).get(y) for y in COB.YEARS] if s not in r['cenarios_bloqueados'].split('|') else None) for s in COB.CENARIOS} if projetada else None,
            cenarios_status={s: ('BLOQUEADO' if s in r['cenarios_bloqueados'].split('|') else 'CORRIGIDO' if s in r['cenarios_corrigidos'].split('|') else 'ACEITO') for s in COB.CENARIOS} if projetada else None,
            cenarios_meta=None if not projetada else dict(
                degenerados=dec.get('cenario_cenarios_degenerados') == 'True', piso_zero=dec.get('cenario_piso_zero_aplicado') == 'True',
                crescimento_log1p={k: _r(dec.get('cenario_crescimento_log1p_' + k), 6) for k in ('conservador', 'moderado', 'agressivo')},
                transicoes_historicas=int(dec['cenario_transicoes_historicas']) if dec.get('cenario_transicoes_historicas') not in (None, '') else None,
                transicoes_atipicas_excluidas=json.loads(dec['cenario_transicoes_atipicas_excluidas']) if dec.get('cenario_transicoes_atipicas_excluidas', '').startswith('[') else [],
                regra='Moderado = trajetoria do modelo; Conservador/Agressivo = crescimento log1p anual minimo/maximo das transicoes comparaveis da propria serie quando mais extremo que o moderado; senao coincidem (degeneracao registrada).'),
        )
        serie = contagens_inteiras(serie)
        serie['completude_cenarios'] = completude(serie)
        por_dist[d].append(serie)
    empresas = {r['DIST']: r['empresa'] for r in linhas}
    grupos_cfg = json.loads(Path(GROUPS).read_text(encoding='utf-8'))
    grupo_de = {r['DIST']: r['grupo'] for r in linhas}
    for d, ss in por_dist.items():
        (saida / 'distribuidoras' / f'{d}.json').write_text(json.dumps(dict(schema=SCHEMA, dist=d, empresa=empresas[d], grupo=grupo_de[d] or None, series=ss),
                                                             ensure_ascii=False, separators=(',', ':'), allow_nan=False), encoding='utf-8')
    comp = defaultdict(lambda: dict(COMPLETA=0, PARCIAL=0, SEM_PREVISAO=0))
    for ss in por_dist.values():
        for x in ss:
            if x['estado'] in COB.PROJETADOS or x['estado'] == 'BLOQUEIO_PLAUSIBILIDADE':
                comp[x['objetivo'], x['metrica']][x['completude_cenarios']['estado']] += 1
    por_obj = defaultdict(list)
    for ss in por_dist.values():
        for x in ss:
            por_obj[x['objetivo'], x['metrica']].append(x)
    objetivos = []
    for p in res['por_objetivo']:
        cat = next(c for c in COB.catalogo() if c['objetivo'] == p['objetivo'] and c['metrica'] == p['metrica'])
        objetivos.append(dict(objetivo=p['objetivo'], metrica=p['metrica'], nome=cat['nome'], familia=cat['familia'], unidade=p['unidade'], natureza=cat['natureza'],
                              no_catalogo=cat['no_catalogo'], estados={k: p[k] for k in COB.ESTADOS if p[k]}, series_com_15_valores=p['series_com_15_valores'],
                              cobertura_estoque_2025=_r(p['cobertura_estoque_2025'], 6), rotulo_total=p['rotulo_total'] or None, observacao=p['observacao'] or None,
                              total_2030={s: _r(p['total_2030_' + s.lower()], 3) for s in COB.CENARIOS} if p['rotulo_total'] else None,
                              n_series_total={s: p['n_series_total_' + s.lower()] for s in COB.CENARIOS} if p['rotulo_total'] else None,
                              total_2030_moderado_todas=_r(p['total_2030_moderado_todas_as_series'], 3) if p['rotulo_total'] else None, n_series_moderado_todas=p['n_series_moderado_todas'] if p['rotulo_total'] else None,
                              series_com_cenario_bloqueado=p['series_com_cenario_bloqueado'], series_com_cenario_corrigido=p['series_com_cenario_corrigido'],
                              completude_cenarios=dict(comp[p['objetivo'], p['metrica']])))
        objetivos[-1]['agregado_extremos'] = agregado_extremos(por_obj.get((p['objetivo'], p['metrica']), []), objetivos[-1]['total_2030']) if p['rotulo_total'] else None
        if cat['natureza'] == 'discrete_count':
            o = objetivos[-1]
            for k in ('total_2030',):
                if o[k]:
                    o[k] = {c: _inteiro(v, f"total {p['objetivo']}/{c}") for c, v in o[k].items()}
            o['total_2030_moderado_todas'] = _inteiro(o['total_2030_moderado_todas'], f"total {p['objetivo']}")
    indice = dict(schema=SCHEMA, status_publicacao='HOMOLOGACAO_EXPERIMENTAL_NAO_PUBLICAVEL_EM_PRODUCAO', contrato_sha256=digest(CONTRACT),
                  anos_historicos=[2022, 2023, 2024, 2025], anos_projecao=list(COB.YEARS), cenarios=list(COB.CENARIOS),
                  estados={k: dict(rotulo=v[0], descricao=v[1], com_valores=k in COB.PROJETADOS) for k, v in ROTULOS.items()},
                  objetivos=objetivos, grupos={g['grupo_id']: g['nome'] for g in grupos_cfg['grupos']},
                  dists=[dict(dist=d, empresa=empresas[d], grupo=grupo_de[d] or None, projetadas=sum(1 for s in por_dist[d] if s['estado'] in COB.PROJETADOS),
                              series=len(por_dist[d])) for d in sorted(por_dist)],
                  plausibilidade=plres,
                  resumo={k: res[k] for k in ('universo', 'cobertura_processamento', 'cobertura_previsao', 'estados', 'combinacoes_objetivo_metrica_com_previsao',
                                                'dist_com_alguma_projecao', 'bloqueio_tecnico', 'classes_auditoria')},
                  coeficientes=dict(recuperados=sum(1 for v in coefs.values() if v['status'] == 'recuperado_e_verificado'), tentados=len(coefs)),
                  limitacoes=LIMITACOES)
    (saida / 'indice.json').write_text(json.dumps(indice, ensure_ascii=False, separators=(',', ':'), allow_nan=False), encoding='utf-8')
    return dict(dist=len(por_dist), series=sum(len(v) for v in por_dist.values()), coeficientes=indice['coeficientes'],
                bytes=sum(p.stat().st_size for p in saida.rglob('*.json')))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--saida', required=True)
    print(json.dumps(run(ap.parse_args().saida), ensure_ascii=False))
