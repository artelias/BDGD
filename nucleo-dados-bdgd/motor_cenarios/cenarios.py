"""Motor de Expansão Elétrica — cenários CONSERVADOR | MODERADO | AGRESSIVO por métrica física.

Os cenários são interpretações de modelos efetivamente executados e validados com a mesma origem temporal,
não nomes de algoritmos:
  MODERADO     = modelo de menor erro retrospectivo (WAPE sobre os mesmos pontos), entre os fisicamente plausíveis;
  CONSERVADOR  = modelo plausível, dentro da tolerância de erro do moderado, com a menor trajetória agregada abaixo dele;
  AGRESSIVO    = idem, com a maior trajetória agregada acima dele.
Sem modelo que satisfaça a regra, o cenário fica INDISPONÍVEL (nunca preenchido com número artificial).

Entradas: contrato nacional (serie_fisica_nacional.csv), variáveis internas extraídas dos Parquets
(extrair_features.py) e variáveis externas do IBGE (raw JSON do SIDRA, com SHA-256 e data de divulgação).
Uso: python cenarios.py <contrato_dir> <entrada_dir> <entrada_dir> <saida_dir> [<web_json>] [--check]
(entrada_dir contém as variáveis internas extraídas dos Parquets e o CSV municipal do IBGE; --check regenera em
diretório temporário e compara com o produto versionado, sem sobrescrever nada.)
"""
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ANOS = [2022, 2023, 2024, 2025]
BASE = 2025
HORIZONTE = [2026, 2027, 2028, 2029, 2030]
ORIGENS = [2023, 2024]          # rolling origin: treino só com informação até a origem
TOLERANCIA_ERRO = 1.25           # cenários alternativos: WAPE até 25% acima do moderado
RAZAO_PLAUSIVEL = (0.5, 3.0)     # 2030/2025 por série: fora disso a trajetória é fisicamente implausível
MAX_IMPLAUSIVEL = 0.05           # modelo inelegível se >5% das séries ficarem implausíveis
MIN_SERIES_PAINEL = 15           # pares mínimos de treino para modelos de painel
DIFERENCA_MINIMA_PP = 0.05       # cenários distintos: diferença mínima de 0,05 p.p./ano na trajetória agregada

