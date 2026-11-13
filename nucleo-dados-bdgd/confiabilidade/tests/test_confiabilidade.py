"""Testes do módulo de Confiabilidade. Os sintéticos rodam sempre; os de dados reais pulam quando o produto ou a BDGD não estão na máquina.

    python -m unittest discover -s confiabilidade/tests -t .
"""
import json
import math
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from confiabilidade import contrato as K
from confiabilidade.metricas import IDS, TIPO, derivar
from confiabilidade.publicar import ZERO_ALIM, completar_zeros, reconstrucao, validar

RAIZ = Path(__file__).resolve().parents[2]
PRODUTO = RAIZ / 'web/public/data/confiabilidade'
TRABALHO = Path(os.environ.get('CONF_TRABALHO', 'D:/NUCLEO_BDGD_2025/confiabilidade'))


class Formulas(unittest.TestCase):
    def test_anual_e_soma_dos_meses_e_ausencia_nao_e_zero(self):
        self.assertEqual(K.anual([1.0, 2.0, 3.0]), (6.0, 3, False))
        self.assertEqual(K.anual([1.0] * 12)[2], True)
        self.assertEqual(K.anual([None, None]), (None, 0, False))

    def test_agregado_ponderado_nao_media_simples(self):
        v, n, fora = K.agregado_mensal([(10.0, 9000), (40.0, 1000), (None, 50), (5.0, 0)])
        self.assertAlmostEqual(v, 13.0)
        self.assertEqual((n, fora), (2, 2))
        self.assertNotAlmostEqual(v, (10 + 40) / 2)

    def test_somar_dic_nao_e_dec(self):
        # 3 consumidores, DIC 1, 2 e 3 h: numerador 6, DEC 2
        soma_dic, cc = 6.0, 3
        self.assertEqual(K.razao(soma_dic, cc), 2.0)

    def test_limite_e_situacao(self):
        self.assertEqual(K.situacao_limite(12, 10), 'ACIMA')
        self.assertEqual(K.situacao_limite(10, 10), 'DENTRO')
        self.assertEqual(K.situacao_limite(10, None), 'ND')
        self.assertIsNone(K.razao_limite(1, 0))

    def test_supressao_e_concentracao(self):
        self.assertEqual([K.suprimir(x) for x in (0, 1, 4, 5, None)], [0, None, None, 5, None])
        self.assertAlmostEqual(K.gini([1, 1, 1, 1]), 0.0)
        self.assertGreater(K.gini([0, 0, 0, 10]), 0.7)
        self.assertIsNone(K.gini([5]))
        self.assertAlmostEqual(K.participacao_maiores([5, 3, 2], 1), 0.5)

    def test_reconciliacao_tolerancia(self):
        self.assertTrue(K.reconciliado(10.4, 10.0))
        self.assertFalse(K.reconciliado(11.0, 10.0))
        self.assertTrue(K.reconciliado(0.04, 0.0))
        self.assertIsNone(K.reconciliado(None, 1.0))

    def test_classes_de_seccionamento(self):
        self.assertEqual(K.classe_seccionamento('32'), 'religador')
        self.assertEqual(K.classe_seccionamento(22), 'fusivel')
        self.assertEqual(K.classe_seccionamento('x'), 'outros')


