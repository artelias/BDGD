"""Chains the national stages in one detached process, after the extraction (and the Level B run) end.

    python -m motor_v2.nacional.pipeline --wait-pid 19560 2484 [--from preparar]

Stages: preparar -> comparativos -> projecao -> consolidar. Each stage writes its own status; this file records start/end and the
outcome of each stage in nacional/PIPELINE.json. A failed stage stops the chain (the later ones depend on it) with the error kept."""
import argparse
import json
import time
import traceback

import psutil

from . import ROOT_OUT
from ..runner import atomic, read

STAGES = ('preparar', 'comparativos', 'projecao', 'consolidar')


def main(wait, start='preparar', parallel=2):
    path = ROOT_OUT / 'PIPELINE.json'
    rec = read(path) if path.exists() else {}
    rec.setdefault('etapas', {})
    rec['aguardando_pids'] = wait; atomic(path, rec)
    while any(psutil.pid_exists(p) for p in wait):
        time.sleep(60)
    ext = read(ROOT_OUT / 'extracao' / 'STATUS.json')
    rec['extracao'] = ext.get('estado')
    if not str(ext.get('estado')).startswith('concluido'):
        rec['estado'] = 'parado: extracao ' + str(ext.get('estado')); atomic(path, rec); return rec
    for st in STAGES[STAGES.index(start):]:
        t = time.monotonic(); rec['etapas'][st] = dict(inicio=time.strftime('%Y-%m-%dT%H:%M:%S')); rec['estado'] = 'executando:' + st; atomic(path, rec)
        try:
            if st == 'preparar':
                from .preparar import run; q, p = run(); out = dict(quarentena=q, propostas=[x['id'] for x in p])
            elif st == 'comparativos':
                from .comparativos import run; r = run(parallel); out = dict(estado=r.get('estado'), concluidos=r.get('concluidos'), total=r.get('total'))
            elif st == 'projecao':
                from .projecao import run; d, tr, to, b, bad = run(); out = dict(decisoes=len(d), territoriais=len(tr), totais=len(to), bloqueadas=len(b), falhas_reconciliacao=len(bad))
            else:
                from .consolidar import run; out = run('motor_v2/reports/nacional')
            rec['etapas'][st].update(resultado=out, segundos=round(time.monotonic() - t, 1), estado='ok')
        except Exception as e:
            rec['etapas'][st].update(estado='falha', erro=str(e), traceback=traceback.format_exc(), segundos=round(time.monotonic() - t, 1))
            rec['estado'] = 'falha:' + st; atomic(path, rec); return rec
        atomic(path, rec)
    rec['estado'] = 'concluido'; atomic(path, rec)
    return rec


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--wait-pid', type=int, nargs='*', default=[]); ap.add_argument('--from', dest='start', default='preparar')
    ap.add_argument('--parallel', type=int, default=2)
    a = ap.parse_args()
    print(json.dumps(main(a.wait_pid, a.start, a.parallel), ensure_ascii=False, default=str)[:3000])
