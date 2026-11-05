"""Causa da divergência de WAPE entre Linux (Codex) e Windows (referência).

Uso: python causa_wape.py <saida_dir> [conceito/metrica ...]

Experimentos, todos no mesmo processo Windows, sem alterar dados, código ou limites:
  E0  referência: `cenarios.executar_metrica` sem alteração;
  E1  `math.log`/`math.exp` da UCRT trocados por versões de arredondamento correto (decimal, 50 dígitos),
      que é o comportamento do glibc (erro < 0,52 ULP) usado no Linux;
  E2  só `math.log` trocado;
Para cada métrica e modelo: WAPE, |Δ| contra o publicado e contra o valor observado no Linux (quando há).
Também conta, nas entradas efetivas de `math.log` do gerador, quantas vezes a UCRT difere do valor
corretamente arredondado.
"""
import json
import math
import sys
import types
from decimal import Decimal, getcontext
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))
from motor_cenarios.recuperacao.fontes import C, R, carregar  # noqa: E402

getcontext().prec = 50
LINUX = {('bancos_capacitores', 'quantidade', 'random_forest_painel'): 0.06005597829053297}


def cr_log(x):
    if not (isinstance(x, (int, float)) and math.isfinite(x) and x > 0):
        return math.log(x)
    return float(Decimal(x).ln())


def cr_exp(x):
    if not (isinstance(x, (int, float)) and math.isfinite(x)) or abs(x) > 700:
        return math.exp(x)
    return float(Decimal(x).exp())


class Contador:
    def __init__(self):
        self.n = self.dif = 0
        self.exemplos = []

    def log(self, x):
        a, b = math.log(x), cr_log(x)
        self.n += 1
        if a != b:
            self.dif += 1
            if len(self.exemplos) < 5:
                self.exemplos.append(dict(x=repr(x), ucrt=repr(a), correto=repr(b), ulps=round((a - b) / math.ulp(b))))
        return a


def modulo_math(**troca):
    ns = types.SimpleNamespace(**{k: getattr(math, k) for k in dir(math) if not k.startswith('_')})
    for k, v in troca.items():
        setattr(ns, k, v)
    return ns


def rodar(motor, k):
    segs, bt, prev, _, _ = C.executar_metrica(motor, k)
    met, cen, _ = C.escolher_cenarios(bt, prev, segs)
    return {m: x['erros']['wape'] for m, x in met.items()}, cen, prev


def main(saida, *alvos):
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    pub = json.loads(R.ENTRADAS['publicado'].read_text(encoding='utf-8'))
    pubm = {(m['conceito'], m['metrica']): m for m in pub['metricas'] if m['series']}
    chaves = [tuple(a.split('/')) for a in alvos] or sorted(pubm)
    original = C.math
    out = []
    for nome, troca in [('E0_ucrt', {}), ('E1_log_exp_corretos', dict(log=cr_log, exp=cr_exp)), ('E2_log_correto', dict(log=cr_log))]:
        C.math = modulo_math(**troca) if troca else original
        series, empresas, _, motor, _ = carregar()   # recarrega: as variáveis internas também usam math.log
        for k in chaves:
            w, cen, prev = rodar(motor, k)
            pm = pubm[k]
            for m, v in w.items():
                p = pm['modelos'][m]['wape']
                lx = LINUX.get((*k, m))
                out.append(dict(experimento=nome, conceito=k[0], metrica=k[1], modelo=m, wape=v, wape_publicado=p,
                                dif_publicado=None if v is None or p is None else abs(v - p),
                                wape_linux=lx, dif_linux=None if lx is None or v is None else abs(v - lx),
                                escolha_igual_publicada=cen == pm['cenarios']))
            print(nome, '/'.join(k), {m: (None if r['dif_publicado'] is None else f"{r['dif_publicado']:.3g}") for r in out[-len(w):] for m in [r['modelo']]}, flush=True)
    C.math = original
    cont = Contador()
    C.math = modulo_math(log=cont.log)
    _, _, _, motor, _ = carregar()
    for k in chaves:
        rodar(motor, k)
    C.math = original
    res = dict(linhas=out, log_ucrt_vs_correto=dict(chamadas=cont.n, diferentes=cont.dif, exemplos=cont.exemplos))
    (saida / 'CAUSA_WAPE.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(res['log_ucrt_vs_correto'], ensure_ascii=False))


if __name__ == '__main__':
    main(*sys.argv[1:])
