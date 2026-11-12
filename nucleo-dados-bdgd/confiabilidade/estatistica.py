"""Estudo dos fatores associados ao DEC/FEC dos conjuntos (observacional, exploratório).

    python -m confiabilidade.estatistica [--produto web/public/data/confiabilidade] [--reamostras 300]

Entrada: o produto publicado (distribuidoras/*.json), o mesmo que a interface lê. Saída: fatores.json (contrato da tela
Fatores) e a entrada correspondente no manifesto. Só numpy, scipy e scikit-learn.

Regras definidas ANTES de olhar os resultados (não mudam depois):
  amostra    conjunto-ano 2022–2025 com DEC e FEC oficiais nos 12 meses, infraestrutura da BDGD do mesmo ano, pelo menos
             100 consumidores e sem o alerta 'consumidores_divergentes' (métricas por consumidor pouco confiáveis);
  incerteza  intervalo de 95% por reamostragem de DISTRIBUIDORAS inteiras (conjuntos da mesma empresa não são independentes);
  contexto   porte (consumidores), densidade (UC/km²), parcela não urbana e consumo por consumidor;
  parcial    correlação de postos entre resíduos de y e de x depois de regredir ambos (em postos) no contexto;
  dentro     correlação depois de retirar a média de cada distribuidora-ano (escores normais dos postos);
  veredito   COMPATIVEL: parcial E dentro com IC 95% sem zero e no sinal esperado (ou, sem sinal esperado, no mesmo sinal);
             NAO_SUSTENTADA: parcial com IC sem zero no sinal oposto, ou |parcial| < 0,05 com os dois IC contendo zero;
             INCONCLUSIVA: demais casos; SEM_DADOS: menos de 200 observações com a variável.
Nada aqui indica causa: as frases da tela dizem "associação" e nunca "efeito".
"""
import argparse
import hashlib
import json
import math
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import stats

from . import contrato as K

RAIZ = Path(__file__).resolve().parents[1]
SEMENTE = 20261112
CONTEXTO = ['uc', 'uc_por_km2', 'pct_uc_rural', 'mwh_por_uc']
INFRA = ['km_mt_por_mil_uc', 'km_mt_por_alim', 'uc_por_alim', 'uc_por_trafo', 'sec_por_100km', 'relig_por_100km', 'tlcd_por_100km',
         'na_por_100km', 'conc_uc_top1', 'pct_km_mt_tri']
VARIAVEIS = CONTEXTO + INFRA
LOG = {'uc', 'uc_por_km2', 'mwh_por_uc', 'km_mt_por_mil_uc', 'km_mt_por_alim', 'uc_por_alim', 'uc_por_trafo', 'sec_por_100km'}
LOG1P = {'relig_por_100km', 'tlcd_por_100km', 'na_por_100km'}   # densidades com zeros e cauda longa
VARIACAO = ['km_mt', 'alim', 'trafos', 'sec', 'sec_religador', 'sec_tlcd', 'uc', 'relig_por_100km', 'tlcd_por_100km', 'uc_por_alim', 'km_mt_por_alim']
HIPOTESES = [  # id, enunciado, variável, alvo, sinal esperado (None = sem sinal esperado)
    ('H1', 'Mais quilômetros de rede MT por consumidor estão associados a DEC maior.', 'km_mt_por_mil_uc', 'dec', +1),
    ('H2', 'Alimentadores mais extensos dentro do conjunto (km MT por alimentador) estão associados a DEC maior.', 'km_mt_por_alim', 'dec', +1),
    ('H3', 'Mais consumidores por alimentador estão associados a FEC maior.', 'uc_por_alim', 'fec', +1),
    ('H4', 'A relação entre consumidores e transformadores está associada à continuidade (sem sinal esperado).', 'uc_por_trafo', 'dec', None),
    ('H5', 'Mais pontos de seccionamento por 100 km de rede MT estão associados a DEC menor.', 'sec_por_100km', 'dec', -1),
    ('H5b', 'Mais religadores por 100 km de rede MT estão associados a DEC menor.', 'relig_por_100km', 'dec', -1),
    ('H6a', 'Maior densidade de consumidores está associada a DEC menor.', 'uc_por_km2', 'dec', -1),
    ('H6b', 'Maior parcela de consumidores em área não urbana está associada a DEC maior.', 'pct_uc_rural', 'dec', +1),
]


