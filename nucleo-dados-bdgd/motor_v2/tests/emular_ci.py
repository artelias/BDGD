"""Emulates the GitHub Actions synthetic job on the local machine: the repository code is copied off the data drive and every read of a
blocked prefix (default D:/) raises FileNotFoundError, then the synthetic runner is executed there.

    python -m motor_v2.tests.emular_ci [--bloquear D:/ --bloquear C:/GEOIA]
    python -m motor_v2.tests.emular_ci -- -m unittest discover -s motor_v2/tests     # any other command, e.g. a workflow step

Only the interpreter and its installed packages (sys.prefix, sys.base_prefix and the site-packages already on sys.path) stay readable, as the separate venv of the Actions runner.
A synthetic suite that secretly needs local data fails here exactly as it would on Linux. Exit code = the runner's exit code.
Nothing is written into the repository; the copy lives in a temporary directory that is removed at the end."""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PKG = Path(__file__).resolve().parents[2]                # nucleo-dados-bdgd
COPIAR = ('motor_v2', 'motor_universal', 'etl/bdgd2025/config', 'output-historico/contrato-integracao')
IGNORAR = shutil.ignore_patterns('__pycache__', 'reports', '*.parquet', '.venv*')

SITE = '''import builtins, io, os, sys
_N = lambda s: s.replace(chr(92), '/').lower().rstrip('/') + '/'
_BLOCK = tuple(p.lower() for p in {block!r})
# the interpreter and its installed packages are allowed (on Actions they live in their own venv); everything else under a blocked prefix is data
_ALLOW = tuple({{_N(p) for p in (sys.prefix, sys.base_prefix, sys.exec_prefix, *[x for x in sys.path if 'site-packages' in x.lower()])}})
def _bad(p):
    try: s = os.fspath(p)
    except TypeError: return False
    if isinstance(s, bytes): s = s.decode(errors='ignore')
    s = _N(s)
    return s.startswith(_BLOCK) and not s.startswith(_ALLOW)
def _wrap(f):
    def g(p, *a, **k):
        if _bad(p): raise FileNotFoundError(2, 'CI emulation: no access', str(p))
        return f(p, *a, **k)
    return g
builtins.open = io.open = _wrap(builtins.open)
for _n in ('stat', 'scandir', 'listdir', 'mkdir', 'makedirs'):
    setattr(os, _n, _wrap(getattr(os, _n)))
'''


PROBE = '''import os, sys
try:
    os.listdir(sys.argv[1]); sys.exit(3)
except FileNotFoundError:
    sys.exit(0)
'''


def main(block, comando=None, incluir=()):
    with tempfile.TemporaryDirectory(prefix='motor-v2-ci-') as tmp:
        root = Path(tmp) / 'nucleo-dados-bdgd'
        for rel in (*COPIAR, *incluir):            # incluir: other repository paths a workflow step reads (e.g. web/public/data)
            if (PKG / rel).exists():
                shutil.copytree(PKG / rel, root / rel, ignore=IGNORAR)
        wf = PKG.parent / '.github' / 'workflows' / 'motor-v2-sintetico.yml'
        if wf.exists():
            (Path(tmp) / '.github' / 'workflows').mkdir(parents=True); shutil.copyfile(wf, Path(tmp) / '.github' / 'workflows' / wf.name)
        site = Path(tmp) / 'site'; site.mkdir()
        (site / 'sitecustomize.py').write_text(SITE.format(block=[b.replace('\\', '/') for b in block]), encoding='utf-8')
        env = dict(os.environ, PYTHONPATH=str(site), PYTHONDONTWRITEBYTECODE='1', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
        print(f'copia em {root}; bloqueados: {block}', flush=True)
        # self-check: the block must really hold inside the emulated interpreter, otherwise the run proves nothing
        probe = subprocess.run([sys.executable, '-c', PROBE, block[0]], cwd=root, env=env)
        if probe.returncode != 0:
            print(f'emulacao invalida: {block[0]} continua legivel', file=sys.stderr)
            return 2
        return subprocess.run([sys.executable, *(comando or ['-m', 'motor_v2.tests.suites'])], cwd=root, env=env).returncode


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--bloquear', action='append'); ap.add_argument('--incluir', action='append', default=[]); ap.add_argument('comando', nargs=argparse.REMAINDER)
    a = ap.parse_args()
    sys.exit(main(a.bloquear or ['D:/'], [c for c in a.comando if c != '--'] or None, a.incluir))
