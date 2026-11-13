"""Dicionário das métricas do módulo e cálculo das métricas relativas (uma única definição, usada na publicação e nos testes).

tipo: 'contagem' (inteiro), 'continua' (km, kVA, MWh, km²), 'razao' (por unidade), 'pct' (0–1).
sentido: só documenta a leitura física; não é juízo de desempenho.
"""
from .contrato import finito, razao

# id, nome, unidade, tipo, grupo, definição
METRICAS = [
    ('uc', 'Consumidores (BDGD, 31/12)', 'unidades', 'contagem', 'Consumidores', 'Unidades consumidoras ativas distintas (COD_ID anonimizado + ponto de conexão, SIT_ATIV = AT) em UCBT, UCMT e UCAT do conjunto.'),
    ('uc_bt', 'Consumidores BT', 'unidades', 'contagem', 'Consumidores', 'Unidades consumidoras ativas de baixa tensão (UCBT).'),
    ('uc_mt_at', 'Consumidores MT e AT', 'unidades', 'contagem', 'Consumidores', 'Unidades consumidoras ativas de média e alta tensão (UCMT + UCAT). De 1 a 4 unidades o valor não é publicado.'),
    ('pct_uc_rural', 'Consumidores em área não urbana', '%', 'pct', 'Território', 'Parcela das unidades consumidoras BT e MT ativas com ARE_LOC = NU (não urbana), segundo o cadastro da distribuidora.'),
    ('area_km2', 'Área do conjunto', 'km²', 'continua', 'Território', 'Área geodésica do polígono do conjunto publicado na BDGD 2025 (camada CONJ).'),
    ('uc_por_km2', 'Densidade de consumidores', 'UC/km²', 'razao', 'Território', 'Consumidores ÷ área do conjunto.'),
    ('mwh_por_uc', 'Consumo anual por consumidor', 'MWh/UC', 'razao', 'Território', 'Energia anual das unidades ativas (soma de ENE_01..12, kWh → MWh) ÷ consumidores.'),
    ('ug_por_mil_uc', 'Geração distribuída por mil consumidores', 'UG/mil UC', 'razao', 'Território', 'Unidades geradoras ativas (UGBT + UGMT) ÷ consumidores × 1000.'),
    ('km_mt', 'Rede de média tensão', 'km', 'continua', 'Rede', 'SUM(SSDMT.COMP)/1000 dos trechos do conjunto (comprimento declarado).'),
    ('km_bt', 'Rede de baixa tensão', 'km', 'continua', 'Rede', 'SUM(SSDBT.COMP)/1000 dos trechos do conjunto (comprimento declarado).'),
    ('pct_km_mt_rural', 'Rede MT em área não urbana', '%', 'pct', 'Rede', 'Parcela da extensão MT em trechos com ARE_LOC = NU.'),
    ('pct_km_mt_tri', 'Rede MT trifásica', '%', 'pct', 'Rede', 'Parcela da extensão MT em trechos com três fases (FAS_CON com A, B e C).'),
    ('km_mt_por_mil_uc', 'Rede MT por mil consumidores', 'km/mil UC', 'razao', 'Rede', 'Extensão MT ÷ consumidores × 1000.'),
    ('km_bt_por_mil_uc', 'Rede BT por mil consumidores', 'km/mil UC', 'razao', 'Rede', 'Extensão BT ÷ consumidores × 1000.'),
    ('km_mt_por_km2', 'Rede MT por área', 'km/km²', 'razao', 'Rede', 'Extensão MT ÷ área do conjunto.'),
    ('alim', 'Alimentadores com rede no conjunto', 'alimentadores', 'contagem', 'Alimentadores', 'Circuitos MT (CTMT) distintos com pelo menos um trecho de rede MT cadastrado no conjunto. Um alimentador pode atender mais de um conjunto.'),
    ('alim_pred', 'Alimentadores predominantes', 'alimentadores', 'contagem', 'Alimentadores', 'Alimentadores cuja maior extensão MT está neste conjunto.'),
    ('subs', 'Subestações de origem', 'subestações', 'contagem', 'Alimentadores', 'Subestações (CTMT.SUB) distintas dos alimentadores com rede no conjunto.'),
    ('km_mt_por_alim', 'Rede MT por alimentador', 'km/alim.', 'razao', 'Alimentadores', 'Extensão MT do conjunto ÷ alimentadores com rede no conjunto (trecho médio de alimentador dentro do conjunto).'),
    ('km_mt_maior_alim', 'Maior trecho de alimentador', 'km', 'continua', 'Alimentadores', 'Maior extensão MT de um único alimentador dentro do conjunto.'),
    ('uc_por_alim', 'Consumidores por alimentador', 'UC/alim.', 'razao', 'Alimentadores', 'Consumidores ÷ alimentadores com rede no conjunto.'),
    ('conc_uc_top1', 'Consumidores no maior alimentador', '%', 'pct', 'Alimentadores', 'Parcela dos consumidores BT e MT do conjunto ligada ao alimentador com mais consumidores.'),
    ('conc_uc_top3', 'Consumidores nos 3 maiores alimentadores', '%', 'pct', 'Alimentadores', 'Parcela dos consumidores BT e MT nos três alimentadores com mais consumidores.'),
    ('conc_km_gini', 'Desigualdade de extensão entre alimentadores', 'índice 0–1', 'razao', 'Alimentadores', 'Índice de Gini das extensões MT dos alimentadores dentro do conjunto (0 = extensões iguais).'),
    ('trafos', 'Transformadores de distribuição', 'equipamentos', 'contagem', 'Transformação', 'Equipamentos EQTRMT com TUC 565 instalados em unidades (UNTRMT) do conjunto. Equipamentos, não instalações.'),
    ('trafo_un', 'Instalações transformadoras MT', 'instalações', 'contagem', 'Transformação', 'Unidades UNTRMT ativas do conjunto. Visão por instalação: não somar com os equipamentos.'),
    ('trafo_pot_kva', 'Potência nominal das instalações', 'kVA', 'continua', 'Transformação', 'SUM(UNTRMT.POT_NOM) das unidades ativas, como declarado. Não homologada: há distribuidoras que declaram em outra escala.'),
    ('uc_por_trafo', 'Consumidores por transformador', 'UC/trafo', 'razao', 'Transformação', 'Consumidores BT ÷ transformadores de distribuição.'),
    ('trafos_por_alim', 'Transformadores por alimentador', 'trafos/alim.', 'razao', 'Transformação', 'Transformadores de distribuição ÷ alimentadores com rede no conjunto.'),
    ('kva_por_uc', 'Potência instalada por consumidor', 'kVA/UC', 'razao', 'Transformação', 'Potência nominal das instalações ÷ consumidores BT.'),
    ('pct_trafo_mrt', 'Instalações em rede monofilar (MRT)', '%', 'pct', 'Transformação', 'Parcela das instalações transformadoras ativas com MRT = 1.'),
    ('sec', 'Pontos de seccionamento e proteção MT', 'instalações', 'contagem', 'Seccionamento e proteção', 'Unidades seccionadoras MT (UNSEMT) ativas: chaves, fusíveis, religadores, seccionalizadores e disjuntores. Instalações, não equipamentos.'),
    ('sec_fusivel', 'Chaves fusíveis', 'instalações', 'contagem', 'Seccionamento e proteção', 'UNSEMT ativas com TIP_UNID de chave fusível ou fusível (DDA TUNI 22–27, 46).'),
    ('sec_manobra', 'Chaves de manobra', 'instalações', 'contagem', 'Seccionamento e proteção', 'UNSEMT ativas com TIP_UNID de chave faca, seccionadora, a gás, a óleo, motorizada ou de transferência.'),
    ('sec_religador', 'Religadores', 'instalações', 'contagem', 'Seccionamento e proteção', 'UNSEMT ativas com TIP_UNID = 32 (religador).'),
    ('sec_seccionalizador', 'Seccionalizadores', 'instalações', 'contagem', 'Seccionamento e proteção', 'UNSEMT ativas com TIP_UNID 35 ou 36.'),
    ('sec_tlcd', 'Pontos telecomandados', 'instalações', 'contagem', 'Seccionamento e proteção', 'UNSEMT ativas com TLCD = 1 (telecomando), de qualquer tipo.'),
    ('sec_na', 'Pontos normalmente abertos', 'instalações', 'contagem', 'Seccionamento e proteção', 'UNSEMT ativas com posição normal de operação aberta (P_N_OPE = A): pontos de interligação ou manobra.'),
    ('sec_por_100km', 'Pontos de seccionamento por 100 km MT', 'inst./100 km', 'razao', 'Seccionamento e proteção', 'Pontos de seccionamento e proteção ÷ extensão MT × 100.'),
    ('relig_por_100km', 'Religadores por 100 km MT', 'inst./100 km', 'razao', 'Seccionamento e proteção', 'Religadores ÷ extensão MT × 100.'),
    ('tlcd_por_100km', 'Pontos telecomandados por 100 km MT', 'inst./100 km', 'razao', 'Seccionamento e proteção', 'Pontos telecomandados ÷ extensão MT × 100.'),
    ('na_por_100km', 'Pontos normalmente abertos por 100 km MT', 'inst./100 km', 'razao', 'Seccionamento e proteção', 'Pontos normalmente abertos ÷ extensão MT × 100.'),
    ('uc_por_relig', 'Consumidores por religador', 'UC/relig.', 'razao', 'Seccionamento e proteção', 'Consumidores ÷ religadores.'),
    ('eq160', 'Chaves (equipamentos, TUC 160)', 'equipamentos', 'contagem', 'Seccionamento e proteção', 'Equipamentos EQSE com TUC 160 em instalações MT do conjunto. Visão patrimonial: não somar com os pontos de seccionamento.'),
    ('eq345', 'Religadores (equipamentos, TUC 345)', 'equipamentos', 'contagem', 'Seccionamento e proteção', 'Equipamentos EQSE com TUC 345 em instalações MT do conjunto.'),
    ('reg_eq', 'Reguladores de tensão', 'equipamentos', 'contagem', 'Regulação', 'Equipamentos EQRE em unidades reguladoras MT (UNREMT) do conjunto.'),
]
IDS = [m[0] for m in METRICAS]
TIPO = {m[0]: m[3] for m in METRICAS}
CASAS = {'continua': 3, 'razao': 4, 'pct': 4}


