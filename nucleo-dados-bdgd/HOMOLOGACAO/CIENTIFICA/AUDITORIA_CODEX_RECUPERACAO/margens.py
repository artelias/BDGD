"""Margem até o limiar de cada decisão por série (certificado de margem da proposta recuperacao-2).

Uso: python margens.py <dir_execucao> <saida_dir>
Para toda decisão P1 (manter ou retirar o extremo publicado = opção A) e para o extremo escolhido em P2
(opção B): margens de Q5 (menor folga contínua de ordem, relativa ao Moderado), Q7 (s·(g_E − g_M) − 0,0005),
Q8 (contagens: s·(E_2030 − M_2030) − 1) e a distância de cada valor bruto de contagem ao meio inteiro.
Conta as decisões cuja margem decisiva fica abaixo de δ = 1e-9 (ruído de último dígito) e de δ = 1e-3
(ruído de RF/HGB entre plataformas, até 3e-4 observado).
"""
import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path

SINAL = {'conservador': -1, 'agressivo': 1}


def main(execucao, saida):
    execucao, saida = Path(execucao), Path(saida); saida.mkdir(parents=True, exist_ok=True)
    prod = json.loads((execucao / 'produto.json').read_text(encoding='utf-8'))
    inv = {(m['conceito'], m['metrica']): {c['id']: c for c in m['candidatos']} for m in json.loads((execucao / 'inventario.json').read_text(encoding='utf-8'))}
    linhas, cont = [], Counter()
    for m in prod['metricas']:
        k = (m['conceito'], m['metrica']); disc = m['natureza'] == 'discrete_count'
        cand = inv[k]; mod = m['cenarios']['moderado']
        for d, s in m['series'].items():
            if not s.get('moderado'):
                continue
            M = cand[mod]['trajetorias'][d]
            y25 = s['hist'][-1][1]
            for lado, sg in SINAL.items():
                decs = []
                if s['anteriores'].get(lado):
                    decs.append(('P1', m['cenarios'][lado], s['extremos'][lado] is not None and s['extremos'][lado]['categoria'] == 'A_PUBLICADO_MANTIDO'))
                e = s['extremos'][lado]
                if e and e['categoria'] == 'A_ORIGINAL':
                    decs.append(('P2_escolhido', e['modelo'], True))
                for etapa, mo, aceito in decs:
                    E = cand[mo]['trajetorias'].get(d)
                    if not E:
                        continue
                    gaps = [sg * (a - b) / b for a, b in zip(E, M)]
                    gE, gM = math.log(E[-1] / y25) / 5, math.log(M[-1] / y25) / 5
                    q7 = sg * (gE - gM) - 0.0005
                    q5 = min(gaps)
                    q8 = sg * (E[-1] - M[-1]) - 1 if disc else None
                    meio = min(abs((v % 1) - 0.5) for v in E + M) if disc else None
                    # margem decisiva: a regra mais próxima do limiar entre as que determinam o resultado
                    cand_m = [abs(q5), abs(q7) / max(abs(gM), 1e-3)] + ([abs(q8) / max(abs(M[-1]), 1)] if q8 is not None else [])
                    marg = min(cand_m)
                    alg = {mo, mod}
                    arvores = bool(alg & {'random_forest_painel', 'hgb_painel'})
                    linhas.append(dict(conceito=k[0], metrica=k[1], DIST=d, lado=lado, etapa=etapa, modelo=mo, moderado=mod, aceito=aceito,
                                       margem_q5_rel=q5, margem_q7=q7, margem_q8=q8, dist_meio_inteiro=meio, margem_decisiva_rel=marg,
                                       envolve_arvores=arvores))
                    cont[f'{etapa}_decisoes'] += 1
                    cont[f'{etapa}_margem_lt_1e-9'] += marg < 1e-9
                    cont[f'{etapa}_margem_lt_1e-6'] += marg < 1e-6
                    cont[f'{etapa}_margem_lt_1e-3'] += marg < 1e-3
                    cont[f'{etapa}_margem_lt_1e-3_com_arvores'] += marg < 1e-3 and arvores
                    if meio is not None:
                        cont[f'{etapa}_contagem_a_menos_1e-6_do_meio'] += meio < 1e-6
    with open(saida / 'MARGENS_DECISOES.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0])); w.writeheader(); w.writerows(linhas)
    (saida / 'MARGENS_RESUMO.json').write_text(json.dumps(dict(sorted(cont.items())), indent=1), encoding='utf-8')
    print(json.dumps(dict(sorted(cont.items())), indent=1))


if __name__ == '__main__':
    main(*sys.argv[1:])
