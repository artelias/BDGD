"""UCBT is contained in Consumidores: hierarchical reconciliation (synthetic data only; runs on Linux CI without the D: drive)."""
import unittest

from motor_v2.nacional import hierarquia as H
from motor_v2.nacional.cenarios import YEARS

SCEN = ('Conservador', 'Moderado', 'Agressivo')


def proj(base, growth, spread=.01):
    """{(year, scenario): (int, raw)} with ordered scenarios around an annual growth."""
    out = {}
    for y in YEARS:
        for s, g in zip(SCEN, (growth - spread, growth, growth + spread)):
            raw = base * (1 + g) ** (y - 2025)
            out[y, s] = (float(int(raw + .5)), raw)
    return out


def hist(a, c, breaks=()):
    return dict(A={y: float(v) for y, v in a.items()}, B={y: float(a[y] + c[y]) for y in a}, C={y: float(v) for y, v in c.items()},
                breaks=set(breaks), motivo_fora={})


META = dict(ancora=2025, modelo='x')


class Hierarchy(unittest.TestCase):
    def setUp(self):
        # three companies: B independent grows slower than A (violation), faster, and equal
        self.h = {1: hist({2022: 1000, 2023: 1010, 2024: 1020, 2025: 1030}, {2022: 10, 2023: 10, 2024: 10, 2025: 10}),
                  2: hist({2022: 500, 2023: 520, 2024: 540, 2025: 560}, {2022: 5, 2023: 6, 2024: 7, 2025: 8}),
                  3: hist({2022: 200, 2023: 200, 2024: 200, 2025: 200}, {2022: 0, 2023: 0, 2024: 0, 2025: 0})}
        self.a = {1: proj(1030, .02), 2: proj(560, .03), 3: proj(200, 0.)}
        self.b = {1: proj(1040, -.01), 2: proj(568, .05), 3: proj(200, 0.)}
        self.table = H.complement_table(self.h)

    def run_all(self, b=None):
        rows, decs = [], []
        for d in self.h:
            dec, rr, _ = H.reconcile_dist(d, self.h[d], self.a[d], (b or self.b)[d], META, META, self.table)
            rows += rr; decs.append(dec)
        return rows, decs

    def test_no_violation_after_reconciliation_and_original_violation_kept_for_audit(self):
        rows, _ = self.run_all()
        self.assertTrue(any(r['violacao_original'] for r in rows))                    # the independent B violated
        self.assertEqual(H.violations(rows), [])
        for r in rows:
            self.assertGreaterEqual(r['consumidores_reconciliado'], r['ucbt_A'])
            self.assertIsInstance(r['consumidores_reconciliado'], int)
            self.assertEqual(r['consumidores_reconciliado'] - r['ajuste'], r['consumidores_B_original'])   # original preserved
            self.assertEqual(r['modelo_B_original'], 'x')

    def test_scenario_order_and_non_negative_complement(self):
        rows, _ = self.run_all()
        by = {}
        for r in rows:
            self.assertGreaterEqual(r['complemento'], 0)
            by.setdefault((r['DIST'], r['ano']), {})[r['cenario']] = r['consumidores_reconciliado']
        for v in by.values():
            self.assertLessEqual(v['Conservador'], v['Moderado']); self.assertLessEqual(v['Moderado'], v['Agressivo'])

    def test_ucbt_projection_is_never_changed(self):
        rows, _ = self.run_all()
        for r in rows:
            self.assertEqual(r['ucbt_A'], int(self.a[r['DIST']][r['ano'], r['cenario']][0]))

    def test_deterministic_and_idempotent(self):
        r1, d1 = self.run_all(); r2, d2 = self.run_all()
        self.assertEqual(r1, r2); self.assertEqual(d1, d2)
        # feeding the reconciled series back as "B" changes nothing: the result does not depend on the independent B
        rec = {d: {(r['ano'], r['cenario']): (float(r['consumidores_reconciliado']), float(r['consumidores_reconciliado'])) for r in r1 if r['DIST'] == d} for d in self.h}
        r3, _ = self.run_all(rec)
        self.assertEqual([x['consumidores_reconciliado'] for x in r1], [x['consumidores_reconciliado'] for x in r3])

    def test_complement_method_follows_the_motor_rule(self):
        _, decs = self.run_all()
        d = {x['DIST']: x for x in decs}
        self.assertEqual(d[1]['metodo_complemento'], 'persistencia')                  # flat complement: no trend wins
        self.assertEqual(d[3]['complemento_ancora'], 0.)
        dec, _ = H.choose_complement({2022: 10., 2023: 20., 2024: 30., 2025: 40.}, set())
        self.assertIn(dec['modelo_projecao'], ('deriva', 'cagr'))

    def test_incompatible_pairs_are_not_reconciled(self):
        dec, rows, _ = H.reconcile_dist(9, self.h[1], self.a[1], self.b[1], META, dict(ancora=2024, modelo='y'), self.table)
        self.assertEqual(dec['status'], 'sem_coorte'); self.assertIn('ancoras diferentes', dec['motivo'])
        self.assertTrue(all(r['consumidores_reconciliado'] is None for r in rows))
        h = dict(self.h[1], C={2022: 10., 2023: 10., 2024: 10.})
        dec, _, _ = H.reconcile_dist(9, h, self.a[1], self.b[1], META, META, self.table)
        self.assertEqual(dec['status'], 'sem_coorte')

    def test_violation_detector(self):
        good = [dict(DIST=1, ano=2030, cenario=s, ucbt_A=10, consumidores_reconciliado=v) for s, v in zip(SCEN, (10, 11, 12))]
        self.assertEqual(H.violations(good), [])
        self.assertEqual(len(H.violations([dict(good[0], consumidores_reconciliado=9)])), 1)
        self.assertEqual(len(H.violations([dict(good[0], consumidores_reconciliado=10.5)])), 1)
        bad_order = [dict(g) for g in good]; bad_order[0]['consumidores_reconciliado'] = 13
        self.assertTrue(any(v.get('regra') == 'ordem dos cenarios' for v in H.violations(bad_order)))
        with self.assertRaises(ValueError):
            H.reconcile(10, -1.)

    def test_completeness_exactly_15_unique_pairs_per_dist(self):
        rows, _ = self.run_all()
        self.assertEqual(len([r for r in rows if r['DIST'] == 1]), 15)
        self.assertEqual(H.incompletude(rows), [])
        gone = [r for r in rows if not (r['DIST'] == 2 and r['ano'] == 2028 and r['cenario'] == 'Moderado')]
        bad = H.incompletude(gone)
        self.assertEqual([b['DIST'] for b in bad], [2]); self.assertEqual(bad[0]['ausentes'], [(2028, 'Moderado')])
        # a duplicated pair is reported as such (violations() alone overwrites it in its per-scenario dict and would not see it)
        dup = rows + [r for r in rows if r['DIST'] == 3 and r['ano'] == 2026 and r['cenario'] == 'Agressivo']
        bad = H.incompletude(dup)
        self.assertEqual([b['DIST'] for b in bad], [3]); self.assertEqual(bad[0]['duplicados'], [(2026, 'Agressivo')])
        self.assertEqual(H.violations(dup), [])
        out = rows + [dict(rows[0], ano=2031)]
        self.assertEqual(H.incompletude(out)[0]['fora_do_horizonte'], [(2031, rows[0]['cenario'])])
        # 15 rows for the DIST, but not the 15 required pairs (one pair replaced by a year outside the horizon)
        swapped = [dict(r, ano=2031) if (r['DIST'] == 1 and r['ano'] == 2030 and r['cenario'] == 'Moderado') else r for r in rows]
        self.assertEqual(len([r for r in swapped if r['DIST'] == 1]), 15)
        self.assertTrue(H.incompletude(swapped))

    def test_complement_breaks_cut_the_segment(self):
        self.assertEqual(H.segment({2022: 1., 2023: 2., 2024: 3., 2025: 4.}, {2024}, 2025), [(2024, 3.), (2025, 4.)])


if __name__ == '__main__':
    unittest.main()
