"""Test matrix of the Motor V2 suite: every test with its outcome, plus the SHA-256 of each test file and of the environment.

    python -m motor_v2.nacional.testes

Runs `unittest discover -s motor_v2/tests` in-process and writes nacional/testes/MATRIZ_TESTES.csv and MANIFESTO_TESTES.json.
Some suites read local data (contract, D:/ panels), which is why they are run here and not in the Linux CI of the repository."""
import importlib.metadata
import json
import platform
import sys
import time
import unittest
from pathlib import Path

from . import ROOT_OUT
from .relatorio import write_csv
from ..runner import ROOT, atomic, digest

OUT = ROOT_OUT / 'testes'
# suites that read no local data (D:/, knowledge base): run on Linux CI (.github/workflows/motor-v2-sintetico.yml); checked by
# emulating the absence of those paths. The others need the local data and run only in this full local audit.
SINTETICOS = ('test_hierarquia', 'test_auditoria_final', 'test_nacional', 'test_baselines', 'test_conj_plan', 'test_future',
              'test_metric_contract', 'test_public_audit', 'test_temporal', 'test_vintage')


class _Result(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k); self.rows = []; self._t = {}

    def startTest(self, test):
        self._t[test.id()] = time.monotonic(); super().startTest(test)

    def _add(self, test, status, detail=None):
        mod, cls, name = (test.id().split('.')[-3:] + ['', '', ''])[:3]
        self.rows.append(dict(arquivo=mod, classe=cls, teste=name, resultado=status, ci_linux_sintetico=mod in SINTETICOS, segundos=round(time.monotonic() - self._t.get(test.id(), time.monotonic()), 3),
                              detalhe=(detail or '')[-500:]))

    def addSuccess(self, test):
        super().addSuccess(test); self._add(test, 'ok')

    def addFailure(self, test, err):
        super().addFailure(test, err); self._add(test, 'falha', self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err); self._add(test, 'erro', self._exc_info_to_string(err, test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason); self._add(test, 'ignorado', reason)


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'motor_v2' / 'tests'))
    with open(OUT / 'saida_unittest.txt', 'w', encoding='utf-8') as f:
        res = unittest.TextTestRunner(stream=f, verbosity=2, resultclass=_Result).run(suite)
    write_csv(OUT / 'MATRIZ_TESTES.csv', res.rows)
    m = dict(total=res.testsRun, ok=sum(r['resultado'] == 'ok' for r in res.rows), falhas=len(res.failures), erros=len(res.errors), ignorados=len(res.skipped),
             arquivos={p.name: digest(p) for p in sorted((ROOT / 'motor_v2' / 'tests').glob('*.py'))},
             ambiente=dict(python=platform.python_version(), executavel=sys.executable,
                           pacotes={n: importlib.metadata.version(n) for n in ('scikit-learn', 'numpy', 'scipy', 'duckdb', 'pyarrow')}),
             ci_linux=dict(workflow='.github/workflows/motor-v2-sintetico.yml', suites=list(SINTETICOS),
                           testes=sum(1 for r in res.rows if r['ci_linux_sintetico']),
                           nota='suites com dados reais rodam so nesta auditoria local'))
    atomic(OUT / 'MANIFESTO_TESTES.json', m)
    return m


if __name__ == '__main__':
    m = run()
    print(json.dumps({k: v for k, v in m.items() if k != 'arquivos'}, indent=1))
    sys.exit(0 if m['falhas'] == m['erros'] == 0 else 1)