class Metricas(unittest.TestCase):
    BASE = dict(uc_bt=900, uc_mt=8, uc_at=2, uc_bt_rural=300, uc_mt_rural=2, ene_bt_mwh=1800.0, ene_mt_mwh=200.0, ene_at_mwh=0.0, km_mt=50.0, km_bt=80.0,
                km_mt_rural=20.0, km_mt_tri=40.0, alim=5, alim_pred=4, subs=2, trafos=30, trafo_un=32, trafo_pot_kva=1500.0, trafo_un_mrt=2, sec=40,
                sec_religador=4, sec_tlcd=3, sec_na=2, eq160=10, eq345=4, reg_eq=1, ug=50, km_mt_maior_alim=20.0, conc_uc_top1=0.4, conc_uc_top3=0.9, conc_km_gini=0.3)

    def test_relativas_e_tipos(self):
        m = derivar(self.BASE, area_km2=100.0)
        self.assertEqual(set(m), set(IDS))
        self.assertEqual(m['uc'], 910)
        self.assertAlmostEqual(m['km_mt_por_mil_uc'], round(50 / 910 * 1000, 4))
        self.assertAlmostEqual(m['relig_por_100km'], 8.0)
        self.assertAlmostEqual(m['uc_por_trafo'], 30.0)
        self.assertAlmostEqual(m['pct_uc_rural'], round(302 / 908, 4))
        for k, v in m.items():
            if TIPO[k] == 'contagem' and v is not None:
                self.assertIsInstance(v, int, k)

    def test_ausencia_preservada(self):
        m = derivar(dict(uc_bt=None, km_mt=10.0))
        self.assertIsNone(m['uc'])
        self.assertIsNone(m['km_mt_por_mil_uc'])
        self.assertEqual(m['km_mt'], 10.0)

    def test_contagem_nao_inteira_falha(self):
        with self.assertRaises(ValueError):
            derivar(dict(self.BASE, alim=2.5))

    def test_mt_at_pequeno_suprimido(self):
        self.assertIsNone(derivar(dict(self.BASE, uc_mt=2, uc_at=1))['uc_mt_at'])
        self.assertEqual(derivar(dict(self.BASE, uc_mt=0, uc_at=0))['uc_mt_at'], 0)

    def test_zero_observado_so_quando_a_camada_foi_lida(self):
        m = completar_zeros(dict(uc_bt=10), ausentes=set())
        self.assertEqual(m['reg_eq'], 0)
        self.assertEqual(m['km_mt'], 0)
        m2 = completar_zeros(dict(uc_bt=10), ausentes={'EQRE', 'SSDMT'})
        self.assertIsNone(m2.get('reg_eq'))
        self.assertIsNone(m2.get('km_mt'))

    def test_alimentador_suprimido_nao_vira_zero(self):
        al = dict(uc_bt=None, uc_mt=None, uc_suprimido=True, trafos=None)
        mapa = {k: e for k, e in ZERO_ALIM.items() if not (al['uc_suprimido'] and k.startswith('uc_'))}
        out = completar_zeros(al, set(), mapa)
        self.assertIsNone(out['uc_bt'])
        self.assertEqual(out['trafos'], 0)


class Reconstrucao(unittest.TestCase):
    def test_denominador_oficial_mensal(self):
        dic = dict(soma_dic=[10.0] * 12, soma_fic=[5.0] * 12, linhas=100, linhas_com_dic=100, entidades=['UCBT'])
        r = reconstrucao(dic, [None] * 12, [None] * 12, [100] * 12, 1.2, 0.6, 100)
        self.assertAlmostEqual(r['dec'], 1.2)
        self.assertAlmostEqual(r['fec'], 0.6)
        self.assertEqual(r['estado'], K.RECONSTRUIDO_VALIDADO)
        r2 = reconstrucao(dic, [None] * 12, [None] * 12, [100] * 12, 2.0, 0.6, 100)
        self.assertEqual(r2['estado'], K.DERIVADO_EXPLORATORIO)

    def test_mes_sem_denominador_nao_reconstroi(self):
        dic = dict(soma_dic=[10.0] * 12, soma_fic=[5.0] * 12, linhas=1, linhas_com_dic=1, entidades=['UCBT'])
        r = reconstrucao(dic, [None] * 12, [None] * 12, [100] * 11 + [None], 1.2, 0.6, 100)
        self.assertIsNone(r['dec'])

    def test_mes_sem_oficial_fica_fora_dos_dois_lados(self):
        # regressão (auditoria de 12/11/2026): FEC de jun/2025 da Elektro ausente na ANEEL; o FIC de junho não pode entrar
        dic = dict(soma_dic=[10.0] * 12, soma_fic=[5.0] * 12, linhas=100, linhas_com_dic=100, entidades=['UCBT'])
        fec_m = [0.05] * 5 + [None] + [0.05] * 6
        r = reconstrucao(dic, [0.1] * 12, fec_m, [100] * 12, 1.2, 0.55, 100)
        self.assertAlmostEqual(r['fec'], 0.55)
        self.assertEqual((r['meses_dec'], r['meses_fec']), (12, 11))
        self.assertEqual(r['estado'], K.RECONSTRUIDO_VALIDADO)


