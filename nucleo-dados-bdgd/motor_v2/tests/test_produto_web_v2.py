"""Produto web do Motor V2 (web/data-motor-v2): contagens publicadas como inteiros JSON e completude dos cenários coerente.

Lê só os arquivos do repositório (nenhum dado local): roda no workflow da web, com as demais suítes públicas."""
import json
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2] / 'web' / 'data-motor-v2'
CENARIOS = ('Conservador', 'Moderado', 'Agressivo')


@unittest.skipUnless((RAIZ / 'indice.json').exists(), 'produto web do Motor V2 não gerado')
class ProdutoWebV2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ix = json.loads((RAIZ / 'indice.json').read_text(encoding='utf-8'))
        cls.series = [s for f in sorted((RAIZ / 'distribuidoras').glob('*.json'))
                      for s in json.loads(f.read_text(encoding='utf-8'))['series']]

    def test_contagens_sao_inteiros_json_nunca_123_ponto_0(self):
        n = 0
        for s in self.series:
            if s['natureza'] != 'discrete_count':
                continue
            vals = [v for _, v, _ in s['historico']] + [s['valor_ancora']]
            vals += [v for c in CENARIOS for v in ((s['cenarios'] or {}).get(c) or [])]
            for v in vals:
                if v is not None:
                    n += 1
                    self.assertIs(type(v), int, (s['objetivo'], s['metrica'], v))
                    self.assertGreaterEqual(v, 0)
        self.assertGreater(n, 30000)
        for o in self.ix['objetivos']:
            if o['natureza'] == 'discrete_count' and o['total_2030']:
                for c in CENARIOS:
                    self.assertIs(type(o['total_2030'][c]), int, (o['objetivo'], c))

    def test_extensao_e_potencia_mantem_decimais(self):
        dec = sum(1 for s in self.series if s['natureza'] != 'discrete_count'
                  for c in CENARIOS for v in ((s['cenarios'] or {}).get(c) or []) if isinstance(v, float) and not v.is_integer())
        self.assertGreater(dec, 1000)

    def test_completude_igual_aos_cenarios_publicados_e_nunca_extremo_sem_moderado(self):
        tot = {'COMPLETA': 0, 'PARCIAL': 0, 'SEM_PREVISAO': 0}
        for s in self.series:
            pub = [c for c in CENARIOS if (s['cenarios'] or {}).get(c)]
            comp = s['completude_cenarios']
            self.assertEqual(comp['publicados'], pub, (s['objetivo'], s['metrica']))
            if pub:
                self.assertIn('Moderado', pub)
            esperado = 'COMPLETA' if len(pub) == 3 else 'PARCIAL' if pub else 'SEM_PREVISAO'
            self.assertEqual(comp['estado'], esperado)
            for c in CENARIOS:
                if c not in pub:
                    self.assertTrue(comp['nao_publicados'].get(c), (s['objetivo'], s['metrica'], c))
            if s['estado'] in ('PROJETADA_EXPERIMENTAL', 'PROJETADA_BASELINE', 'SEM_ANCORA_2025', 'BLOQUEIO_PLAUSIBILIDADE'):
                tot[esperado] += 1
        self.assertEqual(tot, {'COMPLETA': 2484, 'PARCIAL': 219, 'SEM_PREVISAO': 4})
        soma = {k: sum(o['completude_cenarios'][k] for o in self.ix['objetivos']) for k in tot}
        self.assertEqual(soma, tot)


class AgregadoNacionalDosExtremos(unittest.TestCase):
    """O total nacional de um extremo é a soma dos extremos individuais; comparado ao crescimento nacional observado na mesma coorte."""
    @classmethod
    def setUpClass(cls):
        cls.ix = json.loads((RAIZ / 'indice.json').read_text(encoding='utf-8'))

    def test_todo_total_tem_comparacao_com_o_observado_e_geradores_alerta(self):
        com_total = [o for o in self.ix['objetivos'] if o['total_2030']]
        self.assertGreater(len(com_total), 20)
        for o in com_total:
            a = o['agregado_extremos']
            self.assertEqual(a['n_series'], o['n_series_total']['Moderado'], o['objetivo'])
            g = a['crescimento_implicito']
            self.assertLessEqual(g['Conservador'], g['Moderado'] + 1e-9); self.assertLessEqual(g['Moderado'], g['Agressivo'] + 1e-9)
            self.assertEqual(a['alerta'], a['agressivo_acima_do_observado'] or a['conservador_abaixo_do_observado'])
        ger = next(o for o in com_total if o['objetivo'] == 'geradores')['agregado_extremos']
        self.assertTrue(ger['agressivo_acima_do_observado'])
        self.assertGreater(ger['crescimento_implicito']['Agressivo'], ger['crescimento_nacional_observado_max'])


class RegrasDoExportador(unittest.TestCase):
    """Funções puras do exportador (sem dados): contagem fracionária é erro, nunca arredondada; extremo sem Moderado é recusado."""
    def setUp(self):
        from motor_v2.nacional import exportar_web as E
        self.E = E

    def test_contagem_fracionaria_ou_negativa_e_erro_e_inteira_vira_int(self):
        self.assertIs(type(self.E._inteiro(36241.0, 'x')), int)
        self.assertIsNone(self.E._inteiro(None, 'x'))
        for v in (12.5, -1.0):
            with self.assertRaises(ValueError):
                self.E._inteiro(v, 'x')

    def test_completude_parcial_com_motivo_e_recusa_de_extremo_sem_moderado(self):
        base = dict(objetivo='postes', metrica='quantidade', motivo='m', plausibilidade={'cenarios': {'Agressivo': {'motivo': 'bloqueado: ruptura'}}})
        c = self.E.completude({**base, 'cenarios': {'Conservador': [1] * 5, 'Moderado': [2] * 5, 'Agressivo': None}})
        self.assertEqual((c['estado'], c['publicados'], c['nao_publicados']), ('PARCIAL', ['Conservador', 'Moderado'], {'Agressivo': 'bloqueado: ruptura'}))
        self.assertEqual(self.E.completude({**base, 'cenarios': None})['estado'], 'SEM_PREVISAO')
        with self.assertRaises(ValueError):
            self.E.completude({**base, 'cenarios': {'Conservador': [1] * 5, 'Moderado': None, 'Agressivo': None}})


if __name__ == '__main__':
    unittest.main()