# ------------------------------------------------------------------ dados
def carregar(produto):
    linhas, excl = [], defaultdict(int)
    for f in sorted((Path(produto) / 'distribuidoras').glob('*.json')):
        d = json.loads(f.read_text(encoding='utf-8'))
        for c in d['conjuntos']:
            for a, b in c['a'].items():
                if b['dec'] is None or b['fec'] is None or b['meses_dec'] < 12 or b['meses_fec'] < 12:
                    excl['apuracao_incompleta'] += 1; continue
                if not b['infra']:
                    excl['sem_infraestrutura'] += 1; continue
                if (b['infra'].get('uc') or 0) < 100:
                    excl['menos_de_100_consumidores'] += 1; continue
                if 'consumidores_divergentes' in b['alertas']:
                    excl['consumidores_divergentes'] += 1; continue
                linhas.append(dict(dist=d['dist'], c=c['c'], n=c['n'], ano=int(a), dec=b['dec'], fec=b['fec'], infra=b['infra'], alertas=b['alertas']))
    return linhas, dict(excl)


def matriz(linhas, vars_):
    X = np.full((len(linhas), len(vars_)), np.nan)
    for i, l in enumerate(linhas):
        for j, v in enumerate(vars_):
            x = l['infra'].get(v)
            if x is not None and math.isfinite(x) and (v not in LOG or x > 0):
                X[i, j] = math.log(x) if v in LOG else math.log1p(x) if v in LOG1P else x
    return X


def alvo(linhas, ind):
    return np.array([math.log(l[ind] + 0.1) for l in linhas])   # log(DEC + 0,1): DEC/FEC podem ser 0


# ------------------------------------------------------------------ estatísticas
def postos(v):
    return stats.rankdata(v) / (len(v) + 1)


def escore_normal(v):
    return stats.norm.ppf(postos(v))


def residuo(y, C):
    if C is None or C.shape[1] == 0:
        return y - y.mean()
    A = np.column_stack([np.ones(len(y)), C])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    return y - A @ beta


def correlacoes(y, x, C, grupos_da):
    """(bruta, parcial, dentro) para vetores já sem NaN."""
    ry, rx = postos(y), postos(x)
    bruta = float(np.corrcoef(ry, rx)[0, 1])
    rC = np.column_stack([postos(C[:, k]) for k in range(C.shape[1])]) if C is not None and C.shape[1] else None
    ey, ex = residuo(ry, rC), residuo(rx, rC)
    parcial = float(np.corrcoef(ey, ex)[0, 1]) if ey.std() > 0 and ex.std() > 0 else float('nan')
    zy, zx = escore_normal(y), escore_normal(x)
    dy, dx = zy.copy(), zx.copy()
    for g in np.unique(grupos_da):
        m = grupos_da == g
        dy[m] -= dy[m].mean(); dx[m] -= dx[m].mean()
    dentro = float(np.corrcoef(dy, dx)[0, 1]) if dy.std() > 0 and dx.std() > 0 else float('nan')
    return bruta, parcial, dentro


def bootstrap_dist(dists, funcao, B, rng):
    """Reamostra distribuidoras inteiras; devolve (B × k) com o resultado de funcao(índices)."""
    unicas = np.unique(dists)
    por = {d: np.flatnonzero(dists == d) for d in unicas}
    out = []
    for _ in range(B):
        esc = rng.choice(unicas, size=len(unicas), replace=True)
        idx = np.concatenate([por[d] for d in esc])
        try:
            out.append(funcao(idx))
        except (ValueError, np.linalg.LinAlgError):
            continue
    return np.array(out, dtype=float)


def ic(amostras):
    a = amostras[np.isfinite(amostras)]
    return [round(float(np.percentile(a, 2.5)), 4), round(float(np.percentile(a, 97.5)), 4)] if len(a) >= 20 else None


def r4(v):
    return None if v is None or not math.isfinite(v) else round(float(v), 4)