class ValidacaoProduto(unittest.TestCase):
    def _produto(self, conjuntos, demonstrativo=False):
        d = Path(tempfile.mkdtemp())
        (d / 'distribuidoras').mkdir()
        (d / 'indice.json').write_text(json.dumps(dict(demonstrativo=demonstrativo)), encoding='utf-8')
        (d / 'distribuidoras' / '1.json').write_text(json.dumps(dict(conjuntos=conjuntos)), encoding='utf-8')
        self.addCleanup(shutil.rmtree, d)
        return d

    def _bloco(self, **infra):
        return dict(dec=1.0, fec=1.0, ld=2.0, lf=2.0, infra=infra or None)

    def test_aceita_produto_valido(self):
        self.assertTrue(validar(self._produto([dict(c=1, a={'2025': self._bloco(uc=10, km_mt=1.5)}, al=None)])))

    def test_recusa_demonstrativo_duplicado_contagem_e_ano(self):
        for conj, demo in [([dict(c=1, a={'2025': self._bloco()}, al=None)], True),
                           ([dict(c=1, a={}, al=None), dict(c=1, a={}, al=None)], False),
                           ([dict(c=1, a={'2025': self._bloco(uc=1.5)}, al=None)], False),
                           ([dict(c=1, a={'2021': self._bloco()}, al=None)], False),
                           ([dict(c=1, a={}, al=dict(lista=[dict(ctmt='x', uc_bt=3)]))], False)]:
            with self.assertRaises(SystemExit):
                validar(self._produto(conj, demo))


@unittest.skipUnless((PRODUTO / 'indice.json').exists(), 'produto publicado ausente')
class ProdutoReal(unittest.TestCase):
    def test_auditoria_sem_falhas(self):
        from confiabilidade.auditoria import auditar
        r = auditar(PRODUTO, Path(tempfile.mkdtemp()))
        self.assertEqual(r['falhas'], [])
        self.assertEqual(r['A4_piloto_contra_portal_2025'][6600]['trafos']['igual'], True)
        self.assertEqual(r['A6_geometria']['poligonos_de_conjunto_sem_apuracao_2025'], 0)

    def test_apuracao_parcial_sinalizada_e_fora_do_limite(self):
        # regressão (auditoria de 12/11/2026): FEC com menos de 12 meses sem alerta e comparado ao limite anual
        parciais = 0
        for f in (PRODUTO / 'distribuidoras').glob('*.json'):
            d = json.loads(f.read_text(encoding='utf-8'))
            acima = {}
            for c in d['conjuntos']:
                for a, b in c['a'].items():
                    if b['meses_dec'] < 12 or b['meses_fec'] < 12:
                        parciais += 1
                        self.assertIn('apuracao_parcial', b['alertas'], f"{d['dist']}/{c['c']}/{a}")
                    s = acima.setdefault(a, [0, 0, 0, 0])
                    s[0] += b['meses_dec'] == 12 and K.situacao_limite(b['dec'], b['ld']) == 'ACIMA'
                    s[1] += b['meses_fec'] == 12 and K.situacao_limite(b['fec'], b['lf']) == 'ACIMA'
                    # auditoria de 13/11/2026: denominador = conjuntos com 12 meses e limite publicado
                    s[2] += b['meses_dec'] == 12 and b['dec'] is not None and b['ld'] is not None
                    s[3] += b['meses_fec'] == 12 and b['fec'] is not None and b['lf'] is not None
            for a, (ad, af, cd, cf) in acima.items():
                an = d['anual'][a]
                self.assertEqual((an['acima_dec'], an['acima_fec'], an['comparaveis_dec'], an['comparaveis_fec']), (ad, af, cd, cf), f"{d['dist']}/{a}")
        self.assertGreater(parciais, 0)
        el = json.loads((PRODUTO / 'distribuidoras/385.json').read_text(encoding='utf-8'))
        self.assertIs(el['anual']['2025']['completo_fec'], False)
        self.assertIs(el['anual']['2025']['completo_dec'], True)
        nac = json.loads((PRODUTO / 'nacional/2025.json').read_text(encoding='utf-8'))
        self.assertIn('meses_fec', nac['campos'])

    def test_componentes_internas_somam_o_indicador_no_mesmo_periodo(self):
        # regressão (auditoria de 12/11/2026): FEC 2025 da Elektro com parcelas internas somando 104% (componentes de junho sem FEC)
        n = 0
        for f in (PRODUTO / 'distribuidoras').glob('*.json'):
            d = json.loads(f.read_text(encoding='utf-8'))
            for c in d['conjuntos']:
                for a, b in c['a'].items():
                    for ind in ('dec', 'fec'):
                        comp = (b.get('comp') or {}).get(ind) or {}
                        if b[ind] is None or comp.get('ip') is None or comp.get('ind') is None:
                            continue
                        n += 1
                        self.assertAlmostEqual(comp['ip'] + comp['ind'], b[ind], delta=0.02 + 0.006 * 12, msg=f"{d['dist']}/{c['c']}/{a}/{ind}")
        self.assertGreater(n, 20000)

    def test_fatores_respeita_contrato(self):
        p = PRODUTO / 'fatores.json'
        if not p.exists():
            self.skipTest('fatores.json ainda não gerado')
        f = json.loads(p.read_text(encoding='utf-8'))
        self.assertFalse(f['demonstrativo'])
        self.assertEqual({a['alvo'] for a in f['alvos']}, {'dec', 'fec'})
        for h in f['hipoteses']:
            self.assertIn(h['veredito'], {'COMPATIVEL', 'NAO_SUSTENTADA', 'INCONCLUSIVA', 'SEM_DADOS'})
        for a in f['alvos']:
            for x in a['associacoes']:
                if x['ic95']:
                    self.assertLessEqual(x['ic95'][0], x['ic95'][1])
                if x['spearman'] is not None:
                    self.assertTrue(-1 <= x['spearman'] <= 1)


