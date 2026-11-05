"""Regras de recuperação, contratos reais e preservação do produto público."""
import copy
import csv
import hashlib
import json
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from motor_cenarios.recuperacao.fontes import C, R, RAIZ, digest, verificar_fontes
from motor_cenarios.recuperacao.qualidade import checar, publicar
from motor_cenarios.recuperacao.selecao import selecionar
from motor_cenarios.recuperacao.__main__ import destino


def check(E, lado='agressivo', M=None, disc=True, **kw):
    M=[100]*5 if M is None else M
    nature='discrete_count' if disc else 'continuous_length'
    Epub=publicar(E,nature) if E and all(math.isfinite(v) and v>=0 for v in E) else E
    return checar(E,Epub,M,publicar(M,nature) if M else M,100,lado,disc,kw.get('p01',-1),kw.get('p99',1))


def fixture():
    k=('teste','quantidade')
    series={k:{str(i):{y:('observado',1000*math.exp((i-10)*.01*(y-2025)),False) for y in C.ANOS} for i in range(21)}}
    old=dict(hist=[[y,1000] for y in C.ANOS],conservador=None,moderado=[1000]*5,agressivo=None)
    pm=dict(conceito='teste',metrica='quantidade',unidade='itens',natureza='discrete_count',
            cenarios=dict(conservador=None,moderado='mod',agressivo=None),series={'10':old},modelos={'mod':{'wape':.1}})
    mod=dict(id='mod',categoria='O',trajetorias={'10':[1000.]*5},competitivo=False,elegivel=True,pontos=[],wape=.1,
             estatisticas={},algoritmo='mod',parametros={},variaveis=[],hash_configuracao='mod')
    return pm,{'candidatos':[mod]},series


class Qualidade(unittest.TestCase):
    def test_conservador_menor_moderado(self):
        self.assertEqual(check([90]*5,'conservador')[0],'COERENTE')
    def test_agressivo_maior_moderado(self):
        self.assertEqual(check([110]*5)[0],'COERENTE')
    def test_cruzamento_no_meio_nao_apenas_2030(self):
        self.assertEqual(check([110,110,90,110,110])[0],'CRUZA')
    def test_lado_oposto(self):
        self.assertEqual(check([90]*5)[0],'LADO_OPOSTO')
    def test_coincidencia(self):
        self.assertEqual(check([100]*5)[0],'COINCIDE')
    def test_nao_negativo(self):
        self.assertNotEqual(check([110,110,-1,110,110])[0],'COERENTE')
    def test_nan_infinito(self):
        for v in (float('nan'),float('inf')):
            self.assertNotEqual(check([110,110,v,110,110])[0],'COERENTE')
    def test_horizonte_completo(self):
        self.assertEqual(check([110]*4)[0],'CONTRATO_INVALIDO')
    def test_extremo_sem_moderado(self):
        self.assertEqual(check([110]*5,M=[])[0],'SEM_MODERADO')
    def test_contagens_inteiras_meio_para_cima(self):
        self.assertEqual(publicar([10.5,11.5,0,2.49,3.51],'discrete_count'),[11,12,0,2,4])
    def test_km_kva_tres_decimais(self):
        for unit in ('km','kVA'):
            self.assertEqual(publicar([1.23456]*5,C.mc.nature_of(unit)),[1.235]*5)
    def test_unidade_desconhecida_rejeitada(self):
        with self.assertRaises(ValueError): C.mc.nature_of('banana')
    def test_diferenca_criada_so_por_arredondamento_bloqueada(self):
        self.assertEqual(check([10.51]*5,M=[10.49]*5)[0],'IMPLAUSIVEL')
        st,q=checar([10.51]*5,[11]*5,[10.49]*5,[10]*5,10,'agressivo',True,-1,1)
        self.assertEqual(st,'COINCIDE'); self.assertFalse(q['Q8'])
    def test_diferenca_minima_real(self):
        self.assertEqual(check([100.001]*5)[0],'COINCIDE')
    def test_razao_implausivel(self):
        self.assertEqual(check([110,120,130,140,301])[0],'IMPLAUSIVEL')
    def test_salto_2026_implausivel(self):
        self.assertEqual(check([200,110,110,110,110],p01=-.1,p99=.1)[0],'IMPLAUSIVEL')
    def test_sem_percentis_nao_fabrica_evidencia(self):
        self.assertEqual(check([110]*5,p01=None,p99=None)[0],'SEM_EVIDENCIA_PERCENTIS')
    def test_q9_rejeita_decimal_em_contagem(self):
        self.assertEqual(checar([110]*5,[110.5]*5,[100]*5,[100]*5,100,'agressivo',True,-1,1)[0],'IMPLAUSIVEL')
    def test_ruptura_exclui_transicao(self):
        s={('a','quantidade'):{'1':{2022:('observado',10,False),2023:('observado',20,True),2024:('observado',22,False)}}}
        self.assertEqual([(d,t) for d,t,_ in R.transicoes(s,('a','quantidade'),2024)],[('1',2024)])
    def test_origem_exclui_futuro(self):
        _,_,s=fixture()
        first=R.transicoes(s,('teste','quantidade'),2023)
        for years in s[('teste','quantidade')].values(): years[2025]=('observado',1e12,False)
        self.assertEqual(first,R.transicoes(s,('teste','quantidade'),2023))


