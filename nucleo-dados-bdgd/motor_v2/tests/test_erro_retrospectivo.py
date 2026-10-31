"""End-to-end retrospective error of reconciled consumers and the canonical internal source (synthetic data only; runs on Linux CI)."""
import tempfile
import unittest
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from motor_v2.nacional import erro_retrospectivo as E
from motor_v2.nacional import fonte_canonica as F
from motor_v2.nacional.cenarios import YEARS

SCEN = ('Conservador', 'Moderado', 'Agressivo')
A_SER = {2022: 1000, 2023: 1010, 2024: 1030, 2025: 1040}
C_SER = {2022: 10, 2023: 12, 2024: 14, 2025: 16}


def hist(a, c, breaks=()):
    return dict(A={y: float(v) for y, v in a.items()}, B={y: float(a[y] + c[y]) for y in a}, C={y: float(v) for y, v in c.items()}, breaks=set(breaks), motivo_fora={})


def a_tot(model='cagr_x'):
    """Level A stored backtest: persistence and one chosen model, origins 2023 / 2024 as {origin: (actual of origin+1, prediction)}."""
    return {'persistencia:individual': {2023: (1030., 1010.), 2024: (1040., 1030.)}, model: {2023: (1030., 1020.), 2024: (1040., 1035.)}}


def b_err(h):
    pers = {o: abs(h['B'][o + 1] - h['B'][o]) for o in (2023, 2024)}
    return {'persistencia': pers, 'deriva': {2023: 7., 2024: 9.}, 'cagr': {2023: 8., 2024: 9.5}}


class EndToEnd(unittest.TestCase):
    def setUp(self):
        self.h = hist(A_SER, C_SER)

    def cells(self, h=None, **kw):
        h = h or self.h
        args = dict(d=1, h=h, a_tot=a_tot(), a_model='persistencia', c_kind='persistencia', b_err=b_err(h), b_chosen='cagr')
        args.update(kw)
        return E.cells_for_dist(**args)

    def test_two_origins_one_year_ahead_and_closure_identity(self):
        rows, excl = self.cells()
        self.assertEqual([r['origem'] for r in rows], [2023, 2024]); self.assertEqual(excl, [])
        for r in rows:
            self.assertEqual(r['alvo'], r['origem'] + 1)
            # A persistence + complement persistence IS Level B persistence when the historical closure is exact
            self.assertAlmostEqual(r['E2E_persistencia_erro'], r['B_persistencia_erro'])
            self.assertEqual(r['real_consumidores'], self.h['B'][r['alvo']])

    def test_chosen_models_use_their_own_predictions(self):
        rows, _ = self.cells(a_model='cagr_x')
        r = [x for x in rows if x['origem'] == 2023][0]
        # A chosen predicted 1020; complement persistence from C(2023)=12; actual B(2024) = 1030 + 14
        self.assertAlmostEqual(r['E2E_reconciliado_escolhido_pred'], 1020 + 12)
        self.assertAlmostEqual(r['E2E_reconciliado_escolhido_erro'], 1020 + 12 - 1044)

    def test_incomparable_cells_are_excluded_with_a_reason_never_dropped_silently(self):
        _, excl = self.cells(h=hist(A_SER, C_SER, breaks={2024}))
        self.assertEqual([e['origem'] for e in excl], [2023]); self.assertIn('ruptura', excl[0]['motivo'])
        h = hist(A_SER, C_SER); del h['C'][2023]
        rows, excl = self.cells(h=h)
        self.assertEqual([r['origem'] for r in rows], [2024]); self.assertEqual([e['origem'] for e in excl], [2023]); self.assertIn('complemento', excl[0]['motivo'])
        rows, excl = self.cells(a_tot={})
        self.assertEqual(rows, []); self.assertEqual(len(excl), 2)
        bad_actual = a_tot(); bad_actual['persistencia:individual'][2023] = (1031., 1010.)
        self.assertIn('real do nivel A', self.cells(a_tot=bad_actual)[1][0]['motivo'])
        self.assertIn('nivel B', self.cells(b_chosen=None)[1][0]['motivo'])

    def test_summary_is_deterministic_and_paired_comparison_is_reported(self):
        rows = []
        for d, k in ((1, 1), (2, 3), (3, 5), (4, 8)):
            h = hist({y: v * k for y, v in A_SER.items()}, {y: v * k for y, v in C_SER.items()})
            tot = {n: {o: (a * k, p * k) for o, (a, p) in v.items()} for n, v in a_tot().items()}
            rows += E.cells_for_dist(d, h, tot, 'persistencia', 'persistencia', b_err(h), 'cagr')[0]
        s1, s2 = E.summarize(rows), E.summarize(rows)
        self.assertEqual(s1, s2)
        m = s1['todas']['E2E_persistencia']
        self.assertEqual(m['celulas'], 8); self.assertEqual(m['pareado_vitorias'] + m['pareado_derrotas'] + m['pareado_empates'], 8)
        self.assertEqual(s1['todas']['B_escolhido']['vence_B_escolhido'], 0.0)             # never beats itself
        self.assertIn('vies_relativo', s1['todas']['B_persistencia']); self.assertNotIn('vies_relativo', s1['todas']['B_deriva'])

    def test_sign_test(self):
        self.assertEqual(E.sign_test(0, 0), 1.0)
        self.assertAlmostEqual(E.sign_test(5, 5), 1.0)
        self.assertAlmostEqual(E.sign_test(10, 0), 2 / 1024)
        self.assertLess(E.sign_test(1, 20), 0.001)


