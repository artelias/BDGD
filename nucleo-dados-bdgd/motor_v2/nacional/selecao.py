"""Choice policy shared by the territorial (Level A) and distributor (Level B) engines.

Three different things are kept apart:
  melhor_modelo_experimental  the candidate with the best retrospective score that is also STABLE: it beats the best baseline by
                              >= 5% on the robust score (mean + std of the per-origin MAE), and is not worse than that baseline in
                              ANY origin, on exactly the same test keys. A trend baseline may be the experimental choice when it
                              beats persistence the same way. With fewer than 2 origins nothing is stable.
  modelo_homologado           only when every scientific requirement holds; with 2 independent origins (< 3 required) it is
                              always empty here, whatever the scores say.
  modelo_fallback             the best MEASURED baseline (persistence, drift or CAGR); persistence by policy when nothing was
                              measured. It is what projects when the experimental choice is unstable or absent.
`persistencia_superior_empiricamente` is true only when persistence has the lowest measured score; a persistence fallback that
results from the policy is never reported as an empirical win."""
import math

import numpy as np

BASELINES = ('persistencia', 'deriva', 'cagr')
MIN_GAIN = 0.05
MIN_ORIGINS_STABLE = 2
MIN_ORIGINS_HOMOLOGATION = 3


def metrics(pairs):
    """pairs: [(origin, actual, pred)] -> MAE/RMSE/WAPE/bias + per-origin MAE + robust score."""
    if not pairs:
        return None
    a = np.array([p[1] for p in pairs], float); f = np.array([p[2] for p in pairs], float); e = f - a
    by = {}
    for o, x, y in pairs:
        by.setdefault(o, []).append(abs(y - x))
    per = {o: float(np.mean(v)) for o, v in sorted(by.items())}
    return dict(n=len(pairs), origens=len(per), mae=float(np.mean(abs(e))), rmse=float(np.sqrt(np.mean(e * e))), vies=float(np.mean(e)),
                wape=float(abs(e).sum() / abs(a).sum()) if abs(a).sum() else None, mae_por_origem=per,
                robusto=float(np.mean(list(per.values())) + np.std(list(per.values()))))


def choose(cands):
    """cands: {name: dict(kind='baseline'|'ml', keys=set, m=metrics|None, fallback_share=float|None)}.
    `name` for baselines is the bare baseline id. Returns the decision record."""
    base = cands.get('persistencia')
    keys = base['keys'] if base and base.get('m') else set()
    measured = {k: v for k, v in cands.items() if v.get('m') and keys and v['keys'] == keys}
    bl = {k: v for k, v in measured.items() if v['kind'] == 'baseline'}
    ml = {k: v for k, v in measured.items() if v['kind'] == 'ml'}
    best_b = min(bl, key=lambda k: (bl[k]['m']['robusto'], k != 'persistencia')) if bl else None
    best_m = min(ml, key=lambda k: (ml[k]['m']['robusto'], k)) if ml else None
    origins = measured[best_b]['m']['origens'] if best_b else 0
    out = dict(melhor_baseline=best_b, score_melhor_baseline=bl[best_b]['m']['robusto'] if best_b else None,
               melhor_ml=best_m, score_melhor_ml=ml[best_m]['m']['robusto'] if best_m else None,
               ganho_ml_vs_melhor_baseline=_gain(ml.get(best_m), bl.get(best_b)), ganho_ml_vs_persistencia=_gain(ml.get(best_m), bl.get('persistencia')),
               origens=origins, candidatos_medidos=len(measured), candidatos_total=len(cands))
    best_all = min(measured, key=lambda k: (measured[k]['m']['robusto'], k != 'persistencia')) if measured else None
    out['persistencia_superior_empiricamente'] = best_all == 'persistencia'
    exp, why = None, None
    if not measured:
        why = 'nenhuma avaliacao retrospectiva possivel (sem par de competencias comparaveis no conjunto de teste)'
    elif origins < MIN_ORIGINS_STABLE:
        why = f'{origins} origem: estabilidade entre origens nao verificavel'
    else:
        if best_m and _stable(ml[best_m], bl[best_b]):
            exp, why = best_m, f'ML >= {MIN_GAIN:.0%} melhor que o melhor baseline ({best_b}) no score robusto e nao pior em nenhuma origem'
        elif best_b != 'persistencia' and 'persistencia' in bl and _stable(bl[best_b], bl['persistencia']) and (bl[best_b].get('fallback_share') or 0) < .5:
            exp, why = best_b, f'tendencia >= {MIN_GAIN:.0%} melhor que a persistencia e nao pior em nenhuma origem'
        elif best_m and out['ganho_ml_vs_melhor_baseline'] is not None and out['ganho_ml_vs_melhor_baseline'] > 0:
            why = 'melhor ML supera o melhor baseline, mas sem ganho >= 5% ou pior em alguma origem (instavel)'
        else:
            why = 'nenhum candidato supera o melhor baseline com estabilidade'
    out.update(melhor_modelo_experimental=exp, motivo_experimental=why,
               modelo_fallback=best_b or 'persistencia', motivo_fallback='melhor baseline medido' if best_b else 'persistencia por politica (nada medido)',
               modelo_projecao=exp or best_b or 'persistencia',
               base_da_projecao='melhor_modelo_experimental' if exp else 'modelo_fallback',
               modelo_homologado=None,
               motivo_nao_homologado=f'{origins} origem(ns) independente(s) < {MIN_ORIGINS_HOMOLOGATION} exigidas; point-in-time sem vintage comprovada')
    return out


def _gain(a, b):
    if not a or not b or not b['m']['robusto']:
        return None
    return 1 - a['m']['robusto'] / b['m']['robusto']


def _stable(c, ref):
    """>= MIN_GAIN better on the robust score and not worse than `ref` in any origin."""
    if c['m']['robusto'] >= (1 - MIN_GAIN) * ref['m']['robusto']:
        return False
    po, pr = c['m']['mae_por_origem'], ref['m']['mae_por_origem']
    return set(po) == set(pr) and all(po[o] <= pr[o] + 1e-12 for o in po)


def finite(x):
    return x is not None and isinstance(x, (int, float)) and math.isfinite(x)
