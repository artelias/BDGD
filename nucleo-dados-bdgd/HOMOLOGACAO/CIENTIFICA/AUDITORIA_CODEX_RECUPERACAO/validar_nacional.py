"""Validação independente de um produto nacional da recuperação (saída do pacote do Codex).

Uso: python validar_nacional.py <dir_execucao> <saida_json> [modo]

Verifica, com código próprio (as regras sobre valores publicados de `verificar_publicado.avaliar`):
  V1  Moderado, histórico e N/D idênticos ao produto público da RC, série a série;
  V2  todo extremo publicado passa nas regras sobre valores publicados (ordem nos 5 anos, Q1–Q4, Q7, Q8, Q9);
  V3  contrato físico: contagens inteiras, km/kVA com até 3 decimais, nada negativo ou não finito;
  V4  nenhum extremo sem Moderado; nenhum modelo fora do modo; categorias coerentes com o modo;
  V5  modelo de cada extremo competitivo: WAPE_PRODUTO ≤ 1,25 × WAPE do Moderado (O pelo publicado);
  V6  cenarios.csv igual a produto.json (5 anos, 3 cenários, modelos e categorias);
  V7  kVA marcado EXPERIMENTAL_KVA; nenhum total novo;
  V8  classe da série coerente com os extremos presentes.
"""
import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).parent))
from verificar_publicado import C, avaliar, transicoes_percentis  # noqa: E402

ORIGINAIS = set(C.MODELOS)
MODO_CATEGORIAS = {'originais': {'A_PUBLICADO_MANTIDO', 'A_ORIGINAL'},
                   'otimizados': {'A_PUBLICADO_MANTIDO', 'A_ORIGINAL', 'A_OTIMIZADO'},
                   'condicionais': {'A_PUBLICADO_MANTIDO', 'A_ORIGINAL', 'A_OTIMIZADO', 'B_HIST'}}