def rows_ok(dists=(1, 2)):
    out = []
    for d in dists:
        for k, s in enumerate(SCEN):
            for y in YEARS:
                a = 100 * d + (y - 2025) * (k + 1)
                out.append(dict(DIST=d, ano=y, cenario=s, ancora=2025, ucbt_A=a, consumidores_B_original=a - 3, consumidores_reconciliado=a + 5 + k, complemento=5 + k, status='reconciliada'))
    out.append(dict(DIST=9, ano=2026, cenario='Moderado', ancora=2025, ucbt_A=7, consumidores_B_original=5, consumidores_reconciliado=None, complemento=None, status='sem_coorte'))
    return out


class CanonicalSource(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.dir = Path(self.tmp.name)
        self.src, self.ctr = self.dir / 'fonte.parquet', self.dir / 'contrato.json'

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rows):
        pq.write_table(pa.Table.from_pylist(rows), self.src)

    def test_declare_and_load_roundtrip_and_original_never_a_fallback(self):
        self.write(rows_ok())
        c = F.declarar(self.src, self.ctr)
        self.assertEqual(c['coluna_canonica'], 'consumidores_reconciliado'); self.assertEqual(c['coluna_somente_auditoria'], 'consumidores_B_original')
        self.assertEqual(c['pares_por_dist'], 15); self.assertEqual(c['dist_reconciliadas'], [1, 2]); self.assertEqual(c['dist_sem_valor_canonico'], [9])
        v = F.carregar(self.src, self.ctr)
        self.assertEqual(len(v), 30); self.assertEqual(v[1, 2026, 'Moderado'], (100 + 2) + 5 + 1)
        self.assertNotIn((9, 2026, 'Moderado'), v)                                       # no value: the independent B is NOT substituted

    def test_refuses_a_source_that_violates_the_contract(self):
        rows = rows_ok(); rows[3] = dict(rows[3], consumidores_reconciliado=rows[3]['ucbt_A'] - 1)
        self.write(rows)
        with self.assertRaises(F.FonteCanonicaInvalida):
            F.declarar(self.src, self.ctr)
        self.write([r for r in rows_ok() if not (r['DIST'] == 2 and r['ano'] == 2029 and r['cenario'] == 'Agressivo')])
        with self.assertRaises(F.FonteCanonicaInvalida):                                 # one of the 15 pairs missing
            F.declarar(self.src, self.ctr)

    def test_refuses_a_source_changed_after_the_declaration(self):
        self.write(rows_ok()); F.declarar(self.src, self.ctr)
        self.write([dict(r, consumidores_reconciliado=r['consumidores_reconciliado'] + 1) if r['status'] == 'reconciliada' else r for r in rows_ok()])
        with self.assertRaises(F.FonteCanonicaInvalida):
            F.carregar(self.src, self.ctr)


if __name__ == '__main__':
    unittest.main()