# Variáveis externas (documentação): fonte, divulgação e referência. Só entram se divulgadas até a 1ª origem (31/12/2023).
EXTERNAS = {
    "pop_censo2010": {"arquivo": "pop_censo2010.json", "tabela": "SIDRA 1378 (v93)", "referencia": "2010-08-01", "divulgacao": "2011-11-29",
                      "url": "https://apisidra.ibge.gov.br/values/t/1378/n6/all/v/93/p/2010/c1/0/c2/0/c287/0/c455/0"},
    "pop_censo2022": {"arquivo": "pop_censo2022.json", "tabela": "SIDRA 4709 (v93)", "referencia": "2022-08-01", "divulgacao": "2023-08-31",
                      "url": "https://apisidra.ibge.gov.br/values/t/4709/n6/all/v/93/p/2022"},
    "pop_estimativa2021": {"arquivo": "pop_estimativa_2021.json", "tabela": "SIDRA 6579 (v9324)", "referencia": "2021-07-01", "divulgacao": "2021-08-27",
                           "url": "https://apisidra.ibge.gov.br/values/t/6579/n6/all/v/9324/p/2021"},
    "pib_municipal": {"arquivo": "pib_mun_2020_2023.json", "tabela": "SIDRA 5938 (v37)", "referencia": "2021", "divulgacao": "2023-12-15",
                      "url": "https://apisidra.ibge.gov.br/values/t/5938/n6/all/v/37/p/2020,2021,2022,2023"},
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


# ---------------------------------------------------------------- dados
def carregar_contrato(d):
    series = defaultdict(dict)   # (conceito, metrica) -> dist -> {ano: (estado, valor, ruptura)}
    empresas, unidades = {}, {}
    for r in csv.DictReader(open(Path(d) / "serie_fisica_nacional.csv", encoding="utf-8")):
        k = (r["conceitoId"], r["metrica"])
        v = float(r["valor"]) if r["valor"] != "" else None
        series[k].setdefault(r["dist"], {})[int(r["ano"])] = (r["estado"], v, r["ruptura_desde_ano_anterior"] == "true")
        empresas.setdefault(r["dist"], r["empresa"])
        unidades[k] = r["unidade"]
    return series, empresas, unidades


def segmento(anos):
    """Segmento contíguo de observações positivas que termina no ano-base, cortado em ruptura cadastral."""
    seg = []
    for a in reversed(ANOS):
        e = anos.get(a)
        if not e or e[0] != "observado" or not (e[1] or 0) > 0:
            break
        seg.insert(0, (a, e[1]))
        if e[2]:                  # ruptura desde o ano anterior: o ano anterior não é comparável
            break
    return seg if seg and seg[-1][0] == BASE else []


def carregar_potencia(internas, quantidades):
    """Séries experimentais de potência (kVA) por TUC via EQ→UN, com portões de qualidade por DIST-ano."""
    p = Path(internas) / "potencia_trafos_tuc.csv"
    if not p.exists():
        return {}, []
    alvo = {"565": "trafo_dist", "570": "trafo_forca"}
    res, diag = {(c, "potencia_kva"): defaultdict(dict) for c in alvo.values()}, []
    for r in csv.DictReader(open(p, encoding="utf-8")):
        conc = alvo.get(r["tuc"])
        if not conc:
            continue
        eq, vinc, un = int(r["eq"]), int(r["eq_vinculados"]), int(r["unidades"])
        multi, padrao = int(r["unidades_multi_tuc"]), int(r["unidades_kva_padrao"])
        cob = vinc / eq if eq else 0
        q = quantidades.get((conc, "quantidade"), {}).get(r["dist"], {}).get(int(r["ano"]))
        motivos = []
        if cob < 0.98: motivos.append("VINCULO_EQ_UN_ABAIXO_98PCT")
        if un and multi / un > 0.01: motivos.append("UNIDADES_COM_TUC_MISTO")
        if conc == "trafo_dist" and un and padrao / un < 0.80: motivos.append("POT_NOM_FORA_DA_ESCALA_KVA")
        if not q or q[0] != "observado" or abs(q[1] - eq) > 0.01 * max(q[1], 1): motivos.append("QUANTIDADE_DIVERGE_DO_CONTRATO")
        if "VARCHAR" in r["tipo_pot_nom"]: motivos.append("POT_NOM_TEXTUAL")
        ok = not motivos and float(r["potencia_kva"]) > 0
        res[(conc, "potencia_kva")][r["dist"]][int(r["ano"])] = (
            "observado" if ok else "nao_homologado", float(r["potencia_kva"]) if ok else None, bool(q and q[2]))
        diag.append({"conceito": conc, "ano": r["ano"], "dist": r["dist"], "eq": eq, "cobertura_vinculo": round(cob, 4),
                     "potencia_kva": r["potencia_kva"], "valido": ok, "motivos": "|".join(motivos)})
    return {k: dict(v) for k, v in res.items()}, diag


def externas_por_dist(raw, internas):
    """Variáveis municipais do IBGE ponderadas pelas UC ativas de cada DIST no ano (atributo MUN da UC)."""
    ext = {}
    for r in csv.DictReader(open(Path(raw) / "externas_ibge_municipal.csv", encoding="utf-8")):
        ext[r["mun"]] = {k: float(v) for k, v in r.items() if k != "mun" and v != ""}
    pesos = defaultdict(lambda: defaultdict(float))
    for r in csv.DictReader(open(Path(internas) / "uc_por_municipio.csv", encoding="utf-8")):
        pesos[(int(r["ano"]), r["dist"])][r["mun"]] += float(r["uc_ativas"])
    feat, cob = {}, {}
    for k, ws in pesos.items():
        tot = sum(ws.values())
        cres, pibpc, wc, wp = 0.0, 0.0, 0.0, 0.0
        for mun, w in ws.items():
            e = ext.get(mun, {})
            a, b = e.get("pop_2010"), e.get("pop_2022")
            if a and b:
                cres += w * ((b / a) ** (1 / 12) - 1); wc += w
            p, q = e.get("pib_2021_mil_reais"), e.get("pop_2021")
            if p and q:
                pibpc += w * math.log(p * 1000 / q); wp += w
        feat[k] = {"ext_cresc_pop_2010_2022": cres / wc if wc else None, "ext_ln_pib_pc_2021": pibpc / wp if wp else None}
        cob[k] = {"cobertura_mun_pop": wc / tot if tot else 0, "cobertura_mun_pib": wp / tot if tot else 0}
    return feat, cob


def internas_por_dist(series, internas):
    ene = {}
    for r in csv.DictReader(open(Path(internas) / "energia_uc.csv", encoding="utf-8")):
        ene[(int(r["ano"]), r["dist"])] = float(r["energia_uc_mwh"]) or None
    def val(k, d, a):
        e = series.get(k, {}).get(d, {}).get(a)
        return e[1] if e and e[0] == "observado" and (e[1] or 0) > 0 else None
    feat = {}
    dists = {d for k in series for d in series[k]}
    for d in dists:
        for a in ANOS:
            uc, bt, mt = val(("consumidores", "quantidade"), d, a), val(("rede_bt", "extensao_km"), d, a), val(("rede_mt", "extensao_km"), d, a)
            en = ene.get((a, d))
            feat[(a, d)] = {
                "int_ln_uc": math.log(uc) if uc else None,
                "int_ln_km_bt": math.log(bt) if bt else None,
                "int_ln_km_mt": math.log(mt) if mt else None,
                "int_ln_uc_por_km_bt": math.log(uc / bt) if uc and bt else None,
                "int_mwh_por_uc": en / uc if en and uc else None,
            }
    return feat


# ---------------------------------------------------------------- modelos
MODELOS = {
    "persistencia": {"nome": "Persistência (passeio aleatório sem deriva)", "familia": "baseline", "complexidade": 0,
                     "formula": "ŷ(T+h) = y(T)"},
    "deriva": {"nome": "Passeio aleatório com deriva (drift)", "familia": "baseline de tendência", "complexidade": 1,
               "formula": "ŷ(T+h) = y(T) + h·(y(T) − y(T0))/(T − T0)"},
    "tendencia_ols": {"nome": "Tendência linear por mínimos quadrados (OLS)", "familia": "regressão temporal por série", "complexidade": 2,
                      "formula": "ŷ(t) = a + b·t, (a,b) = argmin Σ(y(t) − a − b·t)² no segmento"},
    "crescimento_geometrico": {"nome": "Crescimento geométrico histórico (CAGR)", "familia": "baseline de crescimento", "complexidade": 2,
                               "formula": "ŷ(T+h) = y(T)·(1+g)^h, g = (y(T)/y(T0))^(1/(T−T0)) − 1"},
    "ridge_painel": {"nome": "Regressão Ridge em painel (log-crescimento anual)", "familia": "regressão linear penalizada (L2)", "complexidade": 3,
                     "formula": "ĝ = β0 + xᵀβ, β = argmin Σ(g − β0 − xᵀβ)² + α‖β‖², α=1; ŷ(T+h) = y(T)·exp(h·ĝ)"},
    "ridge_painel_ext": {"nome": "Ridge em painel com variáveis externas IBGE", "familia": "regressão linear penalizada (L2)", "complexidade": 4,
                         "formula": "igual ao Ridge em painel, com x acrescido de crescimento populacional 2010–2022 e ln PIB per capita 2021"},
    "knn_analogos": {"nome": "k vizinhos mais próximos (distribuidoras análogas)", "familia": "não paramétrico por similaridade", "complexidade": 5,
                     "formula": "ĝ = mediana dos log-crescimentos dos k=9 pares de treino mais próximos em x padronizado; ŷ(T+h) = y(T)·exp(h·ĝ)"},
    "random_forest_painel": {"nome": "Random Forest em painel (log-crescimento anual)", "familia": "ensemble de árvores (bagging)", "complexidade": 6,
                             "formula": "ĝ = média de 300 árvores (min_samples_leaf=5, max_features=0,5, semente 42); ŷ(T+h) = y(T)·exp(h·ĝ)"},
    "hgb_painel": {"nome": "HistGradientBoosting em painel (log-crescimento anual)", "familia": "boosting de árvores", "complexidade": 7,
                   "formula": "ĝ = Σ árvores de gradiente (max_iter=150, learning_rate=0,05, max_depth=3, min_samples_leaf=10, semente 42); ŷ(T+h) = y(T)·exp(h·ĝ)"},
}
FEAT_INT = ["ln_estoque", "ln_estoque_por_uc", "int_ln_uc", "int_ln_km_bt", "int_ln_km_mt", "int_ln_uc_por_km_bt", "int_mwh_por_uc"]
FEAT_EXT = ["ext_cresc_pop_2010_2022", "ext_ln_pib_pc_2021"]
PAINEL = {"ridge_painel": FEAT_INT, "ridge_painel_ext": FEAT_INT + FEAT_EXT, "knn_analogos": FEAT_INT,
          "random_forest_painel": FEAT_INT, "hgb_painel": FEAT_INT}


def univariado(modelo, hist, h):
    (t0, y0), (t1, y1) = hist[0], hist[-1]
    if modelo == "persistencia":
        return y1
    if modelo == "deriva":
        return y1 + h * (y1 - y0) / (t1 - t0)
    if modelo == "crescimento_geometrico":
        return y1 * (y1 / y0) ** (h / (t1 - t0))
    if modelo == "tendencia_ols":
        t = np.array([a for a, _ in hist], float); y = np.array([v for _, v in hist], float)
        b, a = np.polyfit(t, y, 1)
        return a + b * (t1 + h)
    raise KeyError(modelo)


def vetor(feats, nomes):
    return [np.nan if feats.get(n) is None else feats[n] for n in nomes]


def treinar_painel(modelo, X, g):
    from sklearn.pipeline import make_pipeline
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import Ridge
    from sklearn.neighbors import KNeighborsRegressor
    from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
    lo, hi = np.quantile(g, [0.05, 0.95])      # winsorização do alvo ajustada só no treino (mudanças cadastrais extremas)
    g = np.clip(g, lo, hi)
    est = {"ridge_painel": lambda: Ridge(alpha=1.0), "ridge_painel_ext": lambda: Ridge(alpha=1.0),
           "knn_analogos": lambda: KNeighborsRegressor(n_neighbors=9),
           "random_forest_painel": lambda: RandomForestRegressor(n_estimators=300, min_samples_leaf=5, max_features=0.5, random_state=42, n_jobs=1),
           "hgb_painel": lambda: HistGradientBoostingRegressor(max_iter=150, learning_rate=0.05, max_depth=3, min_samples_leaf=10, random_state=42)}[modelo]()
    m = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), est)
    if modelo == "knn_analogos":
        class Mediana:     # KNN com mediana dos vizinhos (robusta a crescimentos cadastrais atípicos)
            def __init__(s, pipe): s.pipe = pipe
            def fit(s, X, y):
                s.pipe.fit(X, y); s.y = np.asarray(y); return s
            def predict(s, X):
                Z = s.pipe[:-1].transform(X)
                idx = s.pipe[-1].kneighbors(Z, return_distance=False)
                return np.median(s.y[idx], axis=1)
        m = Mediana(m)
    m.fit(np.asarray(X, float), g)
    return m, (float(lo), float(hi))


