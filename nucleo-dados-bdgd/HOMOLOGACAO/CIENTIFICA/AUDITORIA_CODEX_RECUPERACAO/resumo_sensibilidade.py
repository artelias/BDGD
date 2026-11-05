"""Resume a sensibilidade por cenário, separando o efeito na opção A (decisões P1) e na opção B (escolhas por série).

Uso: python resumo_sensibilidade.py <dir_sensibilidade> <produto_referencia.json> <saida_json>
"""
import csv
import glob
import json
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]


def main(pasta, referencia, saida):
    ref = json.loads(Path(referencia).read_text(encoding='utf-8'))
    pub = {(m['conceito'], m['metrica']): m for m in json.loads((RAIZ / 'web/public/data/previsoes/cenarios-motor.json').read_text(encoding='utf-8'))['metricas']}
    refm = {(m['conceito'], m['metrica']): m for m in ref['metricas']}
    out = {}
    for f in sorted(glob.glob(str(Path(pasta) / 'SENSIBILIDADE_*.json'))):
        nome = Path(f).stem.replace('SENSIBILIDADE_', '')
        if nome in ('X', 'X_RESUMO'):
            continue
        d = json.loads(Path(f).read_text(encoding='utf-8'))
        c = Counter()
        cs = Path(f).with_suffix('.csv')
        for r in (csv.DictReader(cs.open(encoding='utf-8')) if cs.exists() else []):
            k = (r['conceito'], r['metrica'])
            pm, s = pub[k], refm[k]['series'][r['DIST']]
            e = s['extremos'][r['lado']]
            a_ref = bool(e and e['categoria'] == 'A_PUBLICADO_MANTIDO')
            a_cen = r['modelo'] == pm['cenarios'][r['lado']] and r['modelo'] != ''
            c['A_decisao_mudou'] += a_ref != a_cen
            c['B_modelo_mudou'] += r['modelo'] != r['modelo_ref']
            c['B_classe_mudou'] += r['classe'] != r['classe_ref']
            if r['max_dif_absoluta']:
                da, dr = float(r['max_dif_absoluta']), float(r['max_dif_relativa'])
                disc = pm.get('natureza', 'discrete_count') == 'discrete_count'
                fora = dr > 0.005 and (da > 1 if disc else da > 1e-4)   # tolerância de cenarios.comparar_produtos
                c['B_valor_fora_tolerancia_check' if fora else 'B_valor_dentro_tolerancia_check'] += 1
        res = d['resumo']
        out[nome] = dict(tipo='realista' if nome == 'libm' or nome.startswith('ruido') else 'estresse_desfaz_duplicatas',
                         escolha_agregada_diferente=res.get('escolha_agregada_diferente', 0), max_dif_wape=res.get('max_dif_wape_x1e9', 0) / 1e9,
                         **{k: c[k] for k in ('A_decisao_mudou', 'B_modelo_mudou', 'B_classe_mudou', 'B_valor_fora_tolerancia_check', 'B_valor_dentro_tolerancia_check')})
    Path(saida).write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
    for k, v in out.items():
        print(k, v)


if __name__ == '__main__':
    main(*sys.argv[1:])
