import unittest

from motor_v2.audit_public_products import Tally, run


class PublicAuditTests(unittest.TestCase):
    def test_published_products_have_no_fractional_counts_and_coherent_natures(self):
        result = run()
        self.assertTrue(result['ok'], [p for p in result['produtos'] if not p['ok']])
        for product in result['produtos']:
            self.assertEqual(product['contagens_fracionarias'], 0, product['produto'])
            self.assertEqual(product['n_incoerencias'], 0, product['produto'])
            self.assertGreater(product['contagens'], 10000, product['produto'])        # the audit really reads the products
            self.assertGreater(product['continuas_com_decimais'], 100, product['produto'])  # km and kVA keep their decimals

    def test_audit_detects_a_fractional_count_and_a_negative_count(self):
        t = Tally('x')
        t.add('discrete_count', 2.5, 'a'); t.add('discrete_count', -1, 'b'); t.add('continuous_length', 2.5, 'c'); t.add('discrete_count', 3.0, 'd')
        r = t.report()
        self.assertEqual((r['contagens'], r['contagens_fracionarias'], r['contagens_negativas'], r['continuas_com_decimais']), (3, 1, 1, 1))
        self.assertFalse(r['ok'])

    def test_audit_detects_nature_unit_metric_mismatch(self):
        t = Tally('x')
        t.check('continuous_length', 'itens', 'quantidade', 'm1')       # declared length, unit says count
        t.check(None, 'km', 'quantidade', 'm2')                         # unit km, metric quantidade
        t.check('discrete_count', 'itens', 'quantidade', 'ok')
        self.assertEqual(t.report()['n_incoerencias'], 3)
        self.assertEqual(len([m for m in t.incoherent if m.startswith('ok')]), 0)


if __name__ == '__main__':
    unittest.main()
