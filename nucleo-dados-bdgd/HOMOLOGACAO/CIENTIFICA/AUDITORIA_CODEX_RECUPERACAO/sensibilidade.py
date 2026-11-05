"""Sensibilidade numérica da recuperação só com modelos originais (base da proposta recuperacao-2).

Uso: python sensibilidade.py <saida_dir> <referencia_produto.json> <cenario> [cenario ...]
  cenario = libm          : `math.log`/`math.exp` de arredondamento correto (reproduz o Linux do Codex no RF de bancos)
          | ruido:<seed>:<p>: outra libm, realista: ±1 ULP determinístico por argumento em uma fração p das chamadas
                              de `log`/`exp` do gerador (variáveis, alvo e projeção); valores iguais seguem iguais
          | ulp:<seed>    : ESTRESSE: cada entrada das variáveis de painel perturbada em ±1 ULP com sinal aleatório,
                              o que também desfaz duplicatas exatas (mais severo que qualquer plataforma)

Para cada cenário: refaz o inventário dos 9 originais nas 29 métricas e a seleção por série do pacote do
Codex (`modo originais`), sem o portão de 1e-9, que é justamente o objeto do teste, e compara com a
execução de referência:
  - escolha agregada por métrica e |ΔWAPE| de cada modelo;
  - por série e lado: modelo escolhido, classe, valores publicados dos 5 anos.
Nada é gravado fora de <saida_dir>. As configurações X ficam de fora (avaliadas à parte).
"""
import csv
import json
import math
import sys
import tempfile
from collections import Counter
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).parent))
from causa_wape import cr_exp, cr_log, modulo_math  # noqa: E402
from motor_cenarios.recuperacao import inventario as INV  # noqa: E402
from motor_cenarios.recuperacao.fontes import C, R, carregar  # noqa: E402
from motor_cenarios.recuperacao.selecao import selecionar  # noqa: E402

LADOS = ('conservador', 'agressivo')


def perturbar(X, rng):
    X = np.asarray(X, float).copy()
    f = np.isfinite(X)
    s = rng.integers(-1, 2, size=X.shape)
    X[f] = np.where(s[f] > 0, np.nextafter(X[f], np.inf), np.where(s[f] < 0, np.nextafter(X[f], -np.inf), X[f]))
    return X


