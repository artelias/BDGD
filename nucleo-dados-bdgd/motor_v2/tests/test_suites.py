"""The suite classification is complete and the synthetic workflow runs exactly the synthetic group (no local data needed)."""
import re
import unittest
from pathlib import Path

from motor_v2.tests import suites

WORKFLOW = Path(__file__).resolve().parents[3] / '.github' / 'workflows' / 'motor-v2-sintetico.yml'
LOCAL = r'[A-Za-z]:[/\\]NUCLEO|' + 'power' + 'shell'          # split so this file does not match itself


class Classification(unittest.TestCase):
    def test_every_test_file_has_exactly_one_group(self):
        self.assertEqual(suites.problemas(), [])

    def test_synthetic_suites_name_no_local_path(self):
        # necessary, not sufficient: the real check is emular_ci.py (every D:/ path blocked); this catches the obvious regressions early
        for n in suites.SINTETICAS:
            src = (suites.DIR / f'{n}.py').read_text(encoding='utf-8')
            self.assertIsNone(re.search(LOCAL, src, re.I), n)

    def test_the_full_local_audit_reads_the_same_classification(self):
        from motor_v2.nacional import testes
        self.assertEqual(tuple(testes.SINTETICOS), tuple(suites.SINTETICAS))

    def test_workflow_runs_the_synthetic_runner_and_never_a_blind_discover(self):
        if not WORKFLOW.exists():
            self.skipTest('workflow fora desta arvore')
        y = WORKFLOW.read_text(encoding='utf-8')
        self.assertIn('-m motor_v2.tests.suites', y)
        self.assertNotRegex(y, r'unittest discover -s motor_v2/tests(?! -p)')       # discovering every suite would run the local ones

    def test_a_suite_that_loads_nothing_fails_the_run(self):
        ok, res = suites.run(names=('test_inexistente_xyz',), verbosity=0)
        self.assertFalse(ok); self.assertIsNone(res)


if __name__ == '__main__':
    unittest.main()
