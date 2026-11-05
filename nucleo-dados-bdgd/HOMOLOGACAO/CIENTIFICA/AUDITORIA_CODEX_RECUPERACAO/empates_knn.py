"""Fragilidade numérica do knn_analogos_otim (consumidores): empates de distância e sensibilidade a 1 ULP.

Uso: python empates_knn.py <saida_dir> [replicas]
1. Para os pontos S (origem 2023) e F (2024): distância do k-ésimo e do (k+1)-ésimo vizinho; conta
   empates exatos e quase-empates (diferença relativa < 1e-12) na fronteira da vizinhança.
2. Sensibilidade: perturba as variáveis de entrada em ±1 ULP (sinal aleatório, semente fixa) e mede
   |ΔWAPE| de S e F. Mostra se uma diferença de último dígito, como a de outra libm ou de outro
   caminho SIMD do NumPy, basta para mudar a vizinhança.
Não altera dados, código ou limites.
"""
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))
from motor_cenarios.recuperacao.fontes import C, OT, R, carregar  # noqa: E402

K = ('consumidores', 'quantidade')


def main(saida, replicas='20'):
    saida = Path(saida); saida.mkdir(parents=True, exist_ok=True)
    r = next(r for r in csv.DictReader(R.ENTRADAS['modelos_otimizacao'].open(encoding='utf-8'))
             if (r['conceito'], r['metrica']) == K and r['modelo'] == 'knn_analogos_otim')
    hp, nomes = json.loads(r['hiperparametros']), r['variaveis'].split('|')
    _, _, _, _, motor_x = carregar()
    av = OT.Avaliador(motor_x, K, True, {})
    out = dict(config=dict(hp=hp, variaveis=nomes), empates={}, sensibilidade=[])
    original = OT.ajustar
    for et, o in (('S', 2023), ('F', 2024)):
        res, mod = av.avaliar('knn', nomes, hp, o, et, retornar_modelo=True)
        pts = av.pts[o]
        motor_x.k = K
        X = np.asarray([C.vetor(motor_x.feats(d, o, y0), nomes) for d, _, y0, _ in pts], float)
        Z = mod.pipe[:-1].transform(X)
        knn = mod.pipe[-1]
        k = knn.n_neighbors
        dist, _ = knn.kneighbors(Z, n_neighbors=min(k + 1, knn.n_samples_fit_))
        gap = dist[:, k] - dist[:, k - 1]
        rel = gap / np.maximum(dist[:, k], 1e-300)
        Ztr = knn._fit_X
        dup = len(Ztr) - len(np.unique(np.round(Ztr, 12), axis=0))
        out['empates'][et] = dict(k=int(k), algoritmo=knn._fit_method, consultas=int(len(Z)), treino=int(len(Ztr)),
                                  linhas_treino_duplicadas=int(dup), empates_exatos_fronteira=int((gap == 0).sum()),
                                  quase_empates_rel_1e12=int((rel < 1e-12).sum()), quase_empates_rel_1e9=int((rel < 1e-9).sum()),
                                  menor_gap_relativo_nao_nulo=float(rel[rel > 0].min()) if (rel > 0).any() else None, wape=res['wape'])
    base = {et: out['empates'][et]['wape'] for et in ('S', 'F')}
    for rep in range(int(replicas)):
        rng = np.random.default_rng(20261105 + rep)
        def ajustar_perturbado(algo, hp_, X, g, _rng=rng):
            X = np.asarray(X, float).copy()
            fin = np.isfinite(X)
            s = _rng.integers(-1, 2, size=X.shape)
            X[fin] = np.where(s[fin] > 0, np.nextafter(X[fin], np.inf), np.where(s[fin] < 0, np.nextafter(X[fin], -np.inf), X[fin]))
            m = original(algo, hp_, X, g)
            class P:
                def predict(self, Xq):
                    Xq = np.asarray(Xq, float).copy(); f = np.isfinite(Xq); sq = _rng.integers(-1, 2, size=Xq.shape)
                    Xq[f] = np.where(sq[f] > 0, np.nextafter(Xq[f], np.inf), np.where(sq[f] < 0, np.nextafter(Xq[f], -np.inf), Xq[f]))
                    return m.predict(Xq)
            return P()
        OT.ajustar = ajustar_perturbado
        av2 = OT.Avaliador(motor_x, K, True, {})
        w = {et: av2.avaliar('knn', nomes, hp, o, et)['wape'] for et, o in (('S', 2023), ('F', 2024))}
        OT.ajustar = original
        out['sensibilidade'].append(dict(replica=rep, **{f'dif_{et}': abs(w[et] - base[et]) for et in w},
                                         **{f'reproduz_1e6_{et}': abs(w[et] - float(r[et + '_wape'])) <= 1e-6 for et in w}))
    s = out['sensibilidade']
    out['resumo_sensibilidade'] = dict(replicas=len(s), S_mudou=sum(x['dif_S'] > 0 for x in s), F_mudou=sum(x['dif_F'] > 0 for x in s),
                                       max_dif_S=max(x['dif_S'] for x in s), max_dif_F=max(x['dif_F'] for x in s),
                                       falha_portao_1e6=sum(not (x['reproduz_1e6_S'] and x['reproduz_1e6_F']) for x in s))
    (saida / 'EMPATES_KNN_OTIM.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    print(json.dumps({k: v for k, v in out.items() if k != 'sensibilidade'}, indent=1))


if __name__ == '__main__':
    main(*sys.argv[1:])