@unittest.skipUnless((TRABALHO / 'derivado/infra/DIST=6600/ANO=2025.json').exists() and Path('D:/NUCLEO_BDGD_2025/staging_parquet/DIST=6600').exists(), 'BDGD local ausente')
class Idempotencia(unittest.TestCase):
    def test_segunda_execucao_nao_reprocessa(self):
        from confiabilidade.infra import executar, publicacoes_do_contrato
        r = executar(6600, 2025, publicacoes_do_contrato())
        self.assertEqual(r['status'], 'INALTERADO')

    def test_geometria_valida_e_dentro_do_brasil(self):
        g = json.loads((PRODUTO / 'geo/6600.json').read_text(encoding='utf-8'))
        self.assertEqual(g['meta']['tipo'], 'POLIGONO_OFICIAL_SIMPLIFICADO')
        for f in g['features']:
            self.assertIn(f['geometry']['type'], ('Polygon', 'MultiPolygon'))
            xs = [c for c in json.dumps(f['geometry']['coordinates']).replace('[', ' ').replace(']', ' ').replace(',', ' ').split()]
            v = list(map(float, xs))
            self.assertTrue(all(-75 <= x <= -28 for x in v[0::2]) and all(-35 <= y <= 7 for y in v[1::2]))


class Estatistica(unittest.TestCase):
    def test_correlacoes_e_veredito_em_dados_sinteticos(self):
        import numpy as np
        from confiabilidade.estatistica import bootstrap_dist, correlacoes, ic, veredito
        rng = np.random.default_rng(1)
        n = 600
        dist = np.repeat(np.arange(30), 20)
        ctx = rng.normal(size=(n, 1))
        x = rng.normal(size=n) + 0.3 * ctx[:, 0]
        y = 0.8 * x + 0.5 * ctx[:, 0] + rng.normal(scale=0.5, size=n)
        g = dist * 10000 + 2025
        bruta, parcial, dentro = correlacoes(y, x, ctx, g)
        self.assertGreater(parcial, 0.5)
        self.assertGreater(dentro, 0.5)
        boot = bootstrap_dist(dist, lambda idx: correlacoes(y[idx], x[idx], ctx[idx], g[idx]), 60, rng)
        a = dict(n=n, spearman=bruta, parcial=parcial, parcial_ic95=ic(boot[:, 1]), dentro_dist=dentro, dentro_dist_ic95=ic(boot[:, 2]))
        self.assertEqual(veredito(a, +1), 'COMPATIVEL')
        self.assertEqual(veredito(a, -1), 'NAO_SUSTENTADA')
        self.assertEqual(veredito(dict(a, n=50), +1), 'SEM_DADOS')
        ruido = dict(n=n, spearman=0.01, parcial=0.01, parcial_ic95=[-0.05, 0.06], dentro_dist=0.0, dentro_dist_ic95=[-0.04, 0.05])
        self.assertEqual(veredito(ruido, +1), 'NAO_SUSTENTADA')

    def test_veredito_h7_usa_a_mesma_regra(self):
        # regressão (auditoria de 12/11/2026): H7 dava NAO_SUSTENTADA com |ρ| = 0,10 e IC largo contendo zero
        from confiabilidade.estatistica import veredito_variacao
        fraco = dict(variavel='a', n=500, spearman=0.02, ic95=[-0.04, 0.05])
        largo = dict(variavel='b', n=500, spearman=-0.10, ic95=[-0.24, 0.04])
        firme = dict(variavel='c', n=500, spearman=-0.15, ic95=[-0.23, -0.03])
        self.assertEqual(veredito_variacao([fraco])[0], 'NAO_SUSTENTADA')
        self.assertEqual(veredito_variacao([fraco, largo])[0], 'INCONCLUSIVA')
        self.assertEqual(veredito_variacao([fraco, firme])[0], 'INCONCLUSIVA')
        self.assertEqual(veredito_variacao([dict(fraco, ic95=None)])[0], 'SEM_DADOS')


if __name__ == '__main__':
    unittest.main()