class Selecao(unittest.TestCase):
    def test_sem_candidato_nao_fabrica(self):
        p,b,s=fixture(); result,_=selecionar(p,b,s,'originais','hash')
        self.assertIsNone(result['series']['10']['agressivo'])
        self.assertIsNone(result['series']['10']['conservador'])
    def test_rejeitado_nao_volta_por_cobertura(self):
        p,b,s=fixture(); c=copy.deepcopy(b['candidatos'][0]); c.update(id='rejeitado',trajetorias={'10':[1100]*5})
        b['candidatos'].append(c)
        result,_=selecionar(p,b,s,'originais','hash')
        self.assertIsNone(result['series']['10']['agressivo'])
    def test_moderado_nulo_extremos_nulos(self):
        p,b,s=fixture(); p['series']['10']['moderado']=None
        result,_=selecionar(p,b,s,'condicionais','hash')
        self.assertEqual(result['series']['10']['completude'],'SEM_PREVISAO')
        self.assertTrue(all(v is None for v in result['series']['10']['extremos'].values()))
    def test_preservacao_input_moderado_e_nd(self):
        p,b,s=fixture(); p['series']['10']['erro_moderado']=None
        before=copy.deepcopy(p)
        result,_=selecionar(p,b,s,'originais','hash')
        self.assertEqual(p,before)
        self.assertEqual(result['series']['10']['moderado'],before['series']['10']['moderado'])
        self.assertIsNone(result['series']['10']['erro_moderado'])
    def test_determinismo(self):
        p,b,s=fixture()
        a=selecionar(p,b,s,'condicionais','hash'); z=selecionar(p,b,s,'condicionais','hash')
        self.assertEqual(digest(a),digest(z))
    def test_destino_publico_e_traversal_bloqueados(self):
        for name in ('../saida','/tmp/publico','../../web/public',''):
            with self.assertRaises(ValueError): destino(name)
    def test_fontes_congeladas_originais_intactas(self):
        self.assertGreater(len(verificar_fontes()),20)


class ContratoReal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=RAIZ/'motor_cenarios/experimental/recuperacao/piloto-final'
        cls.product=json.loads((cls.root/'produto.json').read_text())
        cls.pub=json.loads(R.ENTRADAS['publicado'].read_text())
        cls.m=cls.product['metricas'][0]
    def test_caso_real_consumidores_energisa_ac(self):
        s=self.m['series']['26']
        self.assertEqual(s['extremos']['agressivo']['modelo'],'knn_analogos')
        self.assertEqual(s['agressivo'][-1],340627)
    def test_gabarito_98_series_sem_divergencia(self):
        g=json.loads((self.root/'gabarito.json').read_text())
        self.assertEqual(g['series_comparadas'],98); self.assertEqual(g['divergencias'],[])
    def test_ordem_todas_series_todos_anos(self):
        for s in self.m['series'].values():
            for side,sign in [('conservador',-1),('agressivo',1)]:
                if s[side]:
                    self.assertTrue(all(sign*(a-b)>=0 for a,b in zip(s[side],s['moderado'])))
                    self.assertGreaterEqual(sign*(s[side][-1]-s['moderado'][-1]),1)
                    self.assertTrue(all(type(v)is int and v>=0 for v in s[side]))
    def test_trajetorias_json_csv_e_nd_identicos(self):
        for r in csv.DictReader((self.root/'cenarios.csv').open()):
            traj=self.m['series'][r['DIST']][r['cenario']]
            self.assertEqual([r[str(y)] for y in range(2026,2031)],[str(v) for v in traj] if traj else ['']*5)
    def test_potencia_eq_un_nao_soma_namespaces(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'potencia_trafos_tuc.csv'
            row=dict(tuc='565',eq=2,eq_vinculados=2,unidades=1,unidades_multi_tuc=0,
                     unidades_kva_padrao=1,dist='26',ano=2025,tipo_pot_nom='DOUBLE',potencia_kva=100)
            with path.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(row)); w.writeheader(); w.writerow(row)
            quantities={('trafo_dist','quantidade'):{'26':{2025:('observado',2,False)}}}
            power,diag=C.carregar_potencia(folder,quantities)
            self.assertTrue(diag[0]['valido'])
            self.assertEqual(power[('trafo_dist','potencia_kva')]['26'][2025],('observado',100.,False))
            self.assertEqual(quantities[('trafo_dist','quantidade')]['26'][2025][1],2)

    def test_total_sem_dupla_contagem_un_eq(self):
        m0=next(m for m in self.pub['metricas'] if m['conceito']=='consumidores')
        self.assertEqual(set(m0['series']),set(self.m['series']))
        for year in range(5):
            self.assertEqual(sum(s['moderado'][year] for s in m0['series'].values() if s['moderado']),
                             sum(s['moderado'][year] for s in self.m['series'].values() if s['moderado']))
    def test_modelos_e_regras_rastreaveis(self):
        for s in self.m['series'].values():
            for e in s['extremos'].values():
                if e:
                    self.assertTrue(e['hash_configuracao']); self.assertTrue(e['hash_proveniencia'])
                    self.assertTrue(all(e['regras']['Q'+str(i)] for i in range(1,10)))

if __name__=='__main__': unittest.main()
