"""Report per DIST x asset x metric comparing persistence, drift, CAGR and the ML algorithms, with the variables actually used.

Reads the finished comparison runs (summaries.json) and writes:
  RELATORIO_DIST_ATIVO_METRICA.csv  one row per DIST x asset x metric x validation mode
  FEATURES_UTILIZADAS.csv           how often each feature was selected (and by the best ML candidate), per asset
No claim of validation is made: `validated` is true only when the configured minimum of independent origins is met.
Usage: python -m motor_v2.report_matrix --runs name=<comparison output dir> ... --out <dir>"""
import argparse
import collections
import csv
import glob
import json
import os
from pathlib import Path

BASE = ('persistencia:individual', 'deriva:individual', 'cagr:individual')


def latest(output):
    found = sorted(glob.glob(str(Path(output) / 'comparison' / '*' / 'summaries.json')), key=os.path.getmtime)
    if not found:
        raise FileNotFoundError(output)
    return Path(found[-1])


def used(candidate):
    c = collections.Counter(f for fold in candidate['folds'] for f in fold['selected_features'])
    return c


def build(runs):
    table, features = [], []
    for name, output in runs.items():
        path = latest(output)
        manifest = json.loads((path.parent / 'manifest.json').read_text(encoding='utf-8'))
        minimum = manifest['config']['min_independent_origins']
        for s in json.loads(path.read_text(encoding='utf-8')):
            by = {c['candidate']: c for c in s['candidates']}
            row = dict(execucao=name, DIST=s['dist'], ativo=s['asset'], metrica=s['metric'], unidade=s.get('unit'), experimental=s.get('experimental_asset'),
                       modo=s['mode'], rotulo=s['evaluation_label'], origens=max((c['independent_origins'] for c in s['candidates']), default=0),
                       minimo_origens=minimum, validado=bool(s['validated_winner']))
            for b in BASE:
                c = by[b]
                row[f'{b.split(":")[0]}_robusto'] = c['robust_score']
                row[f'{b.split(":")[0]}_wape'] = (c['metrics'] or {}).get('wape')
                row[f'{b.split(":")[0]}_vies'] = (c['metrics'] or {}).get('bias')
                row[f'{b.split(":")[0]}_pontos'] = c['n_predictions']
            row['fallbacks_deriva'] = s['baseline_fallback_rows'].get('deriva:individual')
            row['fallbacks_cagr'] = s['baseline_fallback_rows'].get('cagr:individual')
            n = by['persistencia:individual']['n_predictions'] or 0
            # drift/CAGR that fell back to persistence on half or more of the rows are not independent baselines
            row['baselines_degenerados'] = bool(n and max(row['fallbacks_deriva'] or 0, row['fallbacks_cagr'] or 0) >= .5 * n)
            row['melhor_baseline'] = s['best_baseline']; row['melhor_baseline_robusto'] = s['best_baseline_robust']
            ml = by.get(s['best_ml']) if s['best_ml'] else None
            row['melhor_ml'] = s['best_ml']; row['melhor_ml_robusto'] = s['best_ml_robust']
            row['melhor_ml_wape'] = (ml['metrics'] or {}).get('wape') if ml else None
            row['melhor_ml_vies'] = (ml['metrics'] or {}).get('bias') if ml else None
            row['ganho_ml_vs_persistencia'] = s['ml_gain_vs_persistence']
            row['ganho_ml_vs_melhor_baseline'] = s['ml_gain_vs_best_baseline']
            row['ml_supera_melhor_baseline'] = s['ml_beats_best_baseline']
            row['variaveis_melhor_ml'] = json.dumps(dict(used(ml)), ensure_ascii=False) if ml else None
            row['vencedor'] = s['winner']; row['motivo'] = s['selection_reason']
            row['variaveis_externas_no_melhor_ml'] = bool(ml and any(f.startswith(('log_population', 'log_gdp', 'population_growth')) for f in used(ml)))
            table.append(row)
            if s['mode'] == 'reconciled_retrospective':
                allml = collections.Counter(); best = used(ml) if ml else collections.Counter()
                for c in s['candidates']:
                    if c['candidate'] not in BASE:
                        allml.update(used(c))
                for f in sorted(set(allml) | set(best)):
                    features.append(dict(execucao=name, DIST=s['dist'], ativo=s['asset'], metrica=s['metric'], variavel=f,
                                         selecoes_em_dobras_ml=allml.get(f, 0), selecoes_no_melhor_ml=best.get(f, 0)))
    return table, features


def write(rows, path):
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with Path(path).open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fields)
        w.writeheader(); w.writerows(rows)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs', nargs='+', required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    runs = dict(x.split('=', 1) for x in a.runs)
    table, feats = build(runs)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    write(table, out / 'RELATORIO_DIST_ATIVO_METRICA.csv'); write(feats, out / 'FEATURES_UTILIZADAS.csv')
    print(len(table), 'linhas;', len(feats), 'variaveis')
