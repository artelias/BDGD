"""National extraction in batches of <=16 DIST, resumable, one heavy worker at a time.

    python -m motor_v2.nacional.extracao [--wait-pid PID] [--batches nac-01 nac-02]

Per batch: UCBT through runner.execute (one subprocess per DIST, RAM guard, 1 h budget, annual checkpoints), then the other
Level-A assets through assets.execute (failures per DIST/asset are caught and counted). After each batch an integrity record
is written: per DIST x asset x year whether it was extracted, why not, the contract item used (must be ORDINARY), coverage,
the difference to the national contract cell, and the SHA-256 of every aggregate. A localized failure never stops the run;
a systemic one does (more than half of a batch without any UCBT year, or a non-ordinary item read): then the run stops with
the blocker recorded instead of carrying on blindly. `completed_with_errors` is never counted as complete."""
import argparse
import csv
import json
import os
import time
from collections import Counter
from pathlib import Path

import psutil

from . import BATCH, CONTRACT, LEVEL_A, ROOT_OUT
from .. import extraordinary as ex
from ..runner import atomic, read

OUT = ROOT_OUT / 'extracao'
INVENTORY = Path('D:/NUCLEO_BDGD_2025/motor_v2/inventario_v2/INVENTARIO_PUBLICACOES_LOCAIS.csv')
MEMORY, THREADS, MIN_FREE_GB = '512MB', 2, 0.75


