"""Seleção por DIST: precedência P1, P2, P4; Moderado permanece byte a byte."""
import copy
import math
from collections import defaultdict
import numpy as np
from .fontes import C, R, digest
from .qualidade import LADOS, checar, classe, publicar

MODOS = {'originais': {'O'}, 'otimizados': {'O', 'X'}, 'condicionais': {'O', 'X'}}


def selecionar(pm, bundle, series, modo, proveniencia):
    if modo not in MODOS:
        raise ValueError('Modo experimental desconhecido')
    if C.mc.nature_of(pm['unidade']) != pm['natureza']:
        raise ValueError('Unidade incompatível com a natureza física')
    out = copy.deepcopy(pm)
    k = pm['conceito'], pm['metrica']
    candidates = bundle['candidatos']
    byid = {c['id']: c for c in candidates}
    mod_id = pm['cenarios']['moderado']
    trans = R.transicoes(series, k, C.BASE)
    gs = [g for _, _, g in trans]
    ps = np.percentile(gs, [1, 99, 5, 95]).tolist() if len(gs) >= 20 else [None] * 4
    p01, p99, p05, p95 = ps
    bydist = defaultdict(list)
    for d, _, g in trans:
        bydist[d].append(g)
    audit = []
    for d, old in sorted(pm['series'].items(), key=lambda x: int(x[0])):
        s = out['series'][d]
        s['anteriores'] = {l: old.get(l) for l in (*LADOS, 'moderado')}
        s['extremos'] = {}
        s['motivos_experimentais'] = {}
        s['hash_proveniencia'] = digest({'execucao': proveniencia, 'chave': [*k, d], 'modo': modo})
        s['estado_cientifico'] = 'EXPERIMENTAL_KVA' if k[1] == 'potencia_kva' else 'EXPLORATORIO_RETROSPECTIVO_2025_CONSULTADO'
        s['historico_contrato'] = {str(y): list(v) for y, v in sorted(series[k].get(d, {}).items())}
        Mpub = old.get('moderado')
        M = byid[mod_id]['trajetorias'].get(d) if mod_id else None
        y25 = old['hist'][-1][1] if old['hist'] and old['hist'][-1][0] == 2025 else None
        for lado in LADOS:
            s[lado] = None
            s['extremos'][lado] = None
            attempts = []
            def attempt(c, stage, E, Epub=None, permitido=True):
                if Epub is None and E and all(math.isfinite(v) and v >= 0 for v in E):
                    Epub = publicar(E, pm['natureza'])
                state, q = checar(E, Epub, M, Mpub, y25, lado, pm['natureza'] == 'discrete_count', p01, p99)
                local = [p for p in c.get('pontos', []) if p[2] == d]
                wlocal = R.estat([(p[2], *p[3:]) for p in local]).get('wape')
                if not permitido:
                    state = 'REJEITADO'
                a = dict(DIST=d, CONCEITO_ID=k[0], METRICA=k[1], lado=lado, modelo=c['id'], etapa=stage,
                         elegivel=c.get('elegivel', True), competitivo=c.get('competitivo', True), estado=state,
                         regras=q, trajetoria=Epub, wape_dist=wlocal, hash_configuracao=c['hash_configuracao'],
                         origem_projecao=2025, selecionado=False,
                         motivo_rejeicao=c.get('rejeicao') if not permitido else state if state!='COERENTE' else None)
                attempts.append((a, c))
                return a
            if not Mpub:
                s['motivos_experimentais'][lado] = 'H:SEM_MODERADO'
                continue
            if not M:
                raise ValueError(f'Moderado sem trajetória contínua: {k}/{d}')
            if old.get(lado):
                c = byid[pm['cenarios'][lado]]
                attempt(c, 'P1', c['trajetorias'].get(d), old[lado])
            eligible = sorted((c for c in candidates if c['categoria'] in MODOS[modo] and c['competitivo']),
                              key=lambda c: (c['wape'], c['complexidade'], c['id']))
            for c in eligible:
                attempt(c, 'P2', c['trajetorias'].get(d))
            for c in candidates:
                if c['id'] != mod_id and c['categoria'] in MODOS[modo] and not c['competitivo']:
                    attempt(c, 'P2', c['trajetorias'].get(d), permitido=False)
            if modo == 'condicionais':
                g = min(bydist[d]) if lado == 'conservador' and bydist[d] else max(bydist[d]) if bydist[d] else None
                if len(bydist[d]) >= 2 and p05 is not None and p05 <= g <= p95:
                    conditional = dict(id='B_HIST', categoria='B', parametros={'g': g}, variaveis=['transicoes_comparaveis_2022_2025'],
                                       algoritmo='repeticao_crescimento_historico', wape=None, estatisticas={},
                                       hash_configuracao=digest({'regra': 'B_HIST', 'g': g, 'protocolo': R.PROTOCOLO}))
                    attempt(conditional, 'P4', [y25 * math.exp(h * g) for h in range(1, 6)])
            chosen = next(((a, c) for a, c in attempts if a['estado'] == 'COERENTE'), None)
            if chosen:
                a, c = chosen
                a['selecionado'] = True
                cat = 'A_PUBLICADO_MANTIDO' if a['etapa'] == 'P1' else 'B_HIST' if a['etapa'] == 'P4' else 'A_ORIGINAL' if c['categoria'] == 'O' else 'A_OTIMIZADO'
                s[lado] = a['trajetoria']
                s['extremos'][lado] = dict(modelo=c['id'], categoria=cat, regra='serie_a_serie', etapa=a['etapa'],
                    natureza='condicional' if cat == 'B_HIST' else 'independente', algoritmo=c['algoritmo'],
                    parametros=c['parametros'], variaveis=c['variaveis'], origem=2025, horizonte=C.HORIZONTE,
                    wape_referencia=byid[mod_id]['wape'], wape_candidato=c['wape'], wape_dist=a['wape_dist'],
                    escopo_wape='PRODUTO_metrica', r2_crescimento=c['estatisticas'].get('F', {}).get('r2_crescimento'),
                    escopo_r2='F_metrica_2025_consultado', regras=a['regras'], hash_configuracao=c['hash_configuracao'],
                    hash_proveniencia=s['hash_proveniencia'])
                s['motivos_experimentais'][lado] = 'PUBLICADO_APROVADO' if a['etapa'] == 'P1' else 'RECUPERADO_' + a['etapa']
            else:
                states = [a['estado'] for a, _ in attempts]
                precedence = R.PREC_ESTADO
                best = min((v for v in states if v in precedence), key=precedence.index, default=None)
                reason = R.CAUSA_DE_ESTADO[best] if best else 'B' if any(c['elegivel'] for c in candidates if c['id'] != mod_id) else 'A1'
                s['motivos_experimentais'][lado] = reason + ':' + (best or 'SEM_CANDIDATO_COMPETITIVO')
            audit.extend(a for a, _ in attempts)
        s['completude'] = classe(s)
    return out, audit
