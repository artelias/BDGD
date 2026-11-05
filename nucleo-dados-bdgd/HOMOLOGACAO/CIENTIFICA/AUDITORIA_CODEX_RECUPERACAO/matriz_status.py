"""Matriz de status por modelo e métrica: APROVADO, REPROVADO, BLOQUEADO, EXPERIMENTAL.

Uso: python matriz_status.py <saida_csv>

Status de **prontidão para integração como fonte de cenário por série** (não é homologação científica;
2025 já foi consultado e 2026–2030 não são homologáveis). Regras, na ordem:
  Moderado publicado ......................... APROVADO (preservado), ou EXPERIMENTAL se kVA
  sem evidência ou sem contrato DIST ......... BLOQUEADO
  não elegível ou não competitivo ............ REPROVADO
  resultado definido por desempate (KNN) ..... BLOQUEADO
  escolha por série muda sob ruído realista .. BLOQUEADO
  métrica em kVA ............................. EXPERIMENTAL
  otimizado (X), B-HIST, N1/N2/N5 ............ EXPERIMENTAL (decisões D4, D5, D7)
  original competitivo, reproduzido, estável . APROVADO
"""
import csv
import glob
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
EXP = RAIZ / 'motor_cenarios/experimental/recuperacao'
REF03 = RAIZ / 'HOMOLOGACAO/CIENTIFICA/RECUPERACAO_CENARIOS/03_INVENTARIO_MODELOS_EXISTENTES.csv'
KNN_EMPATE = {('chaves', 'quantidade'), ('consumidores', 'quantidade'), ('geradores', 'quantidade')}


def uso(modo):
    prod = json.loads((EXP / f'win-nacional-{modo}/produto.json').read_text(encoding='utf-8'))
    c = Counter()
    for m in prod['metricas']:
        for s in m['series'].values():
            for lado, e in (s.get('extremos') or {}).items():
                if e:
                    c[(m['conceito'], m['metrica'], e['modelo'], lado)] += 1
    return c


