"""Reconstitui somente configurações existentes e persiste trajetórias/pontos em JSON.

Os 1.504 ajustes da busca anterior NÃO são reexecutados. O reprocessamento de
configurações finais é necessário: o repositório não persiste suas trajetórias
anuais completas. Não se desserializam modelos pickle de origem externa.
"""
import csv
import json
from .fontes import C, OT, R, digest
from .qualidade import publicar


def estatisticas(pts):
    return {et: R.estat([(d, y0, y, yh) for h, o, d, y0, y, yh in pts
                        if et == 'PRODUTO' or R.etapa_de((h, o, d)) == et]) for et in ('S', 'F', 'H2', 'PRODUTO')}

def verificar_reproducao(pm, met, cen, prev):
    if cen != pm['cenarios']:
        raise ValueError('Escolha nacional não reproduzida')
    for name, item in met.items():
        # Portão congelado: WAPE absoluto deve reproduzir o produto até 1e-9.
        w = item['erros']['wape']
        expected = pm['modelos'][name]['wape']
        if (w is None) != (expected is None) or (w is not None and abs(w - expected) >= 1e-9):
            raise ValueError(f'WAPE publicado não reproduzido: {name}; atual={w}; publicado={expected}; limite_absoluto=1e-9')
    counts = slack = 0
    for d, serie in pm['series'].items():
        for side in ('conservador', 'moderado', 'agressivo'):
            if not serie.get(side):
                continue
            values = publicar(prev[cen[side]][d], pm['natureza'])
            for a, b in zip(values, serie[side]):
                delta = abs(a - b)
                if pm['natureza'] == 'discrete_count':
                    counts += 1
                    slack += delta != 0
                    if delta > 1:
                        raise ValueError(f'Trajetória publicada não reproduzida: {d}/{side}: {a} != {b}')
                elif delta > .001 + 1e-9:
                    raise ValueError(f'Trajetória contínua não reproduzida: {d}/{side}: {a} != {b}')
    if slack > C.FOLGA_MAXIMA * counts:
        raise ValueError(f'Folga de contagem excedida: {slack}/{counts}')
    return dict(escolha_identica=True, wape_na_precisao_publicada=True, contagens=counts, folga=slack)


def construir(k, pm, motor, motor_x):
    segs, bt, prev, _, _ = C.executar_metrica(motor, k)
    met, cen, _ = C.escolher_cenarios(bt, prev, segs)
    reproduction = verificar_reproducao(pm, met, cen, prev)
    cands = []
    for name, item in met.items():
        params = OT.ORIGINAIS.get(name)
        pts = [[h, o, d, dict(segs[d])[o], y, yh] for y, yh, h, o, d in (bt.get(name) or [])]
        cands.append(dict(id=name, categoria='O', algoritmo=name, parametros=params[2] if params else C.MODELOS[name],
                          variaveis=C.PAINEL.get(name, []), complexidade=C.MODELOS[name]['complexidade'],
                          trajetorias=prev.get(name, {}), pontos=pts, elegivel=item['elegivel'], motivo=item['motivo'],
                          wape=pm['modelos'][name]['wape'], estatisticas=estatisticas(pts)))
    ref = sorted({(h, o, d) for _, _, h, o, d in (bt.get('persistencia') or [])})
    for r in csv.DictReader(R.ENTRADAS['modelos_otimizacao'].open(encoding='utf-8')):
        if (r['conceito'], r['metrica']) != k or r['origem'] != 'otimizado':
            continue
        variables, hp = r['variaveis'].split('|'), json.loads(r['hiperparametros'])
        av = OT.Avaliador(motor_x, k, pm['natureza'] == 'discrete_count', {})
        S = av.avaliar(r['algoritmo'], variables, hp, 2023, 'S')
        F = av.avaliar(r['algoritmo'], variables, hp, 2024, 'F')
        ok = all(v.get('wape') is not None and r[t + '_wape'] and abs(v['wape'] - float(r[t + '_wape'])) <= 5e-7 for t, v in [('S', S), ('F', F)])
        pr = R.Painel(motor_x, k, variables, lambda X, g: OT.ajustar(r['algoritmo'], hp, X, g))
        points, reason = R.backtest(segs, pr, ref)
        traj = pr(C.BASE, {d: s for d, s in segs.items() if len(s) >= 3}, 5) or {}
        eligible, why, _ = R.plausivel_metrica(traj, segs)
        pts = [[h, o, d, *v] for (h, o, d), v in (points or {}).items()]
        stats = estatisticas(pts)
        cands.append(dict(id=r['modelo'], categoria='X', algoritmo=r['algoritmo'], parametros=hp,
                          variaveis=variables, complexidade=C.MODELOS[r['referencia']]['complexidade'] + .5,
                          trajetorias=traj, pontos=pts, elegivel=bool(eligible and points and ok),
                          motivo='REPRODUCAO_FALHOU' if not ok else why or reason,
                          reproducao=dict(ok=bool(ok), S=S.get('wape'), F=F.get('wape')),
                          wape=stats['PRODUTO'].get('wape'), estatisticas=stats))
    mod = next(c for c in cands if c['id'] == cen['moderado'])
    for c in cands:
        c['competitivo'] = False
        if c['id'] == mod['id']:
            c['rejeicao'] = 'MODERADO_PUBLICADO'
        elif not c['elegivel'] or not c['pontos']:
            c['rejeicao'] = c['motivo'] or 'SEM_EVIDENCIA'
        else:
            limit = mod['wape'] if c['categoria'] == 'O' else mod['estatisticas']['PRODUTO']['wape']
            ok = c['wape'] <= C.TOLERANCIA_ERRO * limit
            guard = c['categoria'] == 'O' or c['estatisticas']['F']['wape'] <= C.TOLERANCIA_ERRO * mod['estatisticas']['F']['wape']
            c['competitivo'] = bool(ok and guard)
            c['rejeicao'] = None if c['competitivo'] else ('WAPE_ACIMA_DA_TOLERANCIA' if not ok else 'GUARDA_F_REPROVADA')
        c['origens'] = dict(selecao=2023, comparacao_consultada=2024, projecao=2025, horizonte=C.HORIZONTE)
        c['hash_configuracao'] = digest({n: c[n] for n in ('id', 'algoritmo', 'parametros', 'variaveis', 'origens')})
    return dict(candidatos=cands, reproducao=reproduction)