class Motor:
    def __init__(self, series, feat_int, feat_ext):
        self.series, self.fi, self.fe = series, feat_int, feat_ext

    def feats(self, dist, ano, y, uc_key=("consumidores", "quantidade")):
        f = dict(self.fi.get((ano, dist), {}))
        f.update(self.fe.get((ano, dist), {}) or {})
        f["ln_estoque"] = math.log(y)
        uc = self.series.get(uc_key, {}).get(dist, {}).get(ano)
        f["ln_estoque_por_uc"] = math.log(y / uc[1]) if uc and uc[0] == "observado" and (uc[1] or 0) > 0 else None
        return f

    def pares_treino(self, k, origem, nomes):
        """Pares (x_{t−1}, ln(y_t/y_{t−1})) com t ≤ origem, dentro de segmentos comparáveis (sem ruptura/lacuna)."""
        X, g = [], []
        for dist, anos in self.series[k].items():
            for t in ANOS:
                if t > origem or t - 1 not in anos or t not in anos:
                    continue
                a, b = anos[t - 1], anos[t]
                if a[0] != "observado" or b[0] != "observado" or not (a[1] or 0) > 0 or not (b[1] or 0) > 0 or b[2]:
                    continue
                X.append(vetor(self.feats(dist, t - 1, a[1]), nomes)); g.append(math.log(b[1] / a[1]))
        return X, np.array(g)

    def prever(self, k, origem, alvos):
        """Previsões de todos os candidatos na origem, só com informação até a origem.
        alvos: {dist: hist_até_origem}. Retorna {modelo: {dist: [ŷ(origem+h) for h in 1..H]}} e diagnósticos."""
        H = 5 if origem == BASE else BASE - origem
        out, diag = defaultdict(dict), {}
        for m in ("persistencia", "deriva", "tendencia_ols", "crescimento_geometrico"):
            for d, hist in alvos.items():
                if len(hist) >= 2:
                    out[m][d] = [univariado(m, hist, h) for h in range(1, H + 1)]
        for m, nomes in PAINEL.items():
            X, g = self.pares_treino(k, origem, nomes)
            if len(g) < MIN_SERIES_PAINEL:
                diag[m] = f"TREINO_INSUFICIENTE ({len(g)} pares < {MIN_SERIES_PAINEL})"
                continue
            mod, clip = treinar_painel(m, X, g)
            diag[m] = {"pares_treino": len(g), "winsor_alvo": clip}
            ds = [d for d, hist in alvos.items() if len(hist) >= 1]
            if not ds:
                continue
            Xp = [vetor(self.feats(d, origem, alvos[d][-1][1]), nomes) for d in ds]
            gp = mod.predict(np.asarray(Xp, float))
            for d, gg in zip(ds, gp):
                out[m][d] = [alvos[d][-1][1] * math.exp(h * float(gg)) for h in range(1, H + 1)]
        return out, diag


