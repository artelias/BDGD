"""R² pareado: mesmas partições, mesmo n, mesmo alvo; diferença por dobra (só leitura do produto)."""
import sys, json
import numpy as np
sys.path.insert(0, sys.argv[1])
from confiabilidade import estatistica as E
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
import sklearn; print('sklearn', sklearn.__version__)
linhas, _ = E.carregar(sys.argv[2])
X = E.matriz(linhas, E.VARIAVEIS); dists = np.array([l['dist'] for l in linhas]); anos = np.array([l['ano'] for l in linhas])
Z = np.column_stack([X, anos.reshape(-1, 1)]); iC = [E.VARIAVEIS.index(c) for c in E.CONTEXTO]; tudo = list(range(X.shape[1]))
def ridge(cols):
    pre = ColumnTransformer([('x', make_pipeline(SimpleImputer(strategy='median'), E.Winsor(), StandardScaler()), cols), ('ano', OneHotEncoder(drop='first'), [X.shape[1]])])
    return make_pipeline(pre, RidgeCV(alphas=np.logspace(-2, 3, 12)))
def rf(cols):
    pre = ColumnTransformer([('x', SimpleImputer(strategy='median'), cols), ('ano', 'passthrough', [X.shape[1]])])
    return make_pipeline(pre, RandomForestRegressor(n_estimators=200, min_samples_leaf=20, max_features=0.5, random_state=E.SEMENTE, n_jobs=2))
folds = list(GroupKFold(n_splits=5).split(Z, None, dists))
folds2 = list(GroupKFold(n_splits=5).split(Z, None, dists))
print('partições idênticas em chamadas repetidas:', all((a[1] == b[1]).all() for a, b in zip(folds, folds2)))
print('distribuidoras por dobra:', [len(np.unique(dists[te])) for _, te in folds], '| sem sobreposição treino/teste:', all(not set(dists[tr]) & set(dists[te]) for tr, te in folds))
fat = json.load(open(sys.argv[2] + '/fatores.json', encoding='utf-8'))
out = {}
for ind in ('dec', 'fec'):
    y = E.alvo(linhas, ind); res = {}
    for nome, fab, cols in (('ridge_ctx', ridge, iC), ('ridge_full', ridge, tudo), ('rf_full', rf, tudo), ('rf_ctx', rf, iC)):
        pred = np.full(len(y), np.nan)
        for tr, te in folds: pred[te] = fab(cols).fit(Z[tr], y[tr]).predict(Z[te])
        res[nome] = pred
    sst = np.sum((y - y.mean()) ** 2)
    r2 = {k: 1 - np.sum((y - p) ** 2) / sst for k, p in res.items()}
    pub = {m['modelo']: m['r2_fora'] for a in fat['alvos'] if a['alvo'] == ind for m in a['modelos']}
    print(f'\n{ind.upper()} n={len(y)}  R² recalculado:', {k: round(v, 4) for k, v in r2.items()}, '\n  publicado:', pub)
    for a, b in (('ridge_ctx', 'ridge_full'), ('rf_ctx', 'rf_full'), ('ridge_ctx', 'rf_full')):
        dob = []
        for _, te in folds:
            s = np.sum((y[te] - y[te].mean()) ** 2)
            dob.append((1 - np.sum((y[te] - res[b][te]) ** 2) / s) - (1 - np.sum((y[te] - res[a][te]) ** 2) / s))
        # IC do ganho por reamostragem de distribuidoras (predições fora da amostra fixas)
        rng = np.random.default_rng(E.SEMENTE); un = np.unique(dists); por = {d: np.flatnonzero(dists == d) for d in un}; bs = []
        for _ in range(1000):
            idx = np.concatenate([por[d] for d in rng.choice(un, len(un))]); yy = y[idx]; s = np.sum((yy - yy.mean()) ** 2)
            bs.append((np.sum((yy - res[a][idx]) ** 2) - np.sum((yy - res[b][idx]) ** 2)) / s)
        print(f'  ganho {a} → {b}: {r2[b]-r2[a]:+.4f} | por dobra {[round(v, 3) for v in dob]} | IC95 reamostragem de distribuidoras [{np.percentile(bs, 2.5):+.4f}; {np.percentile(bs, 97.5):+.4f}]')
