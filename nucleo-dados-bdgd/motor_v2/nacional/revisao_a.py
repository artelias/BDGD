"""Level A revision after the experimental Celesc 2023 bridge: re-run ONLY Celesc and the comparison targets that depend on it.

    python -m motor_v2.nacional.revisao_a [--parallel 2]

Dependency (exact, per asset): the comparison of a target DIST reads other companies only through its `grupo_economico` and
`comparaveis` pools. Before the bridge, Celesc (5697) had no usable training row up to origin 2024 (2023 quarantined as target and
as t-1 feature year), and the first run recorded no fold with 5697 among its peers. So the previous state is the current panel
without Celesc's 2023/2024 rows, and a target is DEPENDENT when, for any origin, mode, territorial fold, scope, outer pool or inner
selection pool, the peer list differs between the two states (Celesc joining, or the standardised profile moving the neighbours).
Each asset gets revision batches (<=16 targets) holding Celesc + its dependants, run by the same executor (motor_v2.runner) with
the national pool; their summaries supersede the first-run summaries of those DIST only (`vigentes`)."""
import argparse
import json
import sys
import time
from pathlib import Path

from . import BATCH, LEVEL_A, ROOT_OUT
from .comparativos import ALIAS, OUT as CMP, configs, launch, state
from ..runner import atomic, read

CELESC = 5697
REV = 'rev-celesc'


def _nearest(prof, dist, k):
    """comparison.comparable() on precomputed profiles (same standardisation, urban rule and tie-break)."""
    import numpy as np
    if dist not in prof:
        return []
    use_urban = all(v[2] is not None for v in prof.values())
    keys = sorted(prof); m = np.array([[prof[d][0], prof[d][1]] + ([prof[d][2]] if use_urban else []) for d in keys], dtype=float)
    sd = m.std(axis=0); sd[sd == 0] = 1.; z = (m - m.mean(axis=0)) / sd; me = z[keys.index(dist)]
    order = sorted((float(np.linalg.norm(z[i] - me)), d) for i, d in enumerate(keys) if d != dist)
    return sorted([dist] + [d for _, d in order[:k]])


def _states(rows, targets, cfg):
    """{target: [(mode, origin, part, scope, pool, peers)]} for outer pools (exact) and inner pools (conservative: the K+2 nearest
    on the inner candidates before the target's validation units are blocked, so a neighbour at the margin is never missed)."""
    from ..comparison import K_COMPARAVEIS, MODES, bucket, profiles
    from ..temporal import usable
    out = {d: [] for d in targets}
    nf = cfg['territorial_folds']
    gof = {}
    for r in rows:
        if r.get('grupo'):
            gof.setdefault(r['dist'], r['grupo'])
    for mode in MODES:
        for origin in cfg['origins']:
            for part in range(nf):
                heldout = {r['group'] for r in rows if bucket(r['group'], nf) == part}
                for tag, o, k in (('externo', origin, K_COMPARAVEIS), ('interno', origin - 1, K_COMPARAVEIS + 2)):
                    cand = [r for r in rows if not r.get('future') and usable(r, o, mode) and r['group'] not in heldout and not r['rupture']]
                    prof = profiles(cand)
                    grp = {}
                    for r in cand:
                        if r.get('grupo') and r['grupo'] != 'nao_confirmado':
                            grp.setdefault(r['grupo'], set()).add(r['dist'])
                    for d in targets:
                        peers = _nearest(prof, d, k)
                        out[d].append((mode, origin, part, 'comparaveis', tag, tuple(peers) if len(peers) > 1 else ()))
                        g = gof.get(d)
                        mem = sorted(grp.get(g, ())) if g and g != 'nao_confirmado' else []
                        out[d].append((mode, origin, part, 'grupo_economico', tag, tuple(mem) if len(mem) > 1 and d in mem else ()))
    return out