# ---------------------------------------------------------------- avaliação e cenários
def erros(pares):
    if not pares:
        return {"n": 0, "mae": None, "rmse": None, "wape": None, "vies_rel": None, "mdape": None}
    y = np.array([p[0] for p in pares]); yh = np.array([p[1] for p in pares]); e = yh - y
    return {"n": len(pares), "mae": float(np.mean(np.abs(e))), "rmse": float(np.sqrt(np.mean(e ** 2))),
            "wape": float(np.sum(np.abs(e)) / np.sum(np.abs(y))) if np.sum(np.abs(y)) else None,
            "vies_rel": float(np.sum(e) / np.sum(y)) if np.sum(y) else None,
            "mdape": float(np.median(np.abs(e) / y))}


def executar_metrica(motor, k):
    S = motor.series[k]
    segs = {d: segmento(anos) for d, anos in S.items()}
    # --- backtest: mesmas origens e mesmos pontos para todos os modelos
    pontos = defaultdict(dict)       # modelo -> {(h, origem, dist): (y, ŷ)}
    diag_bt = {}
    for o in ORIGENS:
        alvos = {d: [p for p in s if p[0] <= o] for d, s in segs.items()}
        alvos = {d: h for d, h in alvos.items() if len(h) >= 2}
        prev, dg = motor.prever(k, o, alvos)
        diag_bt[o] = dg
        for m, por_dist in prev.items():
            for d, traj in por_dist.items():
                real = dict(segs[d])
                for h in range(1, BASE - o + 1):
                    if o + h in real:
                        pontos[m][(h, o, d)] = (real[o + h], traj[h - 1])
    # mesmos folds e pontos para todos: referência = pontos da persistência; candidato incompleto é inelegível
    ref = set(pontos.get("persistencia", {}))
    bt = {}
    for m in MODELOS:
        if ref and ref <= set(pontos.get(m, {})):
            bt[m] = [(*pontos[m][key], *key) for key in sorted(ref)]
        elif m in pontos or m in PAINEL:
            bt[m] = None                    # executado parcialmente ou não treinável: fora da seleção
    # --- projeção final a partir da base 2025
    alvos = {d: s for d, s in segs.items() if len(s) >= 3}
    prev, diag_final = motor.prever(k, BASE, alvos)
    return segs, bt, prev, diag_bt, diag_final


def pp(x):
    return f"{x * 100:.2f}%".replace(".", ",")


