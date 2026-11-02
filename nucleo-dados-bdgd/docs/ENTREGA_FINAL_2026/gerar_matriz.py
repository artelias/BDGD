"""Gera 02_MATRIZ_COMPLETA_MODELOS.csv a partir do produto versionado do Motor V2 (web/data-motor-v2), sem acesso a D:.

    python nucleo-dados-bdgd/docs/ENTREGA_FINAL_2026/gerar_matriz.py

Uma linha por DIST x objetivo x métrica (3.420): estado, motivo, modelo, baseline, erros, cobertura e os valores 2026-2030.
Cenário bloqueado pelo portão de plausibilidade sai com valores vazios e estado BLOQUEADO (nunca zero)."""
import csv
import json
from pathlib import Path

AQUI = Path(__file__).resolve().parent
DADOS = AQUI.parents[1] / 'web' / 'data-motor-v2'
CEN = ('Conservador', 'Moderado', 'Agressivo')
ANOS = (2026, 2027, 2028, 2029, 2030)


def main():
    ix = json.loads((DADOS / 'indice.json').read_text(encoding='utf-8'))
    linhas = []
    for d in sorted(ix['dists'], key=lambda x: x['dist']):
        j = json.loads((DADOS / 'distribuidoras' / f"{d['dist']}.json").read_text(encoding='utf-8'))
        for s in j['series']:
            m, e = s['modelo'] or {}, s['erros'] or {}
            hist = {a: v for a, v, _ in s['historico']}
            row = dict(DIST=j['dist'], empresa=j['empresa'], grupo=ix['grupos'].get(j['grupo'] or '', ''), familia=s['familia'], objetivo=s['objetivo'],
                       ativo=s['nome'], metrica=s['metrica'], unidade=s['unidade'], variante=s['variante'] or '', estado=s['estado'], classe_auditoria=s['classe'] or '',
                       motivo=s['motivo'], fonte=s['fonte'], **{f'hist_{a}': hist.get(a, '') if hist.get(a) is not None else '' for a in (2022, 2023, 2024, 2025)},
                       ano_ancora=s['ancora'] or '', horizonte_real=s['horizonte_real'] or '', modelo=m.get('id') or '', tipo_modelo=m.get('tipo') or '',
                       base_da_projecao=m.get('base_da_projecao') or '', melhor_baseline=s['melhor_baseline_medido'] or '', origens_teste=e.get('origens', ''),
                       mae=e.get('mae', ''), rmse=e.get('rmse', ''), wape=e.get('wape', ''), vies=e.get('vies', ''),
                       ganho_vs_melhor_baseline=s['ganho_vs_melhor_baseline'] if s['ganho_vs_melhor_baseline'] is not None else '',
                       coeficientes=(m.get('coeficientes') or {}).get('status', ''), cenarios_degenerados=(s['cenarios_meta'] or {}).get('degenerados', ''),
                       entra_em_totais=s['entra_em_totais'], homologado=False if m else '')
            pl = s.get('plausibilidade') or {}
            row.update(plausibilidade_severidade=pl.get('severidade') or '', plausibilidade_classe=pl.get('classe') or '',
                       **{f'estado_{c.lower()}': (s['cenarios_status'] or {}).get(c, '') for c in CEN})
            for c in CEN:
                for i, a in enumerate(ANOS):
                    row[f'{c.lower()}_{a}'] = s['cenarios'][c][i] if s['cenarios'] and s['cenarios'][c] else ''
            linhas.append(row)
    with open(AQUI / '02_MATRIZ_COMPLETA_MODELOS.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]), lineterminator='\n')
        w.writeheader(); w.writerows(linhas)
    print(len(linhas), 'linhas')


if __name__ == '__main__':
    main()
