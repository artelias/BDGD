"""Where each Motor V2 test suite runs: the single source of truth for GitHub Actions, the local audit and the classification test.

    python -m motor_v2.tests.suites             # runs the SYNTHETIC suites (exactly what .github/workflows/motor-v2-sintetico.yml runs)
    python -m motor_v2.tests.suites --listar    # prints the classification

Three groups, never mixed:
  SINTETICAS  read no local data (no D:/, no BDGD knowledge base, no PowerShell): GitHub Actions on Linux. Verified by running them with
              every D:/ path blocked (motor_v2/tests/emular_ci.py), not only by reading the code.
  LOCAIS      need the real local data (D:/NUCLEO_BDGD_2025 panels, contract, Parquets) or the Windows executor: run only in the full
              local audit, `python -m motor_v2.nacional.testes`, which runs EVERY suite and records the outcome of each test.
  PUBLICAS    audit the published products of the repository (web/public, motor_cenarios/saida). They belong to the public-product
              contract of PR #19 and run in its web workflow; the files arrive with that PR.
Dashboard tests (Node, Playwright) are not Motor V2 suites and are not listed here.
A suite that loads no test fails the run: a renamed or emptied file cannot pass silently."""
import argparse
import sys
import unittest
from pathlib import Path

DIR = Path(__file__).parent

SINTETICAS = {
    'test_hierarquia': 'reconciliacao UCBT + complemento, 15 pares por DIST (dados sinteticos)',
    'test_erro_retrospectivo': 'erro ponta a ponta e fonte canonica (dados sinteticos, Parquet temporario)',
    'test_auditoria_final': 'elegibilidade, sucessao, triagem v2, pontes, verificador publico (sinteticos)',
    'test_nacional': 'selecao, cenarios, consolidacao (sinteticos)',
    'test_baselines': 'baselines de tendencia',
    'test_conj_plan': 'plano de pontes de CONJ (sintetico; 1 caso pula sem a base local)',
    'test_future': 'covariaveis futuras em unidade original',
    'test_metric_contract': 'contrato de natureza fisica (arquivo identico ao do PR #19)',
    'test_metric_contract_motor_v2': 'contrato de natureza fisica nos internos do Motor V2',
    'test_temporal': 'validacao temporal sem vazamento',
    'test_vintage': 'vintages point-in-time',
    'test_suites': 'esta classificacao e o workflow sintetico',
    'test_cobertura': 'estados da matriz de cobertura e regras de liberacao de potencia (sinteticos)',
    'test_plausibilidade': 'portao de plausibilidade dos cenarios (sinteticos)',
}
LOCAIS = {
    'test_comparison': 'comparativo de candidatos sobre o painel real em D:/',
    'test_executor_integration': 'executor destacado no Windows (PowerShell) com diretorio temporario em D:/',
    'test_features': 'features sobre o painel e as externas locais',
    'test_generalization': 'generalizacao territorial sobre dados reais',
    'test_lote': 'lote de validacao sobre dados reais',
    'test_ml': 'pipelines de ML sobre o painel real',
    'test_scale': 'escala e memoria sobre dados reais',
    'test_v2': 'integracao do executor V2 com a base local',
}
PUBLICAS = {
    'test_public_audit': 'audita os produtos publicos reais do repositorio; contrato do PR #19, roda no workflow da web',
}


def arquivos():
    return sorted(p.stem for p in DIR.glob('test*.py'))


def problemas():
    """Classification errors: a test file in no group, a name in two groups, or a synthetic/local suite listed but missing on disk."""
    grupos = (SINTETICAS, LOCAIS, PUBLICAS)
    todos = [n for g in grupos for n in g]
    out = [f'sem classificacao: {n}' for n in arquivos() if n not in todos]
    out += [f'em mais de um grupo: {n}' for n in sorted(set(todos)) if todos.count(n) > 1]
    out += [f'listada mas ausente: {n}' for n in sorted(set(SINTETICAS) | set(LOCAIS)) if n not in arquivos()]
    return out


def run(names=tuple(SINTETICAS), verbosity=2, stream=None):
    """Runs the named suites in this process. -> (ok, result). Fails on a classification problem or on a suite that loads no test."""
    bad = problemas()
    if bad:
        print('\n'.join(bad), file=sys.stderr)
        return False, None
    loader = unittest.TestLoader(); suite = unittest.TestSuite(); empty = []
    for n in names:
        s = loader.discover(str(DIR), pattern=n + '.py', top_level_dir=str(DIR))
        if s.countTestCases() == 0:
            empty.append(n)
        suite.addTests(s)
    if empty:
        print('suites sem nenhum teste: ' + ', '.join(empty), file=sys.stderr)
        return False, None
    res = unittest.TextTestRunner(stream=stream or sys.stderr, verbosity=verbosity).run(suite)
    return res.wasSuccessful(), res


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--listar', action='store_true')
    a = ap.parse_args()
    if a.listar:
        for nome, grupo in (('SINTETICAS (GitHub Actions)', SINTETICAS), ('LOCAIS (auditoria local)', LOCAIS), ('PUBLICAS (PR #19, workflow da web)', PUBLICAS)):
            print(nome); [print(f'  {k:32s} {v}') for k, v in grupo.items()]
        sys.exit(1 if problemas() else 0)
    ok, res = run()
    if res is not None:
        print(f'suites sinteticas: {len(SINTETICAS)}; testes: {res.testsRun}; falhas: {len(res.failures)}; erros: {len(res.errors)}; ignorados: {len(res.skipped)}')
    sys.exit(0 if ok else 1)
