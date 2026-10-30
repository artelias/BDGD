"""Start any motor_v2 module as a detached Windows process that survives the agent/terminal session.

    python -m motor_v2.detach --name nacional --log-dir D:/NUCLEO_BDGD_2025/motor_v2/nacional -- motor_v2.nacional --manifest ...

No inherited handles (stdin is NUL, stdout/stderr go to files), so the parent can exit immediately. A receipt with the PID,
the command and the log paths is written next to the logs."""
import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--name', required=True)
    ap.add_argument('--log-dir', required=True)
    ap.add_argument('module', nargs=argparse.REMAINDER)
    a = ap.parse_args()
    module = [x for x in a.module if x != '--']
    if not module or not module[0].startswith('motor_v2.'):
        raise SystemExit('expected a motor_v2.* module after --')
    out = Path(a.log_dir).resolve()
    if out.drive.upper() != 'D:':
        raise SystemExit('logs must be on D:')
    out.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S')
    env = dict(os.environ, OMP_NUM_THREADS='2', MKL_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2', PYTHONIOENCODING='utf-8')
    with (out / f'{a.name}-{stamp}.log').open('ab') as so, (out / f'{a.name}-{stamp}.err').open('ab') as se:
        child = subprocess.Popen([sys.executable, '-u', '-m', *module], cwd=Path(__file__).resolve().parents[1], env=env,
                                 stdin=subprocess.DEVNULL, stdout=so, stderr=se, close_fds=True,
                                 creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
    receipt = dict(name=a.name, pid=child.pid, command=module, started=stamp, log=str(out / f'{a.name}-{stamp}.log'))
    (out / f'{a.name}.launch.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