def escolher_cenarios(bt, prev, segs):
    met = {}
    for m, pts in bt.items():
        if pts is None:
            met[m] = {"erros": erros([]), "por_h": {1: erros([]), 2: erros([])}, "por_origem_h1": {o: erros([]) for o in ORIGENS},
                      "estabilidade_wape_h1": None, "cagr_agregado": None, "series_projetadas": len(prev.get(m, {})), "implausiveis": 0,
                      "elegivel": False, "motivo": "BACKTEST_INCOMPLETO_OU_TREINO_INSUFICIENTE"}
            continue
        e = erros([(y, yh) for y, yh, *_ in pts])
        e_h = {h: erros([(y, yh) for y, yh, hh, *_ in pts if hh == h]) for h in (1, 2)}
        e_o = {o: erros([(y, yh) for y, yh, hh, oo, _ in pts if hh == 1 and oo == o]) for o in ORIGENS}
        fut = prev.get(m, {})
        base = {d: segs[d][-1][1] for d in fut}
        razoes = [fut[d][-1] / base[d] for d in fut if base[d] > 0]
        implaus = sum(1 for r in razoes if not (RAZAO_PLAUSIVEL[0] <= r <= RAZAO_PLAUSIVEL[1]) or not math.isfinite(r))
        neg = any(v < 0 or not math.isfinite(v) for d in fut for v in fut[d])
        tot0 = sum(base.values()); tot5 = sum(fut[d][-1] for d in fut)
        cagr = (tot5 / tot0) ** (1 / 5) - 1 if tot0 > 0 and tot5 > 0 else None
        estab = abs(e_o[2023]["wape"] - e_o[2024]["wape"]) if e_o[2023]["wape"] is not None and e_o[2024]["wape"] is not None else None
        motivo = None
        if e["n"] == 0: motivo = "SEM_PONTOS_DE_BACKTEST"
        elif neg: motivo = "PROJECAO_NEGATIVA_OU_NAO_FINITA"
        elif razoes and implaus / len(razoes) > MAX_IMPLAUSIVEL: motivo = f"TRAJETORIA_IMPLAUSIVEL ({implaus}/{len(razoes)} séries fora de {RAZAO_PLAUSIVEL})"
        elif not fut: motivo = "SEM_PROJECAO_FINAL"
        met[m] = {"erros": e, "por_h": e_h, "por_origem_h1": e_o, "estabilidade_wape_h1": estab, "cagr_agregado": cagr,
                  "series_projetadas": len(fut), "implausiveis": implaus, "elegivel": motivo is None, "motivo": motivo}
    eleg = [m for m in met if met[m]["elegivel"] and met[m]["erros"]["wape"] is not None]
    cen = {"conservador": None, "moderado": None, "agressivo": None}
    just = {}
    if not eleg:
        return met, cen, {"moderado": "Nenhum modelo elegível", "conservador": "Indisponível", "agressivo": "Indisponível"}
    w = {m: met[m]["erros"]["wape"] for m in eleg}
    mod = min(eleg, key=lambda m: (round(w[m], 6), MODELOS[m]["complexidade"]))
    cen["moderado"] = mod
    just["moderado"] = f"Menor WAPE retrospectivo ({pp(w[mod])}) entre {len(eleg)} modelos plausíveis, avaliados nos mesmos {met[mod]['erros']['n']} pontos de backtest"
    tol = [m for m in eleg if m != mod and w[m] <= TOLERANCIA_ERRO * w[mod] and met[m]["cagr_agregado"] is not None]
    gm = met[mod]["cagr_agregado"]
    baixo = [m for m in tol if gm is not None and met[m]["cagr_agregado"] < gm - DIFERENCA_MINIMA_PP / 100]
    alto = [m for m in tol if gm is not None and met[m]["cagr_agregado"] > gm + DIFERENCA_MINIMA_PP / 100]
    if baixo:
        c = min(baixo, key=lambda m: met[m]["cagr_agregado"]); cen["conservador"] = c
        just["conservador"] = f"Menor crescimento agregado da métrica ({pp(met[c]['cagr_agregado'])}/ano, WAPE {pp(w[c])}) entre modelos com WAPE até {TOLERANCIA_ERRO:.2f}× o do moderado".replace("1.25", "1,25")
    else:
        just["conservador"] = "Indisponível: nenhum modelo plausível, dentro da tolerância de erro, com trajetória abaixo do moderado"
    if alto:
        a = max(alto, key=lambda m: met[m]["cagr_agregado"]); cen["agressivo"] = a
        just["agressivo"] = f"Maior crescimento agregado da métrica ({pp(met[a]['cagr_agregado'])}/ano, WAPE {pp(w[a])}) entre modelos com WAPE até {TOLERANCIA_ERRO:.2f}× o do moderado".replace("1.25", "1,25")
    else:
        just["agressivo"] = "Indisponível: nenhum modelo plausível, dentro da tolerância de erro, com trajetória acima do moderado"
    return met, cen, just


def estado_metrica(cen, met):
    n = sum(1 for v in cen.values() if v)
    if not cen["moderado"]:
        return "bloqueado"
    if cen["moderado"] == "persistencia" and n == 1:
        return "somente_baseline"
    return {3: "tres_cenarios", 2: "dois_cenarios", 1: "somente_moderado"}[n]