# ------------------------------------------------------------------ estudo por alvo
def estudar(linhas, ind, B, rng):
    y_all = alvo(linhas, ind)
    X = matriz(linhas, VARIAVEIS)
    dists = np.array([l['dist'] for l in linhas]); anos = np.array([l['ano'] for l in linhas])
    da = dists * 10000 + anos
    assoc = []
    for j, v in enumerate(VARIAVEIS):
        ctrl = [k for k, c in enumerate(VARIAVEIS) if c in CONTEXTO and c != v]
        ok = np.isfinite(X[:, j]) & np.all(np.isfinite(X[:, ctrl]), axis=1)
        n = int(ok.sum())
        if n < 200:
            assoc.append(dict(variavel=v, n=n, spearman=None, ic95=None, p=None, parcial=None, parcial_ic95=None, dentro_dist=None, dentro_dist_ic95=None,
                              estavel_por_ano=None, por_ano={})); continue
        y, x, C, g, ds, an = y_all[ok], X[ok, j], X[ok][:, ctrl], da[ok], dists[ok], anos[ok]
        bruta, parcial, dentro = correlacoes(y, x, C, g)
        p = float(stats.spearmanr(y, x).pvalue)
        boot = bootstrap_dist(ds, lambda idx: correlacoes(y[idx], x[idx], C[idx], g[idx]), B, rng)
        por_ano = {}
        for a in sorted(set(an.tolist())):
            m = an == a
            por_ano[str(a)] = r4(float(stats.spearmanr(y[m], x[m]).statistic)) if m.sum() >= 50 else None
        sinais = [np.sign(v_) for v_ in por_ano.values() if v_ is not None]
        assoc.append(dict(variavel=v, n=n, spearman=r4(bruta), ic95=ic(boot[:, 0]) if len(boot) else None, p=float(f'{p:.3g}'),
                          parcial=r4(parcial), parcial_ic95=ic(boot[:, 1]) if len(boot) else None,
                          dentro_dist=r4(dentro), dentro_dist_ic95=ic(boot[:, 2]) if len(boot) else None,
                          estavel_por_ano=(len(set(sinais)) == 1 and all(abs(v_) >= 0.05 for v_ in por_ano.values() if v_ is not None)) if sinais else None,
                          por_ano=por_ano))
    modelos, coef, imp, ref = modelar(linhas, y_all, X, dists, anos, ind, B, rng)
    return dict(alvo=ind, n=len(linhas), distribuidoras=int(len(np.unique(dists))), anos=sorted(set(anos.tolist())), associacoes=assoc,
                modelos=modelos, importancias=imp, coeficientes=coef, variacao=variacoes(linhas, ind, B, rng)), ref


class Winsor:
    """Limita cada variável ao intervalo de 1% a 99% observado NO TREINO (evita extrapolação em distribuidoras não vistas)."""
    def fit(self, A, y=None):
        self.lo_, self.hi_ = np.nanpercentile(A, 1, axis=0), np.nanpercentile(A, 99, axis=0)
        return self
    def transform(self, A):
        return np.clip(A, self.lo_, self.hi_)
    def fit_transform(self, A, y=None):
        return self.fit(A).transform(A)
    def get_params(self, deep=True):
        return {}
    def set_params(self, **k):
        return self


