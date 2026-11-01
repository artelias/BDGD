"""Results of a validation batch, per DIST x asset x metric x mode x candidate (reads comparison outputs; recomputes nothing).

    python -m motor_v2.report_lote --lote lote-validacao-1 --comparisons <dir> [<dir> ...] --output <dir>

Effective sample sizes are reported as they are: test predictions and territorial units are many, but independent temporal
origins are what a temporal validation rests on. With fewer than 3 origins nothing is called validated; every row is
experimental. Counts are written as integers; continuous errors keep their decimals."""
import argparse
import csv
import json
from pathlib import Path

from .baselines import BASELINES

MIN_ORIGINS = 3
FUNCOES = {
    'persistencia': 'y(T+1) = y(T)',
    'deriva': 'y(T+1) = y(T) + (y(T) - y(T0)) / (T - T0)',
    'cagr': 'y(T+1) = y(T) * (y(T) / y(T0)) ** (1 / (T - T0))',
    'ols': 'regressão linear sobre features padronizadas em t-1 (alvo: estoque em t)',
    'ridge': 'regressão linear com penalização L2 sobre features padronizadas em t-1',
    'elastic_net': 'regressão linear com penalização L1+L2 sobre features padronizadas em t-1',
    'poisson': 'GLM Poisson com ligação log (contagens) sobre features padronizadas em t-1',
    'random_forest': 'floresta aleatória (64 árvores) sobre features em t-1',
    'hist_gradient_boosting': 'gradient boosting por histogramas (80 iterações) sobre features em t-1',
}
ESCOPOS = {'individual': 'individual (só a própria DIST)', 'shared_lote': 'global do lote', 'group_lote': 'compartilhado no grupo econômico',
           'peers_lote': '3 DIST mais semelhantes (estoque/urbanização no treino)', 'shared_pilot': 'pool do piloto', 'peers_pilot': 'par mais semelhante do piloto'}


def _read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def rows_for(comparison_dir, grupos):
    cdir = Path(comparison_dir)
    coverage = _read(cdir / 'coverage.json')
    out, resumo = [], []
    for summary in _read(cdir / 'summaries.json'):
        dist = summary['dist']
        cov = [q for q in coverage if q['dist'] == dist]
        tcov = [q['territorial_coverage'] for q in cov if q.get('territorial_coverage') is not None]
        cand = {c['candidate']: c for c in summary['candidates']}
        base_scores = {b: cand.get(b + ':individual', {}).get('robust_score') for b in BASELINES}
        for c in summary['candidates']:
            model, scope = c['candidate'].split(':', 1)
            folds = c.get('folds', [])
            params = sorted({json.dumps(f.get('params', {}), sort_keys=True) for f in folds})
            feats = sorted({x for f in folds for x in f.get('selected_features', [])})
            peers = sorted({d for f in folds for d in (f.get('peers') or [])})
            origins = c.get('independent_origins') or 0
            m = c.get('metrics') or {}
            phys = ((c.get('physical') or {}).get('independent') or {}).get('physical') or {}
            rs = c.get('robust_score')
            row = dict(
                lote=None, DIST=dist, grupo=grupos.get(str(dist), ''), ativo=summary['asset'], metrica=summary['metric'], unidade=summary['unit'],
                natureza=summary['nature'], modo=summary['mode'], rotulo=summary['evaluation_label'], candidato=c['candidate'], modelo=model,
                escopo=ESCOPOS.get(scope, scope), funcao=FUNCOES.get(model, model), parametros=' | '.join(params) if params else '{}',
                features=' | '.join(feats), dist_no_treino=len(peers) or (1 if folds else 0), observacoes_treino_max=max((f.get('train_n', 0) for f in folds), default=0),
                unidades_treino_max=max((f.get('train_territories', 0) for f in folds), default=0), previsoes_teste=c.get('n_predictions') or 0,
                unidades_teste_por_origem=round((c.get('n_predictions') or 0) / origins) if origins else 0,
                origens_independentes=origins, periodos_alvo='2023-2025' if origins >= 2 else ('2024' if origins == 1 else ''),
                validacao_temporal='sim' if origins >= MIN_ORIGINS else f'não ({origins} origem(ns) < {MIN_ORIGINS})',
                mae=m.get('mae'), rmse=m.get('rmse'), vies=m.get('bias'), wape=m.get('wape'),
                mae_fisico=phys.get('mae') if summary['nature'] == 'discrete_count' else None,
                wape_total_distribuidora=(c.get('distributor_metrics') or {}).get('wape'), score_robusto=rs,
                **{f'ganho_vs_{b}': (1 - rs / base_scores[b]) if rs is not None and base_scores.get(b) else None for b in BASELINES},
                conjunto_de_teste_comum=c.get('common_test_set'),
                cobertura_territorial_min=min(tcov) if tcov else None,
                falhas=len(c.get('failures') or []),
                status='experimental' if origins < MIN_ORIGINS or not summary.get('validated_winner') else 'validado_temporalmente_sem_homologacao')
            out.append(row)
        best_ml = cand.get(summary.get('best_ml') or '', {})
        resumo.append(dict(lote=None, DIST=dist, grupo=grupos.get(str(dist), ''), ativo=summary['asset'], metrica=summary['metric'],
                           natureza=summary['nature'], modo=summary['mode'], vencedor=summary['winner'], motivo=summary['selection_reason'],
                           melhor_baseline=summary.get('best_baseline'), melhor_ml=summary.get('best_ml'),
                           ganho_ml_vs_melhor_baseline=summary.get('ml_gain_vs_best_baseline'), ganho_ml_vs_persistencia=summary.get('ml_gain_vs_persistence'),
                           origens=best_ml.get('independent_origins') or max((c.get('independent_origins') or 0 for c in summary['candidates']), default=0),
                           previsoes_teste=best_ml.get('n_predictions') or 0, validado=bool(summary.get('validated_winner')),
                           status='experimental'))
    return out, resumo


def write(rows, path):
    if not rows:
        return
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        for r in rows:
            w.writerow({k: ('' if v is None else v) for k, v in r.items()})


def main(lote, comparisons, output, grupos):
    allrows, allres = [], []
    for c in comparisons:
        r, s = rows_for(c, grupos)
        allrows += r; allres += s
    for r in allrows + allres:
        r['lote'] = lote
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    write(allrows, out / 'RESULTADOS_LOTE.csv')
    write(allres, out / 'RESUMO_LOTE.csv')
    return allrows, allres


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--lote', required=True); ap.add_argument('--comparisons', nargs='+', required=True); ap.add_argument('--output', required=True)
    ap.add_argument('--manifest', help='batch manifest with grupos')
    a = ap.parse_args()
    grupos = _read(a.manifest).get('grupos', {}) if a.manifest else {}
    rows, res = main(a.lote, a.comparisons, a.output, grupos)
    print(len(rows), 'linhas;', len(res), 'resumos')