def main(contrato, internas, raw, saida, web=None):
    saida = Path(saida); saida.mkdir(parents=True, exist_ok=True)
    series, empresas, unidades = carregar_contrato(contrato)
    pot, diag_pot = carregar_potencia(internas, series)
    for k, v in pot.items():
        series[k] = v; unidades[k] = "kVA"
    fi = internas_por_dist(series, internas)
    fe, cob_ext = externas_por_dist(raw, internas)
    motor = Motor(series, fi, fe)
    catalogo = json.load(open(Path(contrato).parents[1] / "etl/bdgd2025/config/conceitos_2025.json", encoding="utf-8"))
    nomes = {a["id"]: (a["nome"], a.get("familia", "")) for a in catalogo["ativos"]}
    matriz, backtest_rows, cen_rows, web_metricas = [], [], [], []
    uso_vars = defaultdict(set)
    chaves = sorted(series)
    for k in chaves:
        conc, metr = k
        segs, bt, prev, diag_bt, diag_final = executar_metrica(motor, k)
        met, cen, just = escolher_cenarios(bt, prev, segs)
        est = estado_metrica(cen, met)
        experimental = metr == "potencia_kva"
        for slot, m in cen.items():
            if m in PAINEL:
                for v in PAINEL[m]:
                    uso_vars[v].add(f"{conc}/{metr}:{slot}:{m}")
        for m, x in met.items():
            for h, e in x["por_h"].items():
                backtest_rows.append({"conceito": conc, "metrica": metr, "modelo": m, "horizonte": h, **{f"{a}": e[a] for a in e},
                                      "wape_total": x["erros"]["wape"], "melhor_que_persistencia": (x["erros"]["wape"] or 9) < (met.get("persistencia", {}).get("erros", {}).get("wape") or 0) if "persistencia" in met else None,
                                      "elegivel": x["elegivel"], "motivo": x["motivo"] or ""})
        pers = met.get("persistencia", {}).get("erros", {}).get("wape")
        series_pub = {}
        for d, s in segs.items():
            if not s:
                continue
            linha = {"hist": [[a, v] for a, v in s]}
            for slot, m in cen.items():
                traj = prev.get(m, {}).get(d) if m else None
                if traj and s[-1][1] > 0:
                    r = traj[-1] / s[-1][1]
                    if not (RAZAO_PLAUSIVEL[0] <= r <= RAZAO_PLAUSIVEL[1]):
                        traj = None
                linha[slot] = [round(v, 3) for v in traj] if traj else None
                cen_rows.append({"conceito": conc, "metrica": metr, "dist": d, "empresa": empresas.get(d, ""), "cenario": slot, "modelo": m or "",
                                 **{str(a): (round(v, 3) if traj else "") for a, v in zip(HORIZONTE, traj or [None] * 5)},
                                 "base_2025": s[-1][1], "anos_historico": len(s),
                                 "status": ("indisponivel_metrica" if not m else "indisponivel_serie" if not traj else
                                            ("experimental" if experimental else "simulacao_validada_retrospectivamente"))})
            # erro observado da série no modelo moderado (pontos de backtest da própria DIST)
            pts = [(y, yh) for y, yh, h, o, dd in (bt.get(cen["moderado"]) or []) if dd == d] if cen["moderado"] else []
            linha["erro_moderado"] = erros(pts)["mdape"] if pts else None
            series_pub[d] = linha
        matriz.append({"conceito": conc, "ativo": nomes.get(conc, (conc,))[0], "familia": nomes.get(conc, ("", ""))[1], "metrica": metr,
                       "unidade": unidades.get(k, ""), "estado": est, "experimental": experimental,
                       "conservador": cen["conservador"] or "", "moderado": cen["moderado"] or "", "agressivo": cen["agressivo"] or "",
                       "wape_conservador": met[cen["conservador"]]["erros"]["wape"] if cen["conservador"] else "",
                       "wape_moderado": met[cen["moderado"]]["erros"]["wape"] if cen["moderado"] else "",
                       "wape_agressivo": met[cen["agressivo"]]["erros"]["wape"] if cen["agressivo"] else "",
                       "wape_persistencia": pers if pers is not None else "",
                       "moderado_melhor_que_persistencia": bool(cen["moderado"] and pers and met[cen["moderado"]]["erros"]["wape"] < pers),
                       "pontos_backtest": met[cen["moderado"]]["erros"]["n"] if cen["moderado"] else 0,
                       "series_com_historico": sum(1 for s in segs.values() if s), "series_projetadas": sum(1 for x in series_pub.values() if x.get("moderado")),
                       "justificativa_conservador": just.get("conservador", ""), "justificativa_moderado": just.get("moderado", ""),
                       "justificativa_agressivo": just.get("agressivo", "")})
        web_metricas.append({"conceito": conc, "ativo": nomes.get(conc, (conc,))[0], "familia": nomes.get(conc, ("", ""))[1], "metrica": metr, "unidade": unidades.get(k, ""), "estado": est, "experimental": experimental,
                             "cenarios": cen, "justificativas": just,
                             "modelos": {m: {"wape": x["erros"]["wape"], "mae": x["erros"]["mae"], "rmse": x["erros"]["rmse"], "vies": x["erros"]["vies_rel"],
                                             "mdape": x["erros"]["mdape"], "n": x["erros"]["n"], "wape_h1": x["por_h"][1]["wape"], "wape_h2": x["por_h"][2]["wape"],
                                             "estabilidade": x["estabilidade_wape_h1"], "cagr": x["cagr_agregado"], "elegivel": x["elegivel"], "motivo": x["motivo"]}
                                         for m, x in met.items()},
                             "diagnostico_painel": {str(o): {m: v for m, v in dg.items()} for o, dg in {**diag_bt, BASE: diag_final}.items()},
                             "series": series_pub})
    # combinações catalogadas sem série derivável: aparecem como bloqueadas, nunca com números
    BLOQ = {("reguladores", "potencia_kva"): "EQRE.POT_NOM é código de domínio e UNREMT não possui POT_NOM numérico: potência não derivável sem tabela de domínio auditada",
            ("trafo_medida", "potencia_kva"): "Potência de transformadores de medida não derivada nesta execução: não há vínculo EQ→UN com POT_NOM numérico auditado"}
    for a in catalogo["ativos"]:
        # universo de 29 combinações do motor universal: inclui potência de transformadores de medida
        for metr in dict.fromkeys([a.get("medida", "quantidade"), *a.get("medidas_extra", []), *[m for (c, m) in BLOQ if c == a["id"]]]):
            k = (a["id"], metr)
            if k in series:
                continue
            motivo = BLOQ.get(k, "Sem série histórica comparável no contrato nacional")
            just = {"conservador": f"Indisponível: {motivo}", "moderado": f"Indisponível: {motivo}", "agressivo": f"Indisponível: {motivo}"}
            matriz.append({**{c: "" for c in matriz[0]}, "conceito": a["id"], "ativo": a["nome"], "familia": a.get("familia", ""), "metrica": metr,
                           "unidade": "kVA" if metr == "potencia_kva" else "", "estado": "bloqueado", "experimental": metr == "potencia_kva",
                           "moderado_melhor_que_persistencia": False, "pontos_backtest": 0, "series_com_historico": 0, "series_projetadas": 0,
                           "justificativa_conservador": just["conservador"], "justificativa_moderado": just["moderado"], "justificativa_agressivo": just["agressivo"]})
            web_metricas.append({"conceito": a["id"], "ativo": a["nome"], "familia": a.get("familia", ""), "metrica": metr,
                                 "unidade": "kVA" if metr == "potencia_kva" else "", "estado": "bloqueado", "experimental": metr == "potencia_kva",
                                 "cenarios": {"conservador": None, "moderado": None, "agressivo": None}, "justificativas": just,
                                 "modelos": {}, "diagnostico_painel": {}, "series": {}})
    # ---------------- arquivos
    def wcsv(nome, rows):
        with open(saida / nome, "w", encoding="utf-8", newline="\n") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n"); w.writeheader(); w.writerows(rows)
    wcsv("MATRIZ_MODELO_POR_METRICA.csv", matriz)
    wcsv("BACKTEST_MODELOS_POR_HORIZONTE.csv", backtest_rows)
    wcsv("CENARIOS_CONSERVADOR_MODERADO_AGRESSIVO.csv", cen_rows)
    if diag_pot:
        wcsv("QUALIDADE_POTENCIA_EQ_UN.csv", diag_pot)
    vars_rows = variaveis(uso_vars, cob_ext)
    wcsv("VARIAVEIS_INTERNAS_EXTERNAS.csv", vars_rows)
    fontes = {f"entrada/{n}": sha(Path(raw) / n) for n in ("externas_ibge_municipal.csv", "externas_ibge_manifesto.json")}
    fontes.update({f"internas/{n}": sha(Path(internas) / n) for n in ("uc_por_municipio.csv", "energia_uc.csv", "potencia_trafos_tuc.csv")})
    fontes["contrato/serie_fisica_nacional.csv"] = sha(Path(contrato) / "serie_fisica_nacional.csv")
    fontes["codigo/cenarios.py"] = sha(__file__)
    man = {"versao": "motor-cenarios-1", "base": BASE, "horizonte": HORIZONTE, "origens_backtest": ORIGENS,
           "parametros": {"tolerancia_erro": TOLERANCIA_ERRO, "razao_plausivel_2030_2025": RAZAO_PLAUSIVEL, "max_implausivel": MAX_IMPLAUSIVEL,
                          "min_pares_painel": MIN_SERIES_PAINEL, "diferenca_minima_pp_ano": DIFERENCA_MINIMA_PP},
           "fontes_sha256": fontes, "saidas_sha256": {n: sha(saida / n) for n in sorted(p.name for p in saida.glob("*.csv"))}}
    json.dump(man, open(saida / "MANIFESTO.json", "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    if web:
        web_doc = {"schema_version": "cenarios-motor-1", "base": BASE, "horizonte": HORIZONTE, "origens_backtest": ORIGENS,
                   "parametros": man["parametros"], "modelos": MODELOS, "variaveis": vars_rows,
                   "empresas": empresas, "fontes_sha256": fontes, "metricas": web_metricas,
                   "intervalos": None, "previsao_validada": False}
        Path(web).parent.mkdir(parents=True, exist_ok=True)
        txt = json.dumps(web_doc, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        Path(web).write_text(txt, encoding="utf-8", newline="\n")
    return matriz


def variaveis(uso, cob_ext):
    usadas = lambda v: sorted({x.split(":")[2] for x in uso.get(v, set())})
    cobp = [c["cobertura_mun_pop"] for c in cob_ext.values()]; cobi = [c["cobertura_mun_pib"] for c in cob_ext.values()]
    linhas = [
        ("ln_estoque", "Todos", "interna", "Contrato nacional BDGD (serie_fisica_nacional.csv)", "31/12 do próprio ano (divulgação ANEEL posterior)", "ln do estoque na origem", "série DIST×ativo×métrica"),
        ("ln_estoque_por_uc", "Todos", "interna", "Contrato nacional BDGD", "idem", "ln(estoque/UC ativas)", "DIST"),
        ("int_ln_uc", "Todos", "interna", "Contrato nacional — consumidores (regra UC v3)", "idem", "ln UC ativas", "DIST"),
        ("int_ln_km_bt", "Todos", "interna", "Contrato nacional — rede BT (km)", "idem", "ln km", "DIST"),
        ("int_ln_km_mt", "Todos", "interna", "Contrato nacional — rede MT (km)", "idem", "ln km", "DIST"),
        ("int_ln_uc_por_km_bt", "Todos", "interna", "Contrato nacional — UC e rede BT", "idem", "ln(UC/km BT)", "DIST"),
        ("int_mwh_por_uc", "Todos", "interna", "Parquets BDGD UCBT/UCMT/UCAT — ENE_01..12 (kWh)", "idem", "MWh declarados por UC ativa (sem deduplicação de registros)", "DIST"),
        ("ext_cresc_pop_2010_2022", "Todos", "externa", "IBGE Censo 2010 (SIDRA 1378) e Censo 2022 (SIDRA 4709)", "2023-08-31 (Censo 2022 revisado)", f"crescimento anual composto 2010–2022, ponderado por UC ativas do ano por município (cobertura mediana {np.median(cobp):.3f})", "município→DIST via MUN da UC"),
        ("ext_ln_pib_pc_2021", "Todos", "externa", "IBGE PIB dos Municípios 2021 (SIDRA 5938) / estimativa populacional 2021 (SIDRA 6579)", "2023-12-15", f"ln PIB per capita 2021 ponderado por UC (cobertura mediana {np.median(cobi):.3f})", "município→DIST via MUN da UC"),
    ]
    rows = [{"variavel": v, "ativos": a, "tipo": t, "fonte": f, "disponivel_em": d, "transformacao": tr, "associacao": assoc,
             "defasagem": "valor na origem (t−1 para o alvo t)" if t == "interna" else "estática (divulgada antes da 1ª origem 31/12/2023)",
             "disponivel": "sim", "utilizada": "sim" if usadas(v) else "não (testada, sem modelo selecionado)" if v.startswith("ext_") or v in FEAT_INT else "não",
             "modelos_que_usaram": "|".join(usadas(v))} for v, a, t, f, d, tr, assoc in linhas]
    nao = [
        ("pop_estimativas_2024_2025", "externa", "IBGE estimativas municipais 2024 e 2025 (SIDRA 6579)", "2024-08-29 / 2025-08", "Não utilizada: inexistente na origem 2023 (sem estimativa 2023); usá-la só nas origens seguintes mudaria o conjunto de variáveis entre folds"),
        ("pib_municipal_2022_2023", "externa", "IBGE PIB dos Municípios 2022–2023 (SIDRA 5938)", "2025-12-19", "Não utilizada: divulgada após as origens 2023/2024 e com mudança de ano-base (2010→2021) do SCN"),
        ("mercado_aneel_samp", "externa", "ANEEL — SAMP / mercado de distribuição", "não obtido", "Não utilizada: não integrada nesta execução"),
        ("dec_fec_aneel", "externa", "ANEEL — indicadores DEC/FEC por conjunto", "não obtido", "Não utilizada: não integrada; DIC/FIC das UC existem nos Parquets mas não foram agregados"),
        ("epe_projecoes", "externa", "EPE — projeções de demanda (PDE)", "não obtido", "Não utilizada: cenário futuro externo não integrado"),
        ("atributos_tuc_a1_a6", "interna", "Cubos DDA/TUC 2025", "apenas 2025", "Não utilizada: sem série histórica comparável 2022–2024 no contrato"),
    ]
    rows += [{"variavel": v, "ativos": "Todos", "tipo": t, "fonte": f, "disponivel_em": d, "transformacao": "", "associacao": "",
              "defasagem": "", "disponivel": "não" if d == "não obtido" else "parcial", "utilizada": "não", "modelos_que_usaram": "", } | {"transformacao": m}
             for v, t, f, d, m in nao]
    return rows


def verificar(contrato, internas, raw, saida, web):
    """Regenera em diretório temporário e compara escolhas de modelo (exatas) e números (tolerância relativa 1e-6)."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        main(contrato, internas, raw, Path(tmp) / "saida", Path(tmp) / "web.json")
        novo = json.loads((Path(tmp) / "web.json").read_text(encoding="utf-8"))
    pub = json.loads(Path(web).read_text(encoding="utf-8"))
    erros = []
    def cmp(a, b, cam):
        if isinstance(a, dict) and isinstance(b, dict):
            if set(a) != set(b): erros.append(f"{cam}: chaves {sorted(set(a) ^ set(b))[:5]}")
            for k in set(a) & set(b): cmp(a[k], b[k], f"{cam}/{k}")
        elif isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b): erros.append(f"{cam}: tamanho {len(a)} ≠ {len(b)}")
            for i, (x, y) in enumerate(zip(a, b)): cmp(x, y, f"{cam}[{i}]")
        elif isinstance(a, float) or isinstance(b, float):
            if a is None or b is None or abs(a - b) > 1e-6 * max(1.0, abs(a), abs(b)): erros.append(f"{cam}: {a} ≠ {b}")
        elif a != b and not cam.endswith("codigo/cenarios.py"):
            erros.append(f"{cam}: {a!r} ≠ {b!r}")
    cmp(novo, pub, "")
    for e in erros[:30]:
        print("ERRO:", e)
    if erros:
        sys.exit(f"BLOQUEADO: produto de cenários diverge da regeneração ({len(erros)} diferenças)")
    print(f"CENÁRIOS OK: {len(pub['metricas'])} métricas regeneradas e idênticas ao produto publicado")


if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore", category=UserWarning)
    args = [a for a in sys.argv[1:] if a != "--check"]
    (verificar if "--check" in sys.argv else main)(*args)
