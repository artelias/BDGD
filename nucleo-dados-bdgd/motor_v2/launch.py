"""Detach the executor with no inherited terminal/pipe handles (Windows)."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    args = parser.parse_args()
    config = Path(args.config).resolve()
    cfg = json.loads(config.read_text(encoding='utf-8-sig'))
    out = Path(cfg['output']).resolve()
    if out.drive.upper() != 'D:':
        raise ValueError('output must be on D:')
    out.mkdir(parents=True, exist_ok=True)
    launch_id = uuid.uuid4().hex
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + launch_id[:8]
    env = os.environ.copy()
    env['MOTOR_V2_LAUNCH_ID'] = launch_id
    # DETACHED_PROCESS avoids a console. Explicit handles prevent a parent pipe
    # from staying open until the worker exits, including the venv redirector.
    with (out / f'run-{stamp}.log').open('ab') as stdout, (out / f'run-{stamp}.err').open('ab') as stderr:
        child = subprocess.Popen(
            [sys.executable, '-u', '-m', 'motor_v2.runner', '--config', str(config)],
            cwd=Path(__file__).resolve().parents[1], env=env,
            stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, close_fds=True,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    receipt = dict(launch_id=launch_id, launcher_pid=child.pid, config=str(config))
    temp = out / 'launch.json.tmp'
    temp.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    os.replace(temp, out / 'launch.json')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
