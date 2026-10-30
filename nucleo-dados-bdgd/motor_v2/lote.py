"""Controlled validation batch: extraction -> comparison -> report, resumable and deterministic (no national processing).

    python -m motor_v2.lote --manifest motor_v2/lotes/lote-validacao-1.json

Stages reuse the existing executors and their checkpoints: UCBT through runner.execute (one subprocess per DIST, time budget,
RAM guard, annual checkpoints), the other assets through assets.execute, and one comparison per asset through runner.execute with
pool='lote'. Re-running an unchanged manifest reuses every valid checkpoint. A STOP file in the output directory stops between
stages. Only ordinary publications (contract selection) are read; outputs stay under D:/NUCLEO_BDGD_2025/motor_v2."""
import argparse
import json
import time
from pathlib import Path

from .runner import ROOT, atomic, read

DIST_LIMIT = 16
ALIAS = {'ucbt_quantidade': 'ucbt', 'trafo_dist_quantidade': 'trafo_qty', 'trafo_dist_potencia_kva': 'trafo_kva', 'rede_mt_extensao_km': 'rede_mt'}


def _stage(log, name, fn):
    t = time.monotonic()
    log.append(dict(stage=name, started=time.strftime('%Y-%m-%dT%H:%M:%S')))
    result = fn()
    log[-1].update(seconds=round(time.monotonic() - t, 1), result=str(result))
    return result


def run(manifest_path):
    m = read(manifest_path)
    if len(m['dists']) > DIST_LIMIT:
        raise ValueError('batch above the controlled limit; national processing is not authorised by this entry point')
    out = Path(m['output'])
    if out.drive.upper() != 'D:':
        raise ValueError('output must be on D:')
    out.mkdir(parents=True, exist_ok=True)
    stop = out / 'STOP'
    log, status = [], out / 'lote_status.json'

    def save(state):
        atomic(status, dict(lote=m['id'], state=state, stages=log))

    # 1. UCBT (original executor, subprocess per DIST)
    from . import runner
    ucfg = dict(output=str(out / 'ucbt'), dists=m['dists'], memory=m['memory'], threads=m['threads'], min_folds=3, as_of='2026-10-28',
                scenario_rates=[0, 0, 0], seed=m['seed'], max_trials=8, task_timeout_seconds=m['task_timeout_seconds'],
                min_available_gb=m['min_available_gb'], lote=m['id'])
    (out / 'ucbt').mkdir(exist_ok=True)
    atomic(out / 'ucbt' / 'lote_config.json', ucfg)
    save('ucbt')
    _stage(log, 'extracao_ucbt', lambda: runner.execute(ucfg))
    ust = read(out / 'ucbt' / 'status.json')
    if ust['state'] not in ('completed', 'completed_with_errors'):
        save('failed'); raise RuntimeError('UCBT stage did not complete: ' + ust['state'])
    ucbt_root = ust['output']
    if stop.exists():
        save('stopped'); return out

    # 2. Other assets (bounded DuckDB, annual checkpoints)
    from . import assets
    acfg = dict(output=str(out / 'assets'), dists=m['dists'], assets=[a for a in m['ativos'] if a != 'ucbt_quantidade'],
                memory=m['memory'], threads=m['threads'], min_available_gb=m['min_available_gb'])
    save('assets')
    asset_root = str(_stage(log, 'extracao_ativos', lambda: assets.execute(acfg)))
    if stop.exists():
        save('stopped'); return out

    # 3. Comparisons (pool = this batch)
    c = m['comparison']
    comparisons = []
    for asset in m['ativos']:
        if stop.exists():
            save('stopped'); return out
        cfg = dict(output=str(out / 'comparativo' / ALIAS[asset]), comparison_input=ucbt_root if asset == 'ucbt_quantidade' else asset_root,
                   experiment='comparison', dists=m['dists'], pool='lote', lote=dict(id=m['id'], dists=m['dists'], grupos=m['grupos']),
                   memory=m['memory'], threads=m['threads'], models=c['models'], max_trials=c['max_trials'],
                   seconds_per_candidate=c['seconds_per_candidate'], territorial_folds=c['territorial_folds'],
                   min_independent_origins=c['min_independent_origins'], origins=c['origins'], seed=m['seed'],
                   external_manifest=c['external_manifest'], bridges_dir=str(ROOT / 'motor_v2/bridges'), forward_selection=c['forward_selection'],
                   max_features=c['max_features'], min_territorial_coverage=c['min_territorial_coverage'], baseline_min_points=c['baseline_min_points'],
                   asset=asset, rounding_policy=c['rounding_policy'])
        if asset != 'ucbt_quantidade':
            cfg['shared_inputs'] = dict(asset_root=asset_root, ucbt_root=ucbt_root)
        if asset == 'rede_mt_extensao_km':
            cfg['min_unit_continuity'] = c['min_unit_continuity_rede_mt']
        Path(cfg['output']).mkdir(parents=True, exist_ok=True)
        atomic(Path(cfg['output']) / 'lote_config.json', cfg)
        save('comparativo_' + ALIAS[asset])
        _stage(log, 'comparativo_' + ALIAS[asset], lambda cfg=cfg: runner.execute(cfg))
        st = read(Path(cfg['output']) / 'status.json')
        if st.get('state') != 'completed':
            save('failed'); raise RuntimeError(f"comparison {asset} ended {st.get('state')}")
        comparisons.append(st['output'])

    # 4. Report
    from . import report_lote
    save('relatorio')
    _stage(log, 'relatorio', lambda: report_lote.main(m['id'], comparisons, out / 'relatorio', m['grupos'])[1].__len__())
    atomic(out / 'lote_manifest_efetivo.json', dict(manifest=m, ucbt_root=ucbt_root, asset_root=asset_root, comparisons=comparisons))
    save('completed')
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    print(run(ap.parse_args().manifest))