def rodar(cenario, ref, pub):
    original_treinar, original_math, original_verif = C.treinar_painel, C.math, INV.verificar_reproducao
    registro = {}
    if cenario == 'libm':
        C.math = modulo_math(log=cr_log, exp=cr_exp)
    elif cenario.startswith('ruido:'):
        # Outra libm, de forma realista: o desvio de 1 ULP é função determinística do argumento
        # (valores iguais continuam iguais), numa fração p das entradas de log e exp.
        _, semente, p = cenario.split(':')
        limite = int(float(p) * 2**32)
        def ruidosa(f, tag):
            def g(x):
                y = f(x)
                if not (isinstance(x, (int, float)) and math.isfinite(y)):
                    return y
                h = int.from_bytes(np.float64(x).tobytes(), 'little') * 0x9E3779B97F4A7C15 + int(semente) * 0xBF58476D1CE4E5B9 + tag
                h = (h ^ (h >> 31)) * 0x94D049BB133111EB & (2**64 - 1)
                if (h & 0xFFFFFFFF) < limite:
                    return math.nextafter(y, math.inf if (h >> 32) & 1 else -math.inf)
                return y
            return g
        C.math = modulo_math(log=ruidosa(math.log, 1), exp=ruidosa(math.exp, 2))
    elif cenario.startswith('ulp:'):
        rng = np.random.default_rng(int(cenario.split(':')[1]))
        def treinar(modelo, X, g):
            m, clip = original_treinar(modelo, perturbar(X, rng), g)
            class P:
                def predict(self, Xq):
                    return m.predict(perturbar(Xq, rng))
            return P(), clip
        C.treinar_painel = treinar
    def verif(pm, met, cen, prev):
        registro[(pm['conceito'], pm['metrica'])] = dict(
            escolha_igual=cen == pm['cenarios'],
            dif_wape={n: abs((x['erros']['wape'] or 0) - (pm['modelos'][n]['wape'] or 0)) for n, x in met.items()})
        return {}
    INV.verificar_reproducao = verif
    vazio = Path(tempfile.mkdtemp()) / 'sem_x.csv'
    with R.ENTRADAS['modelos_otimizacao'].open(encoding='utf-8') as f:
        vazio.write_text(f.readline(), encoding='utf-8')
    entrada_x = R.ENTRADAS['modelos_otimizacao']
    R.ENTRADAS['modelos_otimizacao'] = vazio
    try:
        series, _, _, motor, motor_x = carregar()
        produto = {}
        for pm in pub['metricas']:
            if not pm['series']:
                continue
            k = (pm['conceito'], pm['metrica'])
            bundle = INV.construir(k, pm, motor, motor_x)
            if not registro[k]['escolha_igual']:
                produto[k] = None
                continue
            res, _ = selecionar(pm, bundle, series, 'originais', 'sensibilidade')
            produto[k] = res
    finally:
        C.treinar_painel, C.math, INV.verificar_reproducao = original_treinar, original_math, original_verif
        R.ENTRADAS['modelos_otimizacao'] = entrada_x
    linhas, resumo = [], Counter()
    refm = {(m['conceito'], m['metrica']): m for m in ref['metricas']}
    for k, m in produto.items():
        reg = registro[k]
        resumo['metricas'] += 1
        resumo['escolha_agregada_diferente'] += not reg['escolha_igual']
        resumo['max_dif_wape_x1e9'] = max(resumo['max_dif_wape_x1e9'], int(max(reg['dif_wape'].values()) * 1e9))
        if m is None:
            continue
        for d, s in m['series'].items():
            r = refm[k]['series'][d]
            resumo['series'] += 1
            if s['completude'] != r['completude']:
                resumo['classe_diferente'] += 1
            for lado in LADOS:
                a, b = (s['extremos'][lado] or {}).get('modelo'), (r['extremos'][lado] or {}).get('modelo')
                va, vb = s[lado], r[lado]
                dif_un = max((abs(x - y) for x, y in zip(va, vb)), default=0) if va and vb else None
                if a != b:
                    resumo['modelo_diferente'] += 1
                if va and vb and dif_un and dif_un > 0:
                    resumo['valores_diferentes'] += 1
                    if m['natureza'] == 'discrete_count':
                        resumo['contagens_diferentes_em_1_unidade' if dif_un <= 1 else 'contagens_diferentes_mais_de_1_unidade'] += 1
                if a != b or (va and vb and dif_un):
                    linhas.append(dict(cenario=cenario, conceito=k[0], metrica=k[1], DIST=d, lado=lado, modelo_ref=b, modelo=a,
                                       classe_ref=r['completude'], classe=s['completude'],
                                       max_dif_absoluta=dif_un, max_dif_relativa=max((abs(x - y) / max(abs(y), 1e-12) for x, y in zip(va, vb)), default=0) if va and vb else None))
    return dict(cenario=cenario, resumo=dict(resumo), metricas={'/'.join(k): v for k, v in registro.items()}), linhas


def main(saida, referencia, *cenarios):
    saida = Path(saida); saida.mkdir(parents=True, exist_ok=True)
    ref = json.loads(Path(referencia).read_text(encoding='utf-8'))
    pub = json.loads(R.ENTRADAS['publicado'].read_text(encoding='utf-8'))
    for cen in cenarios:
        res, linhas = rodar(cen, ref, pub)
        nome = cen.replace(':', '_')
        (saida / f'SENSIBILIDADE_{nome}.json').write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding='utf-8')
        if linhas:
            with open(saida / f'SENSIBILIDADE_{nome}.csv', 'w', newline='', encoding='utf-8') as f:
                w = csv.DictWriter(f, fieldnames=list(linhas[0])); w.writeheader(); w.writerows(linhas)
        print(json.dumps(dict(cenario=cen, **res['resumo'])), flush=True)


if __name__ == '__main__':
    main(*sys.argv[1:])