def modelar(linhas, y, X, dists, anos, ind, B, rng):
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.impute import SimpleImputer
    from sklearn.inspection import permutation_importance
    from sklearn.linear_model import RidgeCV
    from sklearn.model_selection import GroupKFold
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    from sklearn.compose import ColumnTransformer

    ok = np.isfinite(y)
    anos_col = anos.reshape(-1, 1)
    iC = [VARIAVEIS.index(c) for c in CONTEXTO]
    def pipe_ridge(cols):
        pre = ColumnTransformer([('x', make_pipeline(SimpleImputer(strategy='median'), Winsor(), StandardScaler()), cols), ('ano', OneHotEncoder(drop='first'), [X.shape[1]])])
        return make_pipeline(pre, RidgeCV(alphas=np.logspace(-2, 3, 12)))
    def pipe_rf(cols):
        pre = ColumnTransformer([('x', SimpleImputer(strategy='median'), cols), ('ano', 'passthrough', [X.shape[1]])])
        return make_pipeline(pre, RandomForestRegressor(n_estimators=200, min_samples_leaf=20, max_features=0.5, random_state=SEMENTE, n_jobs=2))
    Z = np.column_stack([X, anos_col])

    gk = GroupKFold(n_splits=5)
    resultados, oof_ctx = [], None
    for nome, fabrica, cols, nota in [
        ('Contexto (Ridge)', pipe_ridge, iC, 'porte, densidade, parcela não urbana, consumo por consumidor e ano'),
        ('Contexto + infraestrutura (Ridge)', pipe_ridge, list(range(X.shape[1])), 'todas as características e ano'),
        ('Contexto + infraestrutura (floresta aleatória)', pipe_rf, list(range(X.shape[1])), '200 árvores, folhas com 20 ou mais conjunto-anos'),
        ('Referência de contexto (floresta aleatória)', pipe_rf, iC, 'só contexto; usada na distância à referência'),
    ]:
        pred = np.full(len(y), np.nan)
        for tr, te in gk.split(Z, y, dists):
            mdl = fabrica(cols).fit(Z[tr], y[tr])
            pred[te] = mdl.predict(Z[te])
        r2 = 1 - np.sum((y - pred) ** 2) / np.sum((y - y.mean()) ** 2)
        resultados.append(dict(modelo=nome, r2_fora=r4(r2), mae_fora=r4(float(np.mean(np.abs(y - pred)))), n=int(ok.sum()), grupos=int(len(np.unique(dists))),
                               nota=nota + '; validação cruzada em 5 grupos de distribuidoras (o modelo não vê a distribuidora avaliada)'))
        if nome.startswith('Referência'):
            oof_ctx, r2_ctx = pred, r2
    # coeficientes padronizados (Ridge com todas as variáveis + ano) e IC por reamostragem de distribuidoras
    def ajustar_coef(idx):
        m = pipe_ridge(list(range(X.shape[1]))).fit(Z[idx], y[idx])
        return m[-1].coef_[:X.shape[1]]
    base = ajustar_coef(np.arange(len(y)))
    boot = bootstrap_dist(dists, ajustar_coef, max(50, B // 3), rng)
    coef = [dict(variavel=v, beta=r4(base[j]), ic95=ic(boot[:, j]) or [None, None]) for j, v in enumerate(VARIAVEIS)]
    # importância por permutação numa partição por grupos (teste = distribuidoras não vistas)
    tr, te = next(GroupKFold(n_splits=4).split(Z, y, dists))
    rf = pipe_rf(list(range(X.shape[1]))).fit(Z[tr], y[tr])
    pi = permutation_importance(rf, Z[te], y[te], n_repeats=5, random_state=SEMENTE, scoring='r2', n_jobs=1)
    imp = sorted([dict(variavel=v, importancia=r4(pi.importances_mean[j]), desvio=r4(pi.importances_std[j])) for j, v in enumerate(VARIAVEIS)],
                 key=lambda x: -(x['importancia'] or 0))
    # referência ajustada por contexto: ano mais recente, faixa de 80% dos resíduos fora da amostra (escala log)
    res = y - oof_ctx
    lo_q, hi_q = np.nanpercentile(res, [10, 90])
    ano_ref = int(anos.max())
    lin = []
    for i in np.flatnonzero(anos == ano_ref):
        refv = math.exp(oof_ctx[i]) - 0.1
        obs = linhas[i][ind]
        lin.append([linhas[i]['dist'], linhas[i]['c'], linhas[i]['n'], round(obs, 2), round(max(refv, 0), 2),
                    round(max(math.exp(oof_ctx[i] + lo_q) - 0.1, 0), 2), round(max(math.exp(oof_ctx[i] + hi_q) - 0.1, 0), 2), round(obs - refv, 2)])
    ref = dict(ano=ano_ref, alvo=ind, modelo='floresta aleatória só com contexto, treinada sem a distribuidora avaliada', r2_fora=r4(r2_ctx),
               campos=['dist', 'c', 'n', 'obs', 'ref', 'lo', 'hi', 'residuo'], linhas=lin)
    return resultados, coef, imp, ref


def variacoes(linhas, ind, B, rng):
    """Δ log(característica) 2022→2025 × Δ log(indicador) no mesmo conjunto (contemporâneo) e Δ 2022→2023 × Δ 2023→2025 (defasado).
    Só conjuntos sem alerta de reconfiguração cadastral em nenhum dos anos usados."""
    por = defaultdict(dict)
    for l in linhas:
        por[(l['dist'], l['c'])][l['ano']] = l
    out = []
    for v in VARIACAO:
        for rot, (a0, a1, b0, b1) in (('2022→2025', (2022, 2025, 2022, 2025)), ('2022→2023 × indicador 2023→2025', (2022, 2023, 2023, 2025))):
            dx, dy, ds = [], [], []
            for (dist, c), anos in por.items():
                if not all(a in anos for a in {a0, a1, b0, b1}):
                    continue
                if any(al.startswith('variacao_cadastral') for a in {a0, a1, b0, b1} for al in anos[a]['alertas']):
                    continue
                x0, x1 = anos[a0]['infra'].get(v), anos[a1]['infra'].get(v)
                if x0 is None or x1 is None or x0 <= 0 or x1 <= 0:
                    continue
                dx.append(math.log(x1 / x0)); dy.append(math.log((anos[b1][ind] + 0.1) / (anos[b0][ind] + 0.1))); ds.append(dist)
            if len(dx) < 200:
                out.append(dict(variavel=f'{v} ({rot})', n=len(dx), spearman=None, ic95=None)); continue
            dx, dy, ds = np.array(dx), np.array(dy), np.array(ds)
            rho = float(stats.spearmanr(dx, dy).statistic)
            boot = bootstrap_dist(ds, lambda idx: [stats.spearmanr(dx[idx], dy[idx]).statistic], max(100, B // 2), rng)
            out.append(dict(variavel=f'{v} ({rot})', n=int(len(dx)), spearman=r4(rho), ic95=ic(boot[:, 0])))
    return out


def veredito(assoc, sinal):
    if assoc is None or assoc['n'] < 200 or assoc['parcial'] is None:
        return 'SEM_DADOS'
    p, pi, di, d = assoc['parcial'], assoc['parcial_ic95'], assoc['dentro_dist_ic95'], assoc['dentro_dist']
    if not pi or not di:
        return 'INCONCLUSIVA'
    sem_zero = lambda i: i[0] > 0 or i[1] < 0
    sinal_ic = lambda i: 1 if i[0] > 0 else -1
    if sem_zero(pi) and sem_zero(di) and sinal_ic(pi) == sinal_ic(di) and (sinal is None or sinal_ic(pi) == sinal):
        return 'COMPATIVEL'
    if sinal is not None and sem_zero(pi) and sinal_ic(pi) == -sinal:
        return 'NAO_SUSTENTADA'
    if abs(p) < 0.05 and not sem_zero(pi) and not sem_zero(di):
        return 'NAO_SUSTENTADA'
    return 'INCONCLUSIVA'


def hipoteses(alvos):
    out = []
    por = {a['alvo']: {x['variavel']: x for x in a['associacoes']} for a in alvos}
    for hid, enun, var, ind, sinal in HIPOTESES:
        a = por.get(ind, {}).get(var)
        v = veredito(a, sinal)
        ev = 'Sem amostra suficiente.' if v == 'SEM_DADOS' else (
            f"{ind.upper()}: bruta {a['spearman']:+.2f}, parcial (contexto) {a['parcial']:+.2f} [IC95% {a['parcial_ic95'][0]:+.2f}; {a['parcial_ic95'][1]:+.2f}], "
            f"dentro da distribuidora {a['dentro_dist']:+.2f} [{a['dentro_dist_ic95'][0]:+.2f}; {a['dentro_dist_ic95'][1]:+.2f}]; n = {a['n']:,}".replace(',', '.') +
            ('; mesmo sinal nos quatro anos.' if a['estavel_por_ano'] else '; o sinal ou a força mudam entre os anos.'))
        out.append(dict(id=hid, enunciado=enun, veredito=v, evidencia=ev))
    # H7: evolução da infraestrutura × evolução posterior do indicador
    var7 = [x for a in alvos for x in a['variacao'] if '2022→2023 ×' in x['variavel'] and x['variavel'].split(' (')[0] in ('relig_por_100km', 'tlcd_por_100km', 'km_mt_por_alim', 'uc_por_alim')]
    com = [x for x in var7 if x['ic95']]
    sig = [x for x in com if x['ic95'][0] > 0 or x['ic95'][1] < 0]
    if not com:
        v7, ev7 = 'SEM_DADOS', 'Amostra insuficiente de conjuntos comparáveis entre 2022 e 2025.'
    elif sig:
        v7, ev7 = 'INCONCLUSIVA', 'Associações defasadas com IC 95% sem zero: ' + '; '.join(f"{x['variavel']} {x['spearman']:+.2f}" for x in sig) + '. Quatro anos e mudanças cadastrais limitam a leitura temporal.'
    else:
        v7, ev7 = 'NAO_SUSTENTADA', 'Nenhuma variação de religadores, telecomando, extensão ou carga por alimentador em 2022→2023 tem associação com IC 95% sem zero com a variação posterior do indicador (2023→2025).'
    out.append(dict(id='H7', enunciado='Mudanças da infraestrutura entre 2022 e 2023 estão associadas a mudanças posteriores de DEC/FEC (2023→2025).', veredito=v7, evidencia=ev7))
    return out


def executar(produto=RAIZ / 'web/public/data/confiabilidade', B=300):
    t0 = time.time()
    produto = Path(produto)
    rng = np.random.default_rng(SEMENTE)
    linhas, excl = carregar(produto)
    alvos, refs = [], []
    for ind in ('dec', 'fec'):
        a, r = estudar(linhas, ind, B, rng)
        alvos.append(a); refs.append(r)
    doc = dict(
        contrato=K.VERSAO_CONTRATO, gerado_em=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), estado=K.DERIVADO_EXPLORATORIO, demonstrativo=False,
        metodo=('Estudo observacional com os conjuntos de todas as distribuidoras: correlação de postos (Spearman) bruta, parcial ao contexto e dentro de cada '
                'distribuidora-ano; regressão Ridge e floresta aleatória com validação cruzada por distribuidora; intervalos de 95% por reamostragem de '
                f'distribuidoras inteiras ({B} réplicas). Alvo dos modelos: log(indicador + 0,1). Regras de amostra e de veredito definidas antes dos resultados.'),
        limitacoes=[
            'Associação não é causa: conjuntos com mais religadores podem tê-los justamente por terem histórico de DEC alto (causalidade reversa).',
            'Clima, vegetação, descargas atmosféricas, idade dos ativos, práticas de manutenção e automação efetiva não estão nos dados.',
            'A infraestrutura é a fotografia cadastral de 31/12 de cada ano; o DEC/FEC é apurado ao longo do ano.',
            'Conjuntos da mesma distribuidora compartilham operação e cadastro; por isso os intervalos reamostram distribuidoras, não conjuntos.',
            'Quatro anos (2022–2025) e mudanças de cadastro limitam a análise de variações; conjuntos com reconfiguração cadastral foram excluídos dela.',
            'Os valores da BDGD são declarados pelas distribuidoras e não foram homologados por este módulo.',
            'A competência 2025 de DEC/FEC já está consolidada nos dados abertos usados; não há validação em dados futuros.'],
        amostra=dict(conjunto_anos=len(linhas), conjuntos=len({(l['dist'], l['c']) for l in linhas}), distribuidoras=len({l['dist'] for l in linhas}),
                     anos=sorted({l['ano'] for l in linhas}), excluidos=excl),
        alvos=alvos, hipoteses=hipoteses(alvos), referencias=refs, referencia=refs[0])
    destino = produto / 'fatores.json'
    texto = json.dumps(doc, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    destino.with_suffix('.parcial').write_text(texto, encoding='utf-8')
    destino.with_suffix('.parcial').replace(destino)
    man_p = produto / 'manifesto.json'
    man = json.loads(man_p.read_text(encoding='utf-8'))
    man['arquivos'] = [a for a in man['arquivos'] if a['caminho'] != 'fatores.json'] + [dict(caminho='fatores.json', bytes=destino.stat().st_size, sha256=hashlib.sha256(destino.read_bytes()).hexdigest())]
    man_p.write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(dict(amostra=doc['amostra'], hipoteses=[(h['id'], h['veredito']) for h in doc['hipoteses']],
                          modelos={a['alvo']: [(m['modelo'], m['r2_fora']) for m in a['modelos']] for a in alvos}, segundos=round(time.time() - t0, 1)), ensure_ascii=False))
    return doc


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--produto', default=str(RAIZ / 'web/public/data/confiabilidade'))
    ap.add_argument('--reamostras', type=int, default=300)
    a = ap.parse_args()
    executar(a.produto, a.reamostras)