def main(execucao, saida, modo='originais'):
    execucao = Path(execucao).resolve()
    prod = json.loads((execucao / 'produto.json').read_text(encoding='utf-8'))
    inv = {(m['conceito'], m['metrica']): {c['id']: c for c in m['candidatos']} for m in json.loads((execucao / 'inventario.json').read_text(encoding='utf-8'))}
    pub = json.loads((RAIZ / 'web/public/data/previsoes/cenarios-motor.json').read_text(encoding='utf-8'))
    pubm = {(m['conceito'], m['metrica']): m for m in pub['metricas']}
    series, _, _ = C.carregar_contrato(RAIZ / 'output-historico/contrato-integracao')
    pot, _ = C.carregar_potencia(RAIZ / 'motor_cenarios/entrada', series)
    series.update(pot)
    falhas, cont = [], Counter()
    def falha(v, k, d, msg):
        falhas.append(dict(verificacao=v, chave='/'.join(k) + '/' + d, detalhe=msg))
    csvv = {}
    for r in csv.DictReader((execucao / 'cenarios.csv').open(encoding='utf-8')):
        csvv[(r['CONCEITO_ID'], r['METRICA'], r['DIST'], r['cenario'])] = r
    for m in prod['metricas']:
        k = (m['conceito'], m['metrica'])
        pm = pubm[k]
        disc = m['natureza'] == 'discrete_count'
        p01, p99 = transicoes_percentis(series, k)
        cand = inv[k]
        wmod = pm['modelos'][pm['cenarios']['moderado']]['wape'] if pm['cenarios']['moderado'] else None
        if set(m['series']) != set(pm['series']):
            falha('V1', k, '*', 'conjunto de DIST difere')
        for d, s in m['series'].items():
            p = pm['series'][d]
            cont['series'] += 1
            for campo in ('moderado', 'hist', 'erro_moderado'):
                if s.get(campo) != p.get(campo):
                    falha('V1', k, d, f'{campo} alterado')
            M = s.get('moderado')
            hist = s.get('hist') or []
            y25 = hist[-1][1] if hist and hist[-1][0] == C.BASE else None
            presentes = []
            for lado in ('conservador', 'agressivo'):
                E, ex = s.get(lado), (s.get('extremos') or {}).get(lado)
                if bool(E) != bool(ex):
                    falha('V4', k, d, f'{lado}: trajetória e metadado inconsistentes')
                if not E:
                    continue
                presentes.append(lado)
                cont['extremos'] += 1
                if not M:
                    falha('V4', k, d, f'{lado} sem Moderado')
                    continue
                estado, regras, _, _ = avaliar(E, M, y25, lado, disc, p01, p99)
                cont['estado_' + estado] += 1
                if estado != 'APROVADO':
                    falha('V2', k, d, f'{lado}: {estado} {regras}')
                if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or x < 0 for x in E):
                    falha('V3', k, d, f'{lado}: valor inválido')
                if disc and any(type(x) is not int for x in E):
                    falha('V3', k, d, f'{lado}: contagem não inteira')
                if not disc and any(abs(x - round(x, 3)) > 1e-9 for x in E):
                    falha('V3', k, d, f'{lado}: mais de 3 decimais')
                cat = ex['categoria']
                cont['categoria_' + cat] += 1
                if cat not in MODO_CATEGORIAS[modo]:
                    falha('V4', k, d, f'{lado}: categoria {cat} fora do modo {modo}')
                if modo == 'originais' and ex['modelo'] not in ORIGINAIS:
                    falha('V4', k, d, f'{lado}: modelo {ex["modelo"]} não original')
                if cat == 'A_PUBLICADO_MANTIDO' and (ex['modelo'] != pm['cenarios'][lado] or E != p.get(lado)):
                    falha('V4', k, d, f'{lado}: publicado mantido difere do publicado')
                if cat.startswith('A_') and cat != 'A_PUBLICADO_MANTIDO':
                    c = cand[ex['modelo']]
                    w = pm['modelos'][c['id']]['wape'] if c['categoria'] == 'O' else c['wape']
                    lim = wmod if c['categoria'] == 'O' else cand[pm['cenarios']['moderado']]['estatisticas']['PRODUTO']['wape']
                    if not (c['competitivo'] and w <= C.TOLERANCIA_ERRO * lim + 1e-15):
                        falha('V5', k, d, f'{lado}: {c["id"]} não competitivo')
                for cen, vals in (('moderado', M), (lado, E)):
                    r = csvv.get((k[0], k[1], d, cen))
                    if r is None or [r[str(a)] for a in C.HORIZONTE] != [str(v) for v in vals]:
                        falha('V6', k, d, f'{cen}: CSV difere do JSON')
                if (csvv.get((k[0], k[1], d, lado)) or {}).get('modelo_serie') != ex['modelo']:
                    falha('V6', k, d, f'{lado}: modelo no CSV difere')
            esperado = 'SEM_PREVISAO' if not M else 'PARCIAL' if len(presentes) < 2 else None
            if esperado and s['completude'] != esperado or not esperado and not s['completude'].startswith('COMPLETA'):
                falha('V8', k, d, f'classe {s["completude"]} incoerente')
            cont['classe_' + s['completude']] += 1
            if k[1] == 'potencia_kva' and s['estado_cientifico'] != 'EXPERIMENTAL_KVA':
                falha('V7', k, d, 'kVA sem marca experimental')
    res = dict(execucao=str(execucao.relative_to(RAIZ)), modo=modo, contagens=dict(sorted(cont.items())),
               falhas_por_verificacao=dict(Counter(f['verificacao'] for f in falhas)), falhas=falhas[:200], aprovado=not falhas)
    Path(saida).parent.mkdir(parents=True, exist_ok=True)
    Path(saida).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({k: v for k, v in res.items() if k != 'falhas'}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main(*sys.argv[1:])
