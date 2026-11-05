"""Sensibilidade das configurações otimizadas (X) ao último dígito, nas 29 métricas.

Uso: python sensibilidade_x.py <saida_dir> [replicas]
Para cada configuração X de `MODELOS_AVALIADOS.csv` (origem=otimizado): WAPE de S e F no Windows,
margem até o portão de reprodução (|Δ| ≤ 1e-6 contra o registrado) e |ΔWAPE| com as variáveis de
treino e de previsão perturbadas em ±1 ULP (sinal aleatório, sementes fixas). Também a variante com
`math.log`/`math.exp` de arredondamento correto (comportamento do glibc).
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).parent))
from causa_wape import cr_exp, cr_log, modulo_math  # noqa: E402
from motor_cenarios.recuperacao.fontes import C, OT, R, carregar  # noqa: E402
from sensibilidade import perturbar  # noqa: E402


def main(saida, replicas='3'):
    saida = Path(saida); saida.mkdir(parents=True, exist_ok=True)
    pub = json.loads(R.ENTRADAS['publicado'].read_text(encoding='utf-8'))
    disc = {(m['conceito'], m['metrica']): m['natureza'] == 'discrete_count' for m in pub['metricas']}
    regs = [r for r in csv.DictReader(R.ENTRADAS['modelos_otimizacao'].open(encoding='utf-8')) if r['origem'] == 'otimizado']
    original = OT.ajustar
    linhas = []
    def avaliar_todos(motor_x, ajuste=None):
        OT.ajustar = ajuste or original
        out = {}
        try:
            for r in regs:
                k = (r['conceito'], r['metrica'])
                av = OT.Avaliador(motor_x, k, disc[k], {})
                hp, nomes = json.loads(r['hiperparametros']), r['variaveis'].split('|')
                out[(k, r['modelo'])] = {et: av.avaliar(r['algoritmo'], nomes, hp, o, et).get('wape') for et, o in (('S', 2023), ('F', 2024))}
        finally:
            OT.ajustar = original
        return out
    _, _, _, _, mx = carregar()
    base = avaliar_todos(mx)
    variantes = {}
    om, oc = OT.math, C.math
    OT.math = C.math = modulo_math(log=cr_log, exp=cr_exp)
    _, _, _, _, mx_libm = carregar()
    variantes['libm'] = avaliar_todos(mx_libm)
    OT.math, C.math = om, oc
    for rep in range(int(replicas)):
        rng = np.random.default_rng(777 + rep)
        def aj(algo, hp_, X, g, _rng=rng):
            m = original(algo, hp_, perturbar(X, _rng), g)
            class P:
                def predict(self, Xq):
                    return m.predict(perturbar(Xq, _rng))
            return P()
        variantes[f'ulp{rep}'] = avaliar_todos(mx, aj)
    for r in regs:
        k = (r['conceito'], r['metrica'])
        b = base[(k, r['modelo'])]
        linha = dict(conceito=k[0], metrica=k[1], modelo=r['modelo'], algoritmo=r['algoritmo'], hiperparametros=r['hiperparametros'],
                     variaveis=r['variaveis'])
        for et in ('S', 'F'):
            reg = float(r[et + '_wape']) if r[et + '_wape'] else None
            linha[f'{et}_registrado'] = reg
            linha[f'{et}_windows'] = b[et]
            linha[f'{et}_dif_registro'] = None if reg is None or b[et] is None else abs(b[et] - reg)
            difs = [abs(v[(k, r['modelo'])][et] - b[et]) for n, v in variantes.items() if n.startswith('ulp') and b[et] is not None and v[(k, r['modelo'])][et] is not None]
            linha[f'{et}_max_dif_ulp'] = max(difs) if difs else None
            lv = variantes['libm'][(k, r['modelo'])][et]
            linha[f'{et}_dif_libm'] = None if lv is None or b[et] is None else abs(lv - b[et])
            linha[f'{et}_reproduz_1e6_windows'] = linha[f'{et}_dif_registro'] is not None and linha[f'{et}_dif_registro'] <= 1e-6
            linha[f'{et}_portao_falharia_sob_ulp'] = any(reg is not None and v[(k, r['modelo'])][et] is not None and abs(v[(k, r['modelo'])][et] - reg) > 1e-6
                                                        for n, v in variantes.items() if n.startswith('ulp'))
        linha['estavel'] = all((linha[f'{et}_max_dif_ulp'] or 0) <= 1e-9 and (linha[f'{et}_dif_libm'] or 0) <= 1e-9 for et in ('S', 'F'))
        linhas.append(linha)
    with open(saida / 'SENSIBILIDADE_X.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0])); w.writeheader(); w.writerows(linhas)
    resumo = dict(configuracoes=len(linhas), reproduz_windows=sum(l['S_reproduz_1e6_windows'] and l['F_reproduz_1e6_windows'] for l in linhas),
                  estaveis=sum(l['estavel'] for l in linhas),
                  instaveis=[f"{l['conceito']}/{l['metrica']}/{l['modelo']}" for l in linhas if not l['estavel']],
                  portao_falharia_sob_ulp=[f"{l['conceito']}/{l['metrica']}/{l['modelo']}" for l in linhas if l['S_portao_falharia_sob_ulp'] or l['F_portao_falharia_sob_ulp']])
    (saida / 'SENSIBILIDADE_X_RESUMO.json').write_text(json.dumps(resumo, indent=1, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(resumo, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main(*sys.argv[1:])