def eligible():
    """DIST with at least one competence whose `consumidores` cell is observed in the national contract."""
    by = {}
    with open(CONTRACT, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            d = by.setdefault(int(r['dist']), dict(empresa=r['empresa'], observed=set(), cells=Counter()))
            if r['conceitoId'] == 'consumidores':
                d['cells'][r['estado']] += 1
                if r['estado'] == 'observado':
                    d['observed'].add(int(r['ano']))
    return {k: dict(empresa=v['empresa'], anos_observados=sorted(v['observed']), estados=dict(v['cells'])) for k, v in by.items()}


def batches(dists):
    ds = sorted(dists)
    return {f'nac-{i // BATCH + 1:02d}': ds[i:i + BATCH] for i in range(0, len(ds), BATCH)}


def wait_ram(floor, limit_s=3600):
    t = time.monotonic()
    while psutil.virtual_memory().available / 2**30 < floor:
        if time.monotonic() - t > limit_s:
            raise MemoryError(f'available RAM stayed below {floor} GiB for {limit_s} s')
        time.sleep(30)


def _hist(root, dist, asset):
    p = Path(root) / str(dist) / asset / 'result.json'
    return read(p) if p.exists() else None


def integrity(batch_id, dists, ucbt_root, asset_root, inventory):
    rows, used = [], set()
    for dist in dists:
        for asset in LEVEL_A:
            root = ucbt_root if asset == 'ucbt_quantidade' else asset_root
            res = _hist(root, dist, asset) if root else None
            if res is None:
                for y in range(2022, 2026):
                    rows.append(dict(lote=batch_id, DIST=dist, ativo=asset, ano=y, status='falha_sem_resultado', motivo='result.json ausente (falha do worker ou do lote)'))
                continue
            errs = {q['year']: q['error'] for q in res.get('quality', []) if 'error' in q}
            got = {h['year']: h for h in res['history']}
            for y in range(2022, 2026):
                h = got.get(y)
                if h is None or h.get('value') is None and asset != 'ucbt_quantidade' and h['qa'].get('error'):
                    why = errs.get(y) or (h['qa'].get('error') if h else None) or 'ano nao extraido'
                    rows.append(dict(lote=batch_id, DIST=dist, ativo=asset, ano=y, status='indisponivel', motivo=why))
                    continue
                qa, src = h['qa'], h.get('source') or {}
                item = src.get('item')
                used.add(item)
                f = Path(root) / str(dist) / asset / str(y) / 'territorial.parquet'
                ck = Path(root) / str(dist) / asset / str(y) / 'checkpoint.json'
                rows.append(dict(lote=batch_id, DIST=dist, ativo=asset, ano=y, status='extraido' if h.get('value') is not None else 'extraido_sem_valor_valido',
                                 motivo=None if h.get('value') is not None else 'regra de qualidade do extrator (cobertura de vinculo/potencia invalida/duplicidade)',
                                 item=item, natureza=inventory[item].natureza if item in inventory else 'desconhecida', valor=h.get('value'),
                                 cobertura=qa.get('coverage'), valor_contrato=qa.get('contract_value'), diferenca_vs_contrato=qa.get('difference_vs_contract'),
                                 ruptura_contrato=h.get('rupture'), disponivel_em=h.get('available'),
                                 sha256_agregado=read(ck)['output_sha256'] if ck.exists() else None))
    bad = sorted(i for i in used if i not in inventory or inventory[i].natureza != ex.ORDINARY)
    no_ucbt = sorted({r['DIST'] for r in rows if r['ativo'] == 'ucbt_quantidade'} - {r['DIST'] for r in rows if r['ativo'] == 'ucbt_quantidade' and r['status'] == 'extraido'})
    systemic = []
    if bad:
        systemic.append('itens nao ordinarios lidos: ' + ','.join(bad))
    if len(no_ucbt) > len(dists) / 2:
        systemic.append(f'{len(no_ucbt)} de {len(dists)} DIST sem nenhum ano UCBT extraido')
    return rows, dict(lote=batch_id, dists=dists, celulas=len(rows), status=dict(Counter(r['status'] for r in rows)),
                      dist_sem_ucbt=no_ucbt, itens_lidos=len(used), itens_nao_ordinarios=bad, falha_sistemica=systemic)


def write_csv(path, rows):
    if not rows:
        return
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        w.writerows({k: ('' if v is None else v) for k, v in r.items()} for r in rows)


def run(wait_pid=None, only=None):
    OUT.mkdir(parents=True, exist_ok=True)
    if wait_pid:
        while psutil.pid_exists(wait_pid):      # one heavy worker at a time: let the ZIP conversion finish first
            time.sleep(30)
    from .. import assets, runner
    inventory = ex.load(INVENTORY)
    elig = eligible()
    dists = [d for d, v in elig.items() if v['anos_observados']]
    plan = batches(dists)
    status_path = OUT / 'STATUS.json'
    state = read(status_path) if status_path.exists() else {}
    state.update(plano=plan, inventario_contrato=dict(dist_no_contrato=len(elig), dist_com_algum_ano_observado=len(dists),
                                                      sem_ano_observado=sorted(d for d, v in elig.items() if not v['anos_observados'])),
                 lotes=state.get('lotes', {}))
    atomic(status_path, state)
    for batch_id, ds in plan.items():
        if only and batch_id not in only:
            continue
        if (OUT / 'STOP').exists():
            state['estado'] = 'interrompido_por_STOP'; atomic(status_path, state); return state
        t0 = time.monotonic()
        rec = dict(dists=ds, inicio=time.strftime('%Y-%m-%dT%H:%M:%S'), etapas={})
        state['lotes'][batch_id] = rec; state['estado'] = 'executando:' + batch_id; atomic(status_path, state)
        bdir = OUT / batch_id
        ucfg = dict(output=str(bdir / 'ucbt'), dists=ds, memory=MEMORY, threads=THREADS, min_folds=3, as_of='2026-10-30', scenario_rates=[0, 0, 0],
                    seed=42, max_trials=8, task_timeout_seconds=3600, min_available_gb=MIN_FREE_GB, lote=batch_id)
        ucbt_root = None
        try:
            wait_ram(MIN_FREE_GB)
            runner.execute(ucfg)
            ust = read(bdir / 'ucbt' / 'status.json')
            ucbt_root = ust.get('output')
            failed = sorted(int(p.stem.split('_')[1]) for p in Path(ucbt_root).glob('failure_*.json'))
            if failed:      # one retry of the failed DIST only (e.g. RAM momentarily short); a second failure is final
                wait_ram(MIN_FREE_GB)
                retry = dict(ucfg, dists=failed, output=str(bdir / 'ucbt_retry'))
                runner.execute(retry)
                rst = read(bdir / 'ucbt_retry' / 'status.json')
                rec['etapas']['ucbt_retry'] = dict(state=rst.get('state'), dists=failed, root=rst.get('output'))
                for d in failed:
                    src = Path(rst['output']) / str(d)
                    if (src / 'ucbt_quantidade' / 'result.json').exists():
                        rec.setdefault('ucbt_retry_ok', []).append(d)
            rec['etapas']['ucbt'] = dict(state=ust.get('state'), completed=ust.get('completed'), total=ust.get('total'), root=ucbt_root,
                                         falhas=failed, segundos=round(time.monotonic() - t0, 1))
        except Exception as e:
            rec['etapas']['ucbt'] = dict(state='failed', error=str(e))
        t1 = time.monotonic()
        asset_root = None
        try:
            wait_ram(MIN_FREE_GB)
            acfg = dict(output=str(bdir / 'assets'), dists=ds, assets=[a for a in LEVEL_A if a != 'ucbt_quantidade'], memory=MEMORY,
                        threads=THREADS, min_available_gb=MIN_FREE_GB)
            asset_root = str(assets.execute(acfg))
            am = read(Path(asset_root) / 'manifest.json')
            rec['etapas']['ativos'] = dict(state='completed' if not am['failures'] else 'completed_with_errors', root=asset_root,
                                           falhas=am['failures'], stats=am['stats'], segundos=round(time.monotonic() - t1, 1))
        except Exception as e:
            rec['etapas']['ativos'] = dict(state='failed', error=str(e))
        cells, summary = integrity(batch_id, ds, ucbt_root, asset_root, inventory)
        # retried DIST: integrity is read from the retry root for UCBT
        for d in rec.get('ucbt_retry_ok', []):
            rcells, _ = integrity(batch_id, [d], rec['etapas']['ucbt_retry']['root'], None, inventory)
            cells = [c for c in cells if not (c['DIST'] == d and c['ativo'] == 'ucbt_quantidade')] + [c for c in rcells if c['ativo'] == 'ucbt_quantidade']
        write_csv(bdir / 'INTEGRIDADE.csv', cells)
        rec.update(integridade=summary, fim=time.strftime('%Y-%m-%dT%H:%M:%S'), segundos=round(time.monotonic() - t0, 1))
        rec['estado'] = 'concluido' if all(e.get('state') == 'completed' for k, e in rec['etapas'].items() if k in ('ucbt', 'ativos')) \
            else 'concluido_com_falhas_localizadas' if not summary['falha_sistemica'] else 'bloqueado'
        atomic(status_path, state)
        if summary['falha_sistemica']:
            state['estado'] = 'bloqueado:' + batch_id; state['bloqueio'] = summary['falha_sistemica']; atomic(status_path, state)
            return state
    state['estado'] = 'concluido'; atomic(status_path, state)
    return state


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--wait-pid', type=int); ap.add_argument('--batches', nargs='*')
    print(json.dumps(run(ap.parse_args().wait_pid, set(ap.parse_args().batches or [])), ensure_ascii=False)[:2000])
