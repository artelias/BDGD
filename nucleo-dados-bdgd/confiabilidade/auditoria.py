"""Auditoria do produto publicado do módulo (somente leitura; resultado resumido em JSON e CSV).

    python -m confiabilidade.auditoria [--produto web/public/data/confiabilidade] [--saida docs/CONFIABILIDADE/auditoria]

Verifica:
  A1 manifesto: SHA-256 e tamanho de cada arquivo;
  A2 chaves: (DIST, CONJ, ano) únicas; um conjunto pertence a uma só distribuidora em cada ano;
  A3 contrato: anos 2022–2025, contagens inteiras, nada negativo, nenhum demonstrativo, supressão de contagens pequenas;
  A4 piloto EPB (6600) e ESE (6587): totais de infraestrutura 2025 = totais do pacote público do portal (index.json);
  A5 reconciliação DIC/FIC × oficial: distribuição das diferenças por distribuidora, ano e indicador;
  A6 geometria: conjuntos com polígono × conjuntos de 2025, e polígonos de conjuntos fora da apuração.
"""
import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from . import contrato as K
from .metricas import TIPO

RAIZ = Path(__file__).resolve().parents[1]


def auditar(produto=RAIZ / 'web/public/data/confiabilidade', saida=RAIZ / 'docs/CONFIABILIDADE/auditoria'):
    produto, saida = Path(produto), Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    R, falhas = {}, []
    man = json.loads((produto / 'manifesto.json').read_text(encoding='utf-8'))
    dif = [a['caminho'] for a in man['arquivos'] if hashlib.sha256((produto / a['caminho']).read_bytes()).hexdigest() != a['sha256']]
    R['A1_manifesto'] = dict(arquivos=len(man['arquivos']), divergentes=dif, bytes=sum(a['bytes'] for a in man['arquivos']))
    if dif:
        falhas.append('A1')

    idx = json.loads((produto / 'indice.json').read_text(encoding='utf-8'))
    dono = defaultdict(set); chaves = Counter(); viol = Counter(); rec = []; geo_conj = 0; geo_ok = 0; anos_conj = Counter()
    soma_infra = defaultdict(lambda: defaultdict(float))
    for f in sorted((produto / 'distribuidoras').glob('*.json')):
        d = json.loads(f.read_text(encoding='utf-8'))
        for c in d['conjuntos']:
            if '2025' in c['a']:
                geo_conj += 1; geo_ok += c['geo']
            for a, b in c['a'].items():
                chaves[(d['dist'], c['c'], a)] += 1
                dono[(c['c'], a)].add(d['dist'])
                anos_conj[a] += 1
                if int(a) not in K.ANOS:
                    viol['ano_fora'] += 1
                for i, v in (b['infra'] or {}).items():
                    if v is None:
                        continue
                    if v < 0:
                        viol['negativo'] += 1
                    if TIPO.get(i) == 'contagem' and not isinstance(v, int):
                        viol['contagem_nao_inteira'] += 1
                    if a == '2025' and i in ('trafos', 'km_mt', 'km_bt', 'uc', 'uc_bt'):
                        soma_infra[d['dist']][i] += v
                for al in (c['al'] or {}).get('lista', []):
                    for k in ('uc_bt', 'uc_mt'):
                        if al.get(k) is not None and 0 < al[k] < K.SUPRESSAO_K:
                            viol['contagem_pequena_publicada'] += 1
                r = b.get('rec')
                if r and r.get('dec') is not None:
                    for ind in ('dec', 'fec'):
                        of, rc = b[ind], r[ind]
                        if of is None or rc is None:
                            continue
                        rec.append(dict(dist=d['dist'], nome=d['nome'], conj=c['c'], ano=a, ind=ind, oficial=of, reconstruido=rc, dif=rc - of,
                                        rel=(rc - of) / of if of > 0 else None, ok=K.reconciliado(rc, of), cobertura=r.get('cobertura')))
    dup = [k for k, n in chaves.items() if n > 1]
    multi = [dict(conj=k[0], ano=k[1], dists=sorted(v)) for k, v in dono.items() if len(v) > 1]
    R['A2_chaves'] = dict(combinacoes=len(chaves), duplicadas=len(dup), conjunto_em_mais_de_uma_dist=multi[:20], por_ano=dict(sorted(anos_conj.items())))
    if dup or multi:
        falhas.append('A2')
    R['A3_contrato'] = dict(violacoes=dict(viol), demonstrativo=idx['demonstrativo'])
    if viol or idx['demonstrativo'] is not False:
        falhas.append('A3')

    portal = json.loads((RAIZ / 'web/public/data/2025-12-31/index.json').read_text(encoding='utf-8'))
    at = {(k, m, r[0]): r[1] for k, ms in portal['ativosTotais'].items() for m, rows in ms.items() for r in rows}
    piloto = {}
    for dist in (6600, 6587, 26):
        s = soma_infra.get(dist, {})
        ref = dict(trafos=at.get(('trafo_dist', 'quantidade', dist)), km_mt=at.get(('rede_mt', 'extensao_km', dist)), km_bt=at.get(('rede_bt', 'extensao_km', dist)),
                   uc=at.get(('consumidores', 'quantidade', dist)))
        piloto[dist] = {k: dict(conjuntos=round(s.get(k, 0), 3), portal=ref[k], igual=ref[k] is not None and abs(s.get(k, 0) - ref[k]) <= 0.01 * (1 if k.startswith('km') else 0) + 1e-6)
                        for k in ref}
    R['A4_piloto_contra_portal_2025'] = piloto
    R['A4_nota'] = ('Soma dos conjuntos com continuidade apurada em 2025 contra o total da distribuidora no portal. Diferenças vêm de registros sem '
                    'conjunto válido ou de conjuntos sem apuração ANEEL (ficam fora do módulo); a auditoria de cada DIST-ano está em fontes_bdgd.')

    por = defaultdict(list)
    for x in rec:
        por[(x['dist'], x['nome'], x['ano'], x['ind'])].append(x)
    linhas = []
    for (dist, nome, ano, ind), xs in sorted(por.items()):
        rels = [abs(x['rel']) for x in xs if x['rel'] is not None]
        linhas.append(dict(dist=dist, distribuidora=nome, ano=ano, indicador=ind.upper(), conjuntos=len(xs), reconciliados=sum(bool(x['ok']) for x in xs),
                           pct_reconciliados=round(sum(bool(x['ok']) for x in xs) / len(xs), 4), mediana_dif_rel_abs=round(statistics.median(rels), 4) if rels else None,
                           p90_dif_rel_abs=round(sorted(rels)[int(0.9 * (len(rels) - 1))], 4) if rels else None,
                           vies_medio=round(statistics.fmean(x['dif'] for x in xs), 4)))
    with open(saida / 'RECONCILIACAO_POR_DIST_ANO_INDICADOR.csv', 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(linhas[0])); w.writeheader(); w.writerows(linhas)
    tot = Counter((x['ind'], bool(x['ok'])) for x in rec)
    ruins = sorted((l for l in linhas if l['pct_reconciliados'] < 0.8), key=lambda l: l['pct_reconciliados'])
    R['A5_reconciliacao'] = dict(
        criterio=f'|reconstruído − oficial| ≤ {K.TOL_RECONSTRUCAO_ABS} ou ≤ {int(K.TOL_RECONSTRUCAO * 100)}% do oficial (experimental, não homologação)',
        pares=len(rec), dec=dict(ok=tot[('dec', True)], total=tot[('dec', True)] + tot[('dec', False)]), fec=dict(ok=tot[('fec', True)], total=tot[('fec', True)] + tot[('fec', False)]),
        dist_ano_indicador_abaixo_de_80pct=[dict(dist=l['dist'], distribuidora=l['distribuidora'], ano=l['ano'], indicador=l['indicador'], pct=l['pct_reconciliados'],
                                                  mediana=l['mediana_dif_rel_abs']) for l in ruins[:40]],
        n_dist_ano_indicador_abaixo_de_80pct=len(ruins))

    feats = 0; fora = 0
    conj_2025 = {(k[0], k[1]) for k in chaves if k[2] == '2025'}
    for g in (produto / 'geo').glob('*.json'):
        fc = json.loads(g.read_text(encoding='utf-8'))
        for ft in fc['features']:
            feats += 1
            fora += (int(g.stem), ft['properties']['c']) not in conj_2025
    R['A6_geometria'] = dict(conjuntos_2025=geo_conj, conjuntos_2025_com_poligono=geo_ok, poligonos_publicados=feats, poligonos_de_conjunto_sem_apuracao_2025=fora,
                             fonte=idx['fontes']['geometria'])
    R['falhas'] = falhas
    (saida / 'AUDITORIA_PRODUTO.json').write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({k: v for k, v in R.items() if k not in ('A5_reconciliacao',)}, ensure_ascii=False)[:3000])
    print(json.dumps({k: v for k, v in R['A5_reconciliacao'].items() if k != 'dist_ano_indicador_abaixo_de_80pct'}, ensure_ascii=False))
    return R


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--produto', default=str(RAIZ / 'web/public/data/confiabilidade'))
    ap.add_argument('--saida', default=str(RAIZ / 'docs/CONFIABILIDADE/auditoria'))
    a = ap.parse_args()
    auditar(a.produto, a.saida)
