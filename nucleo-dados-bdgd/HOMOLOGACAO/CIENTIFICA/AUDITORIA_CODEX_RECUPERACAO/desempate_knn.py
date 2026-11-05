"""O resultado do knn_analogos_otim depende de como a busca de vizinhos desempata distâncias iguais.

Uso: python desempate_knn.py <saida_dir>
Mesmos dados, mesma configuração (k, variável, padronização); só muda o algoritmo de busca ou o
leaf_size da árvore, que alteram a ordem em que vizinhos empatados são encontrados. Mede S e F.
"""
import csv
import json
import sys
from pathlib import Path

import sklearn.neighbors as SN

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))
from motor_cenarios.recuperacao.fontes import OT, R, carregar  # noqa: E402

K = ('consumidores', 'quantidade')
LINUX = {'S': 0.03620207211997554, 'F': 0.023107202334389846}


def main(saida):
    r = next(r for r in csv.DictReader(R.ENTRADAS['modelos_otimizacao'].open(encoding='utf-8'))
             if (r['conceito'], r['metrica']) == K and r['modelo'] == 'knn_analogos_otim')
    hp, nomes = json.loads(r['hiperparametros']), r['variaveis'].split('|')
    _, _, _, _, motor_x = carregar()
    Original = SN.KNeighborsRegressor
    out = []
    for alg, leaf in [('auto', 30), ('kd_tree', 30), ('kd_tree', 5), ('kd_tree', 10), ('kd_tree', 60), ('ball_tree', 30), ('brute', 30)]:
        class Var(Original):
            def __init__(self, n_neighbors=5, **kw):
                super().__init__(n_neighbors=n_neighbors, algorithm=alg, leaf_size=leaf)
        SN.KNeighborsRegressor = Var
        av = OT.Avaliador(motor_x, K, True, {})
        w = {et: av.avaliar('knn', nomes, hp, o, et)['wape'] for et, o in (('S', 2023), ('F', 2024))}
        SN.KNeighborsRegressor = Original
        out.append(dict(algoritmo=alg, leaf_size=leaf, **{f'wape_{et}': w[et] for et in w},
                        **{f'reproduz_registro_1e6_{et}': abs(w[et] - float(r[et + '_wape'])) <= 1e-6 for et in w},
                        **{f'igual_linux_{et}': w[et] == LINUX[et] for et in w}))
        print(out[-1], flush=True)
    Path(saida).mkdir(parents=True, exist_ok=True)
    (Path(saida) / 'DESEMPATE_KNN_OTIM.json').write_text(json.dumps(out, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main(*sys.argv[1:])