def main(saida):
    pub = json.loads((RAIZ / 'web/public/data/previsoes/cenarios-motor.json').read_text(encoding='utf-8'))
    pubm = {(m['conceito'], m['metrica']): m for m in pub['metricas'] if m['series']}
    inv = {(m['conceito'], m['metrica']): {c['id']: c for c in m['candidatos']}
           for m in json.loads((EXP / 'win-nacional-originais/inventario.json').read_text(encoding='utf-8'))}
    uso_o, uso_x, uso_b = uso('originais'), uso('otimizados'), uso('condicionais')
    real = defaultdict(lambda: dict(dif_wape=0.0, mudancas=0))
    for f in sorted(glob.glob(str(AQUI / '04_sensibilidade/SENSIBILIDADE_*.json'))):
        nome = Path(f).stem.replace('SENSIBILIDADE_', '')
        if not (nome == 'libm' or nome.startswith('ruido')):
            continue
        d = json.loads(Path(f).read_text(encoding='utf-8'))
        for k, v in d['metricas'].items():
            for mo, x in v['dif_wape'].items():
                real[(k, mo)]['dif_wape'] = max(real[(k, mo)]['dif_wape'], x)
        cs = Path(f).with_suffix('.csv')
        if cs.exists():
            for r in csv.DictReader(cs.open(encoding='utf-8')):
                if r['modelo_ref'] != r['modelo'] or r['classe_ref'] != r['classe']:
                    for mo in {r['modelo_ref'], r['modelo']} - {''}:
                        real[(r['conceito'] + '/' + r['metrica'], mo)]['mudancas'] += 1
    sx = {(r['conceito'], r['metrica'], r['modelo']): r for r in csv.DictReader((AQUI / '04_sensibilidade/SENSIBILIDADE_X.csv').open(encoding='utf-8'))}
    linhas = []
    for r in csv.DictReader(REF03.open(encoding='utf-8')):
        k = (r['conceito'], r['metrica'])
        if k not in pubm:
            continue
        pm = pubm[k]
        kva = k[1] == 'potencia_kva'
        cand, cat, classe = r['candidato'], r['categoria'], r['classe']
        mod = pm['cenarios']['moderado']
        wm = pm['modelos'][mod]['wape'] if mod else None
        linha = dict(conceito=k[0], metrica=k[1], unidade=pm['unidade'], candidato=cand, categoria=cat, algoritmo=r['algoritmo'],
                     papel='MODERADO' if cand == mod else 'CONDICIONAL' if cat in ('B-HIST', 'N5', 'N6') else 'NOVO_CONGELADO' if cat == 'N' else 'EXTREMO_POR_SERIE',
                     wape_produto=r['wape_produto'], razao_wape_moderado=round(float(r['wape_produto']) / wm, 4) if r['wape_produto'] and wm else '',
                     classe_referencia=classe)
        rr = real.get(('/'.join(k), cand), {})
        linha['dif_wape_ruido_realista_max'] = rr.get('dif_wape', '') if cat == 'O' else ''
        linha['mudancas_escolha_ruido_realista'] = rr.get('mudancas', 0) if cat == 'O' else ''
        x = sx.get((*k, cand))
        if cat == 'O':
            c = inv[k].get(cand, {})
            linha['reproducao_windows'] = 'OK' if c else ''
            linha['series_conservador'] = uso_o[(*k, cand, 'conservador')]
            linha['series_agressivo'] = uso_o[(*k, cand, 'agressivo')]
        elif cat == 'X':
            linha['reproducao_windows'] = 'OK' if x and x['S_reproduz_1e6_windows'] == 'True' and x['F_reproduz_1e6_windows'] == 'True' else 'FALHA'
            linha['dif_wape_libm_x'] = max(float(x['S_dif_libm'] or 0), float(x['F_dif_libm'] or 0)) if x else ''
            linha['dif_wape_estresse_ulp_x'] = max(float(x['S_max_dif_ulp'] or 0), float(x['F_max_dif_ulp'] or 0)) if x else ''
            linha['series_conservador'] = uso_x[(*k, cand, 'conservador')]
            linha['series_agressivo'] = uso_x[(*k, cand, 'agressivo')]
        elif cat == 'B-HIST':
            linha['series_conservador'] = uso_b[(*k, 'B_HIST', 'conservador')]
            linha['series_agressivo'] = uso_b[(*k, 'B_HIST', 'agressivo')]
        if cand == mod:
            st, por = ('EXPERIMENTAL', 'Moderado publicado preservado; métrica kVA experimental') if kva else ('APROVADO', 'Moderado publicado preservado byte a byte; reprodução exata no Windows; não é homologação')
        elif classe in ('SEM_EVIDENCIA_SUFICIENTE', 'NAO_APLICAVEL_AO_PAINEL_DIST'):
            st, por = 'BLOQUEADO', classe
        elif classe in ('REJEITADO', 'CONDICIONAL_REPROVADO', 'CONDICIONAL_NAO_CALIBRADO'):
            st, por = 'REPROVADO', r['motivo_nao_competitivo'] or r['motivo_inelegivel'] or classe
        elif cat == 'X' and r['algoritmo'] == 'knn' and k in KNN_EMPATE:
            st, por = 'BLOQUEADO', 'resultado definido pelo desempate de vizinhos à mesma distância (empates exatos); não reprodutível'
        elif cat == 'X' and linha['reproducao_windows'] != 'OK':
            st, por = 'BLOQUEADO', 'reprodução S/F falhou no Windows'
        elif cat == 'O' and rr.get('mudancas', 0) > 0:
            st, por = 'BLOQUEADO', 'escolha por série muda sob ruído realista de libm'
        elif kva:
            st, por = 'EXPERIMENTAL', 'métrica kVA experimental (EXPERIMENTAL_KVA)'
        elif cat == 'X':
            nota = '; WAPE muda > 1e-6 com outra libm (falharia o portão v1 fora do Windows)' if x and float(linha['dif_wape_libm_x'] or 0) > 1e-6 else ''
            st, por = 'EXPERIMENTAL', 'configuração otimizada: só na 1.1 após revisão (D4)' + nota
        elif cat == 'B-HIST':
            st, por = 'EXPERIMENTAL', 'simulação condicional (D5); não é intervalo de confiança'
        elif cat in ('N', 'N5'):
            st, por = 'EXPERIMENTAL', 'congelado até a confirmação com a competência 2026 (D7)'
        elif cat == 'N6':
            st, por = 'REPROVADO', 'elasticidade reprovada'
        else:
            st, por = 'APROVADO', 'original competitivo, reprodução exata no Windows, escolhas estáveis sob ruído realista; integração depende de D2 e do aceite'
        linha['status'] = st
        linha['justificativa'] = por
        linhas.append(linha)
    campos = ['conceito', 'metrica', 'unidade', 'candidato', 'categoria', 'algoritmo', 'papel', 'status', 'justificativa', 'wape_produto',
              'razao_wape_moderado', 'reproducao_windows', 'series_conservador', 'series_agressivo', 'dif_wape_ruido_realista_max',
              'mudancas_escolha_ruido_realista', 'dif_wape_libm_x', 'dif_wape_estresse_ulp_x', 'classe_referencia']
    with open(saida, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        for l in linhas:
            w.writerow({c: l.get(c, '') for c in campos})
    tab = Counter((l['categoria'], l['status']) for l in linhas)
    print(len(linhas), dict(sorted(tab.items())))
    print(Counter(l['status'] for l in linhas))


if __name__ == '__main__':
    main(*sys.argv[1:])