def dicionario():
    return [dict(id=i, nome=n, unidade=u, tipo=t, grupo=g, definicao=d) for i, n, u, t, g, d in METRICAS]


def _soma(*v):
    """Soma com ausência preservada: None se TODAS as parcelas faltarem; parcela ausente entre presentes também anula (sem subtotal silencioso)."""
    if any(x is None for x in v):
        return None
    return sum(v)


def derivar(m, area_km2=None, k=5):
    """m = métricas-base de infra.py para um conjunto e ano -> dict {id: valor|None} com as métricas publicadas."""
    g = m.get
    uc_bt, uc_mt, uc_at = g('uc_bt'), g('uc_mt'), g('uc_at')
    uc = None if uc_bt is None else uc_bt + (uc_mt or 0) + (uc_at or 0)
    mt_at = None if uc_bt is None else (uc_mt or 0) + (uc_at or 0)
    rural_n = _soma(g('uc_bt_rural'), g('uc_mt_rural') if uc_mt else 0)
    ene = None
    if uc is not None and uc >= k and g('ene_bt_mwh') is not None:
        ene = g('ene_bt_mwh') + (g('ene_mt_mwh') or 0) + (g('ene_at_mwh') or 0)
    km_mt, km_bt = g('km_mt'), g('km_bt')
    o = dict(
        uc=uc, uc_bt=uc_bt, uc_mt_at=None if mt_at is None or 0 < mt_at < k else mt_at,
        pct_uc_rural=razao(rural_n, (uc_bt or 0) + (uc_mt or 0)) if rural_n is not None else None,
        area_km2=area_km2, uc_por_km2=razao(uc, area_km2), mwh_por_uc=razao(ene, uc),
        ug_por_mil_uc=None if g('ug') is None or not uc else 1000 * g('ug') / uc,
        km_mt=km_mt, km_bt=km_bt, pct_km_mt_rural=razao(g('km_mt_rural'), km_mt) if g('km_mt_rural') is not None else None,
        pct_km_mt_tri=razao(g('km_mt_tri'), km_mt) if g('km_mt_tri') is not None else None,
        km_mt_por_mil_uc=_mil(km_mt, uc), km_bt_por_mil_uc=_mil(km_bt, uc), km_mt_por_km2=razao(km_mt, area_km2),
        alim=g('alim'), alim_pred=g('alim_pred'), subs=g('subs'), km_mt_por_alim=razao(km_mt, g('alim')), km_mt_maior_alim=g('km_mt_maior_alim'),
        uc_por_alim=razao(uc, g('alim')), conc_uc_top1=g('conc_uc_top1'), conc_uc_top3=g('conc_uc_top3'), conc_km_gini=g('conc_km_gini'),
        trafos=g('trafos'), trafo_un=g('trafo_un'), trafo_pot_kva=g('trafo_pot_kva'), uc_por_trafo=razao(uc_bt, g('trafos')),
        trafos_por_alim=razao(g('trafos'), g('alim')), kva_por_uc=razao(g('trafo_pot_kva'), uc_bt),
        pct_trafo_mrt=razao(g('trafo_un_mrt'), g('trafo_un')) if g('trafo_un_mrt') is not None else None,
        sec=g('sec'), sec_fusivel=g('sec_fusivel'), sec_manobra=g('sec_manobra'), sec_religador=g('sec_religador'), sec_seccionalizador=g('sec_seccionalizador'),
        sec_tlcd=g('sec_tlcd'), sec_na=g('sec_na'), sec_por_100km=_cem(g('sec'), km_mt), relig_por_100km=_cem(g('sec_religador'), km_mt),
        tlcd_por_100km=_cem(g('sec_tlcd'), km_mt), na_por_100km=_cem(g('sec_na'), km_mt), uc_por_relig=razao(uc, g('sec_religador')),
        eq160=g('eq160'), eq345=g('eq345'), reg_eq=g('reg_eq'),
    )
    out = {}
    for i in IDS:
        v = o.get(i)
        if v is None or not finito(v):
            out[i] = None
        elif TIPO[i] == 'contagem':
            if v != int(v):
                raise ValueError(f'contagem não inteira em {i}: {v!r}')
            out[i] = int(v)
        else:
            out[i] = round(v, CASAS[TIPO[i]])
    return out


def _mil(a, b):
    r = razao(a, b)
    return None if r is None else 1000 * r


def _cem(a, b):
    r = razao(a, b)
    return None if r is None else 100 * r
