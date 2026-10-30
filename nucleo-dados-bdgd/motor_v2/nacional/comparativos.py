"""National comparisons (Level A): every asset x batch of <=16 target DIST, pools drawn from the whole national panel.

    python -m motor_v2.nacional.comparativos [--parallel 2]

Each (asset, batch) is one `python -m motor_v2.runner --config` process (the existing executor: lock, status, checkpoints per
candidate, STOP file). At most `parallel` comparison processes run at once (CPU-bound, ~0.5 GB each, no DuckDB extraction). A
process that does not end `completed` is retried once with the same config (its valid checkpoints are reused); a second failure
is recorded and the remaining batches go on."""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from . import BATCH, GROUPS, LEVEL_A, ROOT_OUT
from .painel import PANEL, dists_with
from ..runner import ROOT, atomic, read

OUT = ROOT_OUT / 'comparativos'
EXTERNAL = 'D:/NUCLEO_BDGD_2025/motor_v2/externals/versions/810b13c6844f36d6/manifest.json'
ALIAS = {'ucbt_quantidade': 'ucbt', 'trafo_dist_quantidade': 'trafo_qty', 'trafo_dist_potencia_kva': 'trafo_kva',
         'rede_mt_extensao_km': 'rede_mt', 'rede_bt_extensao_km': 'rede_bt'}


def grupos():
    g = json.loads(Path(GROUPS).read_text(encoding='utf-8'))
    return {str(d): x['grupo_id'] for x in g['grupos'] for d in x['dists']}


def configs(quarantine, valid_municipalities):
    out = []
    gr = grupos()
    for asset in LEVEL_A:
        pool = dists_with(asset, 1)
        targets = dists_with(asset, 2)            # at least one transition is needed for any backtest
        for i in range(0, len(targets), BATCH):
            bid = f'{ALIAS[asset]}-{i // BATCH + 1:02d}'
            cfg = dict(output=str(OUT / ALIAS[asset] / bid), comparison_input=str(PANEL), experiment='comparison', dists=targets[i:i + BATCH],
                       pool='nacional', pool_dists=pool, grupos={str(d): gr.get(str(d), 'nao_confirmado') for d in pool}, batch_id=bid,
                       memory='512MB', threads=1, models=['ols', 'ridge', 'elastic_net', 'poisson', 'random_forest', 'hist_gradient_boosting'],
                       max_trials=6, seconds_per_candidate=400, territorial_folds=3, min_independent_origins=3, origins=[2023, 2024], seed=42,
                       external_manifest=EXTERNAL, bridges_dir=str(ROOT / 'motor_v2/bridges'), forward_selection=True, max_features=4,
                       min_territorial_coverage=0.98, baseline_min_points=2, asset=asset, rounding_policy='half_up',
                       valid_municipalities=str(valid_municipalities), quarantine=quarantine, enable_recent_connection_share=False)
            if asset != 'ucbt_quantidade':
                cfg['shared_inputs'] = dict(asset_root=str(PANEL), ucbt_root=str(PANEL))
            if asset in ('rede_mt_extensao_km', 'rede_bt_extensao_km'):
                cfg['min_unit_continuity'] = 0.95
            out.append(cfg)
    return out


def launch(cfg):
    path = Path(cfg['output']); path.mkdir(parents=True, exist_ok=True)
    atomic(path / 'nacional_config.json', cfg)
    log = open(path / 'processo.log', 'ab')
    return subprocess.Popen([sys.executable, '-u', '-m', 'motor_v2.runner', '--config', str(path / 'nacional_config.json')], cwd=ROOT,
                            stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL), log


def state(cfg):
    p = Path(cfg['output']) / 'status.json'
    return read(p) if p.exists() else {}


def run(parallel=2):
    OUT.mkdir(parents=True, exist_ok=True)
    q = read(ROOT_OUT / 'quarentena.json')
    cfgs = configs(q['quarentena'], q['municipios_validos'])
    status = OUT / 'STATUS.json'
    rec = dict(total=len(cfgs), lotes={c['batch_id']: dict(ativo=c['asset'], dists=c['dists'], tentativas=0) for c in cfgs})
    pending = list(cfgs); running = {}
    t0 = time.monotonic()
    while pending or running:
        if (OUT / 'STOP').exists():
            for p, _ in running.values():
                p.wait()
            rec['estado'] = 'interrompido'; atomic(status, rec); return rec
        while pending and len(running) < parallel:
            c = pending.pop(0)
            if state(c).get('state') == 'completed' and Path(state(c).get('output', '')).joinpath('summaries.json').exists():
                rec['lotes'][c['batch_id']].update(estado='completed', reaproveitado=True, output=state(c)['output']); continue
            rec['lotes'][c['batch_id']]['tentativas'] += 1
            rec['lotes'][c['batch_id']]['inicio'] = time.strftime('%Y-%m-%dT%H:%M:%S')
            running[c['batch_id']] = (launch(c), c)
        time.sleep(15)
        for bid in list(running):
            (proc, log), c = running[bid]
            if proc.poll() is None:
                continue
            log.close(); del running[bid]
            st = state(c); r = rec['lotes'][bid]
            r.update(estado=st.get('state'), output=st.get('output'), returncode=proc.returncode, fim=time.strftime('%Y-%m-%dT%H:%M:%S'))
            if st.get('state') != 'completed' and r['tentativas'] < 2:
                pending.append(c)
        rec['segundos'] = round(time.monotonic() - t0, 1)
        rec['concluidos'] = sum(1 for r in rec['lotes'].values() if r.get('estado') == 'completed')
        atomic(status, rec)
    rec['estado'] = 'concluido' if rec['concluidos'] == rec['total'] else 'concluido_com_falhas'
    atomic(status, rec)
    return rec


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--parallel', type=int, default=2)
    print(json.dumps(run(ap.parse_args().parallel), ensure_ascii=False)[:3000])
