"""Reproduz no Windows a divergência do knn_analogos_otim observada no Linux, trocando só a libm.

Uso: python causa_knn_otim.py <saida_dir>
Para cada configuração otimizada (X) de consumidores/quantidade: S e F com a UCRT (referência) e com
`math.log`/`math.exp` de arredondamento correto (comportamento do glibc), contra o registrado na
otimização (997c4d7) e contra o observado pelo Codex no Linux.
"""
import csv
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).parent))
from causa_wape import cr_exp, cr_log, modulo_math  # noqa: E402
from motor_cenarios.recuperacao.fontes import C, OT, R, carregar  # noqa: E402

K = ('consumidores', 'quantidade')
LINUX = {'knn_analogos_otim': {'S': 0.03620207211997554, 'F': 0.023107202334389846}}


def main(saida):
    saida = Path(saida); saida.mkdir(parents=True, exist_ok=True)
    regs = [r for r in csv.DictReader(R.ENTRADAS['modelos_otimizacao'].open(encoding='utf-8')) if (r['conceito'], r['metrica']) == K and r['origem'] == 'otimizado']
    om, oo = C.math, OT.math
    out = []
    for nome, troca in [('E0_ucrt', {}), ('E1_log_exp_corretos', dict(log=cr_log, exp=cr_exp))]:
        C.math = OT.math = modulo_math(**troca) if troca else om
        if not troca:
            C.math, OT.math = om, oo
        _, _, _, _, motor_x = carregar()
        for r in regs:
            av = OT.Avaliador(motor_x, K, True, {})
            hp, nomes = json.loads(r['hiperparametros']), r['variaveis'].split('|')
            for et, o in (('S', 2023), ('F', 2024)):
                w = av.avaliar(r['algoritmo'], nomes, hp, o, et).get('wape')
                reg = float(r[et + '_wape'])
                lx = LINUX.get(r['modelo'], {}).get(et)
                out.append(dict(experimento=nome, modelo=r['modelo'], etapa=et, wape=w, registrado=reg, dif_registrado=abs(w - reg),
                                linux=lx, dif_linux=None if lx is None else abs(w - lx), dentro_1e6=abs(w - reg) <= 1e-6))
                print(out[-1], flush=True)
    C.math, OT.math = om, oo
    (saida / 'CAUSA_KNN_OTIM.json').write_text(json.dumps(out, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main(*sys.argv[1:])