def dependents():
    from .projecao import panel_rows
    from .painel import dists_with
    q = read(ROOT_OUT / 'quarentena.json')
    vm = set(json.loads(Path(q['municipios_validos']).read_text(encoding='utf-8')))
    base = {c['asset']: c for c in configs(q['quarentena'], q['municipios_validos'])}
    out = {}
    for asset in LEVEL_A:
        t0 = time.monotonic()
        pool = dists_with(asset, 1); targets = [d for d in dists_with(asset, 2) if d != CELESC]
        rows, _, _ = panel_rows(asset, q['quarentena'], vm, pool)
        rows = [r for r in rows if not r.get('future')]
        old = [r for r in rows if not (r['dist'] == CELESC and r['year'] in (2023, 2024))]
        a, b = _states(old, targets, base[asset]), _states(rows, targets, base[asset])
        dep, why = [], {}
        for d in targets:
            diff = [(x, y) for x, y in zip(a[d], b[d]) if x != y or CELESC in y[-1]]
            if diff:
                dep.append(d)
                why[d] = dict(celesc_no_pool=any(CELESC in y[-1] for _, y in diff), pools_alterados=len(diff),
                              exemplo=dict(antes=list(diff[0][0]), depois=list(diff[0][1])))
        out[asset] = dict(alvos=([CELESC] if CELESC in dists_with(asset, 2) else []) + dep, dependentes=dep, motivo=why,
                          linhas_celesc_novas=sum(1 for r in rows if r['dist'] == CELESC and r['year'] in (2023, 2024) and not r['rupture']),
                          segundos=round(time.monotonic() - t0, 1))
        print(asset, len(dep), out[asset]['segundos'], flush=True)
    return out


def run(parallel=2):
    t0 = time.monotonic()
    q = read(ROOT_OUT / 'quarentena.json')
    base = {c['asset']: c for c in configs(q['quarentena'], q['municipios_validos'])}
    dep = read(CMP / 'DEPENDENCIAS_CELESC.json') if (CMP / 'DEPENDENCIAS_CELESC.json').exists() else dependents()
    atomic(CMP / 'DEPENDENCIAS_CELESC.json', dep)
    cfgs = []
    for asset, x in dep.items():
        for i in range(0, len(x['alvos']), BATCH):
            bid = f'{ALIAS[asset]}-{REV}-{i // BATCH + 1}'
            cfgs.append(dict(base[asset], output=str(CMP / ALIAS[asset] / bid), dists=x['alvos'][i:i + BATCH], batch_id=bid))
    st = read(CMP / 'STATUS.json')
    st.setdefault('revisoes', {})[REV] = dict(motivo='ponte experimental MUN_RECODE_5697_2023 aplicada na camada derivada; Celesc + dependentes',
                                              lotes=[c['batch_id'] for c in cfgs], inicio=time.strftime('%Y-%m-%dT%H:%M:%S'))
    for c in cfgs:
        st['lotes'][c['batch_id']] = dict(ativo=c['asset'], dists=c['dists'], tentativas=0, revisao=REV)
    atomic(CMP / 'STATUS.json', st)
    pending, running = list(cfgs), {}
    while pending or running:
        while pending and len(running) < parallel:
            c = pending.pop(0); st['lotes'][c['batch_id']]['tentativas'] += 1
            running[c['batch_id']] = (launch(c), c)
        time.sleep(15)
        for bid in list(running):
            (proc, log), c = running[bid]
            if proc.poll() is None:
                continue
            log.close(); del running[bid]
            s = state(c); r = st['lotes'][bid]
            r.update(estado=s.get('state'), output=s.get('output'), returncode=proc.returncode, fim=time.strftime('%Y-%m-%dT%H:%M:%S'))
            if s.get('state') != 'completed' and r['tentativas'] < 2:
                pending.append(c)
        atomic(CMP / 'STATUS.json', st)
    ok = all(st['lotes'][c['batch_id']].get('estado') == 'completed' for c in cfgs)
    st['revisoes'][REV].update(estado='concluido' if ok else 'concluido_com_falhas', segundos=round(time.monotonic() - t0, 1))
    atomic(CMP / 'STATUS.json', st)
    return st['revisoes'][REV]


def vigentes(st, asset):
    """{dist: (batch_id, output)} of the summaries in force: a completed revision batch supersedes the first-run batch of its DIST."""
    out = {}
    for rev in (False, True):
        for bid, r in st['lotes'].items():
            if r['ativo'] == asset and r.get('estado') == 'completed' and bool(r.get('revisao')) == rev:
                for d in r['dists']:
                    out[d] = (bid, r['output'])
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--parallel', type=int, default=2); ap.add_argument('--so-dependencias', action='store_true')
    a = ap.parse_args()
    if a.so_dependencias:
        dep = dependents(); atomic(CMP / 'DEPENDENCIAS_CELESC.json', dep)
        print(json.dumps({k: dict(alvos=v['alvos'], linhas_celesc_novas=v['linhas_celesc_novas']) for k, v in dep.items()}, indent=1))
        sys.exit(0)
    print(json.dumps(run(a.parallel), ensure_ascii=False, indent=1, default=str))
