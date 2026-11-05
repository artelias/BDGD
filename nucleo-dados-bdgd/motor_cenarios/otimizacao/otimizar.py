"""Otimização EXPERIMENTAL dos modelos de cenários: R² fora da amostra, seleção de variáveis, ajuste dos candidatos próximos e
nova escolha dos cenários por distribuidora. Protocolo (registrado antes da execução): PROTOCOLO_OTIMIZACAO.md.

    python motor_cenarios/otimizacao/otimizar.py output-historico/contrato-integracao motor_cenarios/entrada motor_cenarios/entrada \
        web/public/data/previsoes/cenarios-motor.json motor_cenarios/otimizacao/saida

Não altera o produto publicado nem o gerador: reusa o Motor de cenarios.py e grava só em <saida>. Resultado experimental, não homologado."""
import csv
import hashlib
import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
import cenarios as C  # noqa: E402

PROTOCOLO = dict(versao="otimizacao-1", origem_selecao=2023, origem_final=2024, disponibilidade_min=0.5, desvio_min=1e-9, corr_max=0.95,
                 perm_repeticoes=5, semente=42, max_subconjuntos=8, parada_sem_melhora=2, melhora_rel=0.05, melhora_abs=0.0005,
                 r2_tolerancia=0.02, r2_min_pontos=5, tolerancia_cenario=C.TOLERANCIA_ERRO, razao_plausivel=list(C.RAZAO_PLAUSIVEL),
                 diferenca_minima_ano=C.DIFERENCA_MINIMA_PP / 100, min_transicoes_condicional=2, percentis_condicional=[1, 99])
GRADES = {"ridge": [{"alpha": a} for a in (0.1, 1.0, 10.0)],
          "knn": [{"k": k} for k in (5, 9, 15)],
          "rf": [{"min_samples_leaf": l, "max_features": f} for l in (3, 5, 10) for f in (0.3, 0.5, 1.0)],
          "hgb": [{"max_depth": d, "learning_rate": r} for d in (2, 3) for r in (0.05, 0.1)]}
# configuração original de cada modelo de painel do produto (cenarios.py), para comparação nos mesmos pontos
ORIGINAIS = {"ridge_painel": ("ridge", C.FEAT_INT, {"alpha": 1.0}), "ridge_painel_ext": ("ridge", C.FEAT_INT + C.FEAT_EXT, {"alpha": 1.0}),
             "knn_analogos": ("knn", C.FEAT_INT, {"k": 9}), "random_forest_painel": ("rf", C.FEAT_INT, {"min_samples_leaf": 5, "max_features": 0.5}),
             "hgb_painel": ("hgb", C.FEAT_INT, {"max_depth": 3, "learning_rate": 0.05})}
REFERENCIA_ALGO = {"ridge": "ridge_painel", "knn": "knn_analogos", "rf": "random_forest_painel", "hgb": "hgb_painel"}
NOME_ALGO = {"ridge": "Ridge em painel", "knn": "KNN (mediana dos vizinhos)", "rf": "Random Forest em painel", "hgb": "HistGradientBoosting em painel"}
EXTRAS = {"int_ln_trafo_dist": ("trafo_dist", "quantidade"), "int_ln_alimentadores": ("alimentadores", "quantidade"),
          "int_ln_subestacoes": ("subestacoes", "quantidade"), "int_ln_km_at": ("rede_at", "extensao_km")}
CANDIDATAS = C.FEAT_INT + C.FEAT_EXT + list(EXTRAS) + ["lag_g_proprio", "lag_g_uc"]
NAO_APLICAVEIS = {"municipio": "painel por distribuidora: o município entra só nas externas ponderadas por UC",
                  "conjunto": "painel por distribuidora: não há série por conjunto no contrato nacional",
                  "potencia_instalada": "potência via EQ→UN é experimental (não homologada); não usada como explicativa"}
SO = [x for x in (__import__("os").environ.get("OTIM_SO") or "").split(",") if x]     # depuração: só estas métricas (conceito/metrica)
UNIVARIADOS = ("persistencia", "deriva", "tendencia_ols", "crescimento_geometrico")
BASELINES = ("persistencia", "deriva", "crescimento_geometrico")


# ------------------------------------------------------------------ variáveis
class MotorX(C.Motor):
    """Motor do produto com as variáveis extras derivadas de séries do próprio contrato (estoques de outros ativos e defasagens)."""
    k = None

    def obs(self, k, dist, a):
        e = self.series.get(k, {}).get(dist, {}).get(a)
        return e[1] if e and e[0] == "observado" and (e[1] or 0) > 0 else None

    def feats(self, dist, ano, y, uc_key=("consumidores", "quantidade")):
        f = super().feats(dist, ano, y, uc_key)
        for nome, k in EXTRAS.items():
            v = self.obs(k, dist, ano)
            f[nome] = math.log(v) if v else None
        e = self.series.get(self.k, {}).get(dist, {}).get(ano)
        y0 = self.obs(self.k, dist, ano - 1)
        f["lag_g_proprio"] = math.log(y / y0) if y0 and y > 0 and e and not e[2] else None
        u1, u0 = self.obs(uc_key, dist, ano), self.obs(uc_key, dist, ano - 1)
        eu = self.series.get(uc_key, {}).get(dist, {}).get(ano)
        f["lag_g_uc"] = math.log(u1 / u0) if u1 and u0 and eu and not eu[2] else None
        return f


def ajustar(algo, hp, X, g):
    """Mesmo pré-processamento de cenarios.treinar_painel (winsorização do alvo no treino, imputação pela mediana, padronização)."""
    from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import Ridge
    from sklearn.neighbors import KNeighborsRegressor
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    lo, hi = np.quantile(g, [0.05, 0.95])
    g = np.clip(g, lo, hi)
    est = {"ridge": lambda: Ridge(alpha=hp["alpha"]),
           "knn": lambda: KNeighborsRegressor(n_neighbors=min(hp["k"], len(g))),
           "rf": lambda: RandomForestRegressor(n_estimators=300, min_samples_leaf=hp["min_samples_leaf"], max_features=hp["max_features"], random_state=42, n_jobs=1),
           "hgb": lambda: HistGradientBoostingRegressor(max_iter=150, learning_rate=hp["learning_rate"], max_depth=hp["max_depth"], min_samples_leaf=10, random_state=42)}[algo]()
    m = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), est)
    if algo == "knn":
        class Mediana:
            def __init__(s, pipe): s.pipe = pipe
            def fit(s, X, y): s.pipe.fit(X, y); s.y = np.asarray(y); return s
            def predict(s, X): return np.median(s.y[s.pipe[-1].kneighbors(s.pipe[:-1].transform(X), return_distance=False)], axis=1)
        m = Mediana(m)
    m.fit(np.asarray(X, float), g)
    return m


# ------------------------------------------------------------------ pontos e métricas
def pontos(motor, k, origem, h=1):
    """Pontos de avaliação: y_{o−1}, y_o e y_{o+h} observados, positivos e comparáveis (sem ruptura em o..o+h)."""
    out = []
    for d, anos in motor.series[k].items():
        anos_n = [origem - 1, origem] + [origem + i for i in range(1, h + 1)]
        es = [anos.get(a) for a in anos_n]
        if any(not e or e[0] != "observado" or not (e[1] or 0) > 0 for e in es) or any(e[2] for e in es[1:]):
            continue
        out.append((d, es[0][1], es[1][1], es[-1][1]))
    return out


def r2(y, yh, minimo):
    y, yh = np.asarray(y, float), np.asarray(yh, float)
    if len(y) < minimo:
        return None
    sst = float(np.sum((y - y.mean()) ** 2))
    return None if sst <= 0 else 1 - float(np.sum((y - yh) ** 2)) / sst


def metricas(pts, yhat, discreta):
    """pts: [(dist, y_{o−1}, y_o, y_alvo)]; yhat: previsões de y_alvo. R² não definido (None) com poucos pontos ou SST=0."""
    y = np.array([p[3] for p in pts], float); y0 = np.array([p[2] for p in pts], float); yh = np.array(yhat, float)
    e = yh - y
    out = {"n": len(y), "wape": float(np.abs(e).sum() / np.abs(y).sum()), "mae": float(np.abs(e).mean()), "rmse": float(np.sqrt((e ** 2).mean())),
           "vies": float(e.sum() / y.sum()),
           "r2_estoque": r2(y, yh, PROTOCOLO["r2_min_pontos"]), "r2_variacao": r2(y - y0, yh - y0, PROTOCOLO["r2_min_pontos"]),
           "r2_crescimento": r2(np.log(y / y0), np.log(np.maximum(yh, 1e-9) / y0), PROTOCOLO["r2_min_pontos"])}
    if discreta:
        ef = np.floor(yh + 0.5) - y
        out["wape_fisico"] = float(np.abs(ef).sum() / np.abs(y).sum())
    return out


def baseline(nome, y_1, y0, h):
    if nome == "persistencia": return y0
    if nome == "deriva": return y0 + h * (y0 - y_1)
    return y0 * (y0 / y_1) ** h


# ------------------------------------------------------------------ busca
class Avaliador:
    def __init__(self, motor, k, discreta, cache):
        self.motor, self.k, self.disc, self.cache = motor, k, discreta, cache
        self.tentativas = []
        self.pts = {o: pontos(motor, k, o) for o in (PROTOCOLO["origem_selecao"], PROTOCOLO["origem_final"])}
        self.pts_h2 = pontos(motor, k, PROTOCOLO["origem_selecao"], 2)

    def chave(self, algo, nomes, hp, origem, etapa):
        return hashlib.sha256(json.dumps([PROTOCOLO["versao"], self.k, algo, nomes, hp, origem, etapa], sort_keys=True).encode()).hexdigest()[:20]

    def treinar(self, algo, nomes, hp, origem):
        self.motor.k = self.k
        X, g = self.motor.pares_treino(self.k, origem, nomes)
        if len(g) < C.MIN_SERIES_PAINEL:
            return None, len(g)
        return ajustar(algo, hp, X, g), len(g)

    def avaliar(self, algo, nomes, hp, origem, etapa, h=1, retornar_modelo=False):
        ck = self.chave(algo, nomes, hp, origem, f"{etapa}/h{h}")
        if ck in self.cache and not retornar_modelo:
            return self.cache[ck]
        t0 = time.time()
        mod, n_treino = self.treinar(algo, nomes, hp, origem)
        pts = self.pts_h2 if h == 2 else self.pts[origem]
        if mod is None or not pts:
            r = {"erro": f"TREINO_INSUFICIENTE ({n_treino} pares)" if mod is None else "SEM_PONTOS"}
        else:
            self.motor.k = self.k
            X = np.asarray([C.vetor(self.motor.feats(d, origem, y0), nomes) for d, _, y0, _ in pts], float)
            gh = mod.predict(X)
            yh = [y0 * math.exp(h * float(gg)) for (_, _, y0, _), gg in zip(pts, gh)]
            r = metricas(pts, yh, self.disc)
            r["pares_treino"] = n_treino
            if etapa in ("F", "H2"):            # erros ponto a ponto da avaliação (bootstrap por grupo no parecer científico)
                r["pontos"] = [[d, y0, y, round(v, 6)] for (d, _, y0, y), v in zip(pts, yh)]
        r["segundos"] = round(time.time() - t0, 3)
        self.cache[ck] = r
        self.tentativas.append({"conceito": self.k[0], "metrica": self.k[1], "algoritmo": algo, "variaveis": "|".join(nomes), "hiper": json.dumps(hp, sort_keys=True),
                                "origem": origem, "etapa": etapa, "horizonte": h, "wape": r.get("wape"), "erro": r.get("erro", ""), "segundos": r["segundos"]})
        return (r, mod) if retornar_modelo else r

    def baselines(self, origem, h=1):
        pts = self.pts_h2 if h == 2 else self.pts[origem]
        out = {}
        for b in BASELINES if pts else ():
            yh = [baseline(b, y_1, y0, h) for _, y_1, y0, _ in pts]
            out[b] = {**metricas(pts, yh, self.disc), "pontos": [[d, y0, y, round(v, 6)] for (d, _, y0, y), v in zip(pts, yh)]}
        return out

    def importancia(self, algo, nomes, hp):
        """Permutação na validação S: aumento médio do WAPE ao embaralhar cada variável (5 repetições, semente fixa)."""
        o = PROTOCOLO["origem_selecao"]
        mod, _ = self.treinar(algo, nomes, hp, o)
        pts = self.pts[o]
        if mod is None or not pts:
            return {n: None for n in nomes}
        self.motor.k = self.k
        X = np.asarray([C.vetor(self.motor.feats(d, o, y0), nomes) for d, _, y0, _ in pts], float)
        y = np.array([p[3] for p in pts]); y0 = np.array([p[2] for p in pts])
        w = lambda Z: float(np.abs(y0 * np.exp(mod.predict(Z)) - y).sum() / y.sum())
        base = w(X)
        rng = np.random.default_rng(PROTOCOLO["semente"])
        imp = {}
        for j, n in enumerate(nomes):
            d = []
            for _ in range(PROTOCOLO["perm_repeticoes"]):
                Z = X.copy(); Z[:, j] = rng.permutation(Z[:, j]); d.append(w(Z) - base)
            imp[n] = float(np.mean(d))
        return imp


def filtrar_variaveis(motor, k):
    """Disponibilidade temporal, constância e redundância, só com os pares de treino da etapa S."""
    motor.k = k
    X, _ = motor.pares_treino(k, PROTOCOLO["origem_selecao"], CANDIDATAS)
    X = np.asarray(X, float)
    status = {}
    for j, n in enumerate(CANDIDATAS):
        col = X[:, j] if len(X) else np.array([])
        disp = float(np.mean(~np.isnan(col))) if len(col) else 0.0
        if disp < PROTOCOLO["disponibilidade_min"]:
            status[n] = ("DESCARTADA", f"INDISPONIVEL_NA_ORIGEM (disponível em {disp:.0%} dos pares de treino até 2023)")
        elif np.nanstd(col) < PROTOCOLO["desvio_min"]:
            status[n] = ("DESCARTADA", "CONSTANTE_NO_TREINO")
        else:
            status[n] = ("CANDIDATA", f"disponível em {disp:.0%}")
    vivas = [n for n in CANDIDATAS if status[n][0] == "CANDIDATA"]
    for i, a in enumerate(vivas):
        if status[a][0] != "CANDIDATA":
            continue
        for b in vivas[i + 1:]:
            if status[b][0] != "CANDIDATA":
                continue
            ca, cb = X[:, CANDIDATAS.index(a)], X[:, CANDIDATAS.index(b)]
            ok = ~np.isnan(ca) & ~np.isnan(cb)
            if ok.sum() >= 5 and np.std(ca[ok]) > 0 and np.std(cb[ok]) > 0:
                r = float(np.corrcoef(ca[ok], cb[ok])[0, 1])
                if abs(r) > PROTOCOLO["corr_max"]:
                    status[b] = ("DESCARTADA", f"REDUNDANTE_COM_{a} (r={r:.3f})")
    return [n for n in CANDIDATAS if status[n][0] == "CANDIDATA"], status


def buscar(av, algo, vivas):
    """Seleção progressiva por importância (até 8 prefixos, parada após 2 sem melhora) e depois a grade de hiperparâmetros, tudo na etapa S."""
    o = PROTOCOLO["origem_selecao"]
    hp0 = ORIGINAIS[REFERENCIA_ALGO[algo]][2]
    if not vivas:
        return None, {}
    imp = av.importancia(algo, vivas, hp0)
    ordem = sorted(vivas, key=lambda n: -(imp[n] if imp[n] is not None else -9))
    melhor, sem = None, 0
    for i in range(1, min(PROTOCOLO["max_subconjuntos"], len(ordem)) + 1):
        r = av.avaliar(algo, ordem[:i], hp0, o, "S")
        if "erro" in r:
            break
        if melhor is None or r["wape"] < melhor[1]["wape"] - 1e-12:
            melhor, sem = (ordem[:i], r), 0
        else:
            sem += 1
            if sem >= PROTOCOLO["parada_sem_melhora"]:
                break
    if melhor is None:
        return None, imp
    sub, best = melhor[0], (hp0, melhor[1])
    for hp in GRADES[algo]:
        r = av.avaliar(algo, sub, hp, o, "S")
        if "erro" not in r and r["wape"] < best[1]["wape"] - 1e-12:
            best = (hp, r)
    return {"algo": algo, "variaveis": sub, "hiper": best[0], "S": best[1]}, imp


def melhora(otim_f, orig_f, base_f):
    """Critério fixado no protocolo, só com a etapa F."""
    if "erro" in otim_f or "erro" in orig_f:
        return "SEM_AVALIACAO_FINAL"
    w1, w0 = otim_f["wape"], orig_f["wape"]
    melhor_base = min((b["wape"] for b in base_f.values()), default=None)
    r1, r0 = otim_f.get("r2_crescimento"), orig_f.get("r2_crescimento")
    r2_ok = (r1 is None and r0 is None) or (r1 is not None and r0 is not None and r1 >= r0 - PROTOCOLO["r2_tolerancia"]) or (r1 is not None and r0 is None)
    if w1 <= (1 - PROTOCOLO["melhora_rel"]) * w0 and w0 - w1 >= PROTOCOLO["melhora_abs"] and r2_ok and (melhor_base is None or w1 <= melhor_base):
        return "MELHOROU_FORA_DA_AMOSTRA"
    if w1 > w0 + 1e-12:
        return "PIOROU_FORA_DA_AMOSTRA"
    return "SEM_GANHO_SIGNIFICATIVO"


# ------------------------------------------------------------------ projeção e cenários
def projetar(motor, k, cfg, segs):
    """Trajetória 2026–2030 a partir de 2025 (treino até 2025, como o produto) para as séries com ≥ 3 anos contíguos."""
    alvos = {d: s for d, s in segs.items() if len(s) >= 3}
    if cfg["tipo"] == "univariado":
        return {d: [C.univariado(cfg["id"], s, h) for h in range(1, 6)] for d, s in alvos.items()}
    motor.k = k
    X, g = motor.pares_treino(k, C.BASE, cfg["variaveis"])
    if len(g) < C.MIN_SERIES_PAINEL:
        return {}
    mod = ajustar(cfg["algo"], cfg["hiper"], X, g)
    ds = list(alvos)
    gp = mod.predict(np.asarray([C.vetor(motor.feats(d, C.BASE, alvos[d][-1][1]), cfg["variaveis"]) for d in ds], float))
    return {d: [alvos[d][-1][1] * math.exp(h * float(gg)) for h in range(1, 6)] for d, gg in zip(ds, gp)}


def coerente(traj, mod, y25, lado):
    if not traj or any(v < 0 or not math.isfinite(v) for v in traj):
        return False
    r = traj[-1] / y25 if y25 > 0 else None
    if r is None or not (PROTOCOLO["razao_plausivel"][0] <= r <= PROTOCOLO["razao_plausivel"][1]):
        return False
    if lado == "conservador" and any(a > b for a, b in zip(traj, mod)): return False
    if lado == "agressivo" and any(a < b for a, b in zip(traj, mod)): return False
    gc, gm = math.log(traj[-1] / y25) / 5, math.log(mod[-1] / y25) / 5
    return (gm - gc if lado == "conservador" else gc - gm) >= PROTOCOLO["diferenca_minima_ano"]


def run(contrato, internas, raw, publicado, saida):
    saida = Path(saida); saida.mkdir(parents=True, exist_ok=True)
    cache_p = saida / "cache.json"
    cache = json.loads(cache_p.read_text(encoding="utf-8")) if cache_p.exists() else {}
    pub = json.loads(Path(publicado).read_text(encoding="utf-8"))
    pubm = {(m["conceito"], m["metrica"]): m for m in pub["metricas"]}
    series, empresas, unidades = C.carregar_contrato(contrato)
    pot, _ = C.carregar_potencia(internas, series)
    for kk, v in pot.items():
        series[kk] = v; unidades[kk] = "kVA"
    motor = MotorX(series, C.internas_por_dist(series, internas), C.externas_por_dist(raw, internas)[0])
    cat = json.load(open(Path(contrato).parents[1] / "etl/bdgd2025/config/conceitos_2025.json", encoding="utf-8"))
    familia = {a["id"]: a.get("familia", "") for a in cat["ativos"]}
    t_ini = time.time()
    modelos_rows, var_rows, tent_rows, matriz, resumo_m, pontos_rows = [], [], [], [], [], []
    reproducao = []
    for k in sorted(series):
        if k not in pubm or not pubm[k]["series"] or (SO and f"{k[0]}/{k[1]}" not in SO):
            continue
        t0 = time.time()
        conc, metr = k
        disc = C.mc.nature_of(unidades.get(k, "")) == "discrete_count"
        av = Avaliador(motor, k, disc, cache)
        oS, oF = PROTOCOLO["origem_selecao"], PROTOCOLO["origem_final"]
        bS, bF, bH2 = av.baselines(oS), av.baselines(oF), av.baselines(oS, 2)
        vivas, status = filtrar_variaveis(motor, k)
        cands = {}                       # id -> {tipo, ..., S, F, H2}
        for b in UNIVARIADOS:
            if b in BASELINES:
                cands[b] = {"tipo": "univariado", "id": b, "algo": b, "variaveis": [], "hiper": {}, "S": bS.get(b, {"erro": "SEM_PONTOS"}), "F": bF.get(b, {"erro": "SEM_PONTOS"}), "H2": bH2.get(b, {})}
        for oid, (algo, nomes, hp) in ORIGINAIS.items():
            cands[oid] = {"tipo": "painel", "id": oid, "algo": algo, "variaveis": list(nomes), "hiper": hp, "origem": "original",
                          "S": av.avaliar(algo, list(nomes), hp, oS, "S"), "F": av.avaliar(algo, list(nomes), hp, oF, "F"), "H2": av.avaliar(algo, list(nomes), hp, oS, "H2", 2)}
        imps = {}
        for algo in GRADES:
            res, imp = buscar(av, algo, vivas)
            imps[algo] = imp
            if not res:
                continue
            oid = f"{REFERENCIA_ALGO[algo]}_otim"
            F = av.avaliar(algo, res["variaveis"], res["hiper"], oF, "F")
            cands[oid] = {"tipo": "painel", "id": oid, "algo": algo, "variaveis": res["variaveis"], "hiper": res["hiper"], "origem": "otimizado",
                          "S": res["S"], "F": F, "H2": av.avaliar(algo, res["variaveis"], res["hiper"], oS, "H2", 2), "referencia": REFERENCIA_ALGO[algo]}
            ref = cands[REFERENCIA_ALGO[algo]]
            cands[oid]["veredito"] = melhora(F, ref["F"], bF)
            # importância na etapa F (diagnóstico pós-hoc de estabilidade; nunca usado em escolha)
            sel = [n for n, v in sorted(imp.items(), key=lambda x: -(x[1] or -9))[:3]]
            cands[oid]["top3_S"] = sel
        # reprodução: o Ridge original deste script tem de prever igual ao do produto (mesmo pré-processamento)
        motor.k = k
        Xr, gr = motor.pares_treino(k, oF, C.FEAT_INT)
        if len(gr) >= C.MIN_SERIES_PAINEL:
            m1, _ = C.treinar_painel("ridge_painel", Xr, gr); m2 = ajustar("ridge", {"alpha": 1.0}, Xr, gr)
            reproducao.append(float(np.max(np.abs(m1.predict(np.asarray(Xr, float)) - m2.predict(np.asarray(Xr, float))))))
        for n in CANDIDATAS:
            var_rows.append({"conceito": conc, "metrica": metr, "variavel": n, "status_filtro": status[n][0], "motivo_filtro": status[n][1],
                             **{f"importancia_S_{a}": (None if imps.get(a, {}).get(n) is None else round(imps[a][n], 6)) for a in GRADES},
                             **{f"selecionada_{a}": n in cands.get(f"{REFERENCIA_ALGO[a]}_otim", {}).get("variaveis", []) for a in GRADES}})
        for n, mot in NAO_APLICAVEIS.items():
            var_rows.append({"conceito": conc, "metrica": metr, "variavel": n, "status_filtro": "NAO_APLICAVEL", "motivo_filtro": mot})
        # ---------- cenários por distribuidora
        m_pub = pubm[k]
        mod_pub_id = m_pub["cenarios"]["moderado"]
        segs = {d: C.segmento(anos) for d, anos in series[k].items()}
        # Protocolo 6.1: o Moderado publicado só é substituído por um otimizado que melhora realmente e tem WAPE_S e WAPE_F menores
        sub = substituto(cands, mod_pub_id)
        mod_id = sub["id"] if sub else mod_pub_id
        traj_sub = projetar(motor, k, sub, segs) if sub else {}
        mod_S = cands.get(mod_id, {}).get("S", {}).get("wape") if mod_id else None
        competitivos = [c for c in cands.values() if c["id"] != mod_id and "wape" in c["S"] and mod_S is not None
                        and c["S"]["wape"] <= PROTOCOLO["tolerancia_cenario"] * mod_S]
        trajs = {c["id"]: projetar(motor, k, c, segs) for c in competitivos}
        # P01–P99 das transições comparáveis da métrica (todas as DIST), para os cenários condicionais
        gs = [math.log(b[1] / a[1]) for anos in series[k].values() for t in (2023, 2024, 2025)
              for a, b in [(anos.get(t - 1), anos.get(t))] if a and b and a[0] == b[0] == "observado" and (a[1] or 0) > 0 and (b[1] or 0) > 0 and not b[2]]
        p_lo, p_hi = (np.percentile(gs, PROTOCOLO["percentis_condicional"]) if len(gs) >= 20 else (None, None))
        tipos = Counter()
        for d, s in sorted(m_pub["series"].items(), key=lambda x: int(x[0])):
            mod = s.get("moderado")
            mod_pub_vals = mod
            y25 = s["hist"][-1][1] if s["hist"] and s["hist"][-1][0] == C.BASE else None
            mod_tipo, mod_motivo, mod_c = "MODERADO_PUBLICADO", "Moderado do produto preservado: nenhum otimizado o supera nas etapas S e F", cands.get(mod_pub_id, {})
            if sub and mod and y25:
                t = traj_sub.get(d)
                r = t[-1] / y25 if t else None
                if t and all(v >= 0 for v in t) and PROTOCOLO["razao_plausivel"][0] <= r <= PROTOCOLO["razao_plausivel"][1]:
                    mod = [int(math.floor(v + 0.5)) for v in t] if disc else [round(v, 3) for v in t]
                    mod_tipo, mod_c = "MODERADO_SUBSTITUIDO_POR_OTIMIZADO", sub
                    mod_motivo = f"{sub['id']} melhora fora da amostra e tem WAPE_S e WAPE_F menores que {mod_pub_id} (protocolo 6.1)"
                else:
                    mod_motivo = f"substituto {sub['id']} implausível nesta DIST; Moderado publicado mantido"
            linha_base = {"DIST": d, "empresa": empresas.get(d, ""), "ativo": conc, "familia": familia.get(conc, ""), "metrica": metr}
            if not mod or not y25:
                for cen in ("conservador", "moderado", "agressivo"):
                    matriz.append({**linha_base, "cenario": cen, "tipo_escolha": "SEM_MODERADO", "modelo_anterior": m_pub["cenarios"][cen] if s.get(cen) else "nao_publicado",
                                   "estado_plausibilidade": "SEM_PREVISAO", "estado_homologacao": "experimental_nao_homologado",
                                   "motivo": (s.get("motivos") or {}).get("moderado") or "sem Moderado publicado nesta distribuidora"})
                tipos["SEM_MODERADO"] += 1
                continue
            pm = cands.get(mod_pub_id, {})
            ganho = (pm["F"]["wape"] - mod_c["F"]["wape"]) if "wape" in pm.get("F", {}) and "wape" in mod_c.get("F", {}) else None
            matriz.append({**linha_base, "cenario": "moderado", "tipo_escolha": mod_tipo, **descr(mod_c), "valor_2030": mod[-1], "valor_2030_anterior": mod_pub_vals[-1],
                           "modelo_anterior": mod_pub_id, "ganho_wape_F": ganho, "estado_plausibilidade": "ACEITO", "estado_homologacao": "experimental_nao_homologado",
                           "motivo": mod_motivo})
            gh = [g for t in (2023, 2024, 2025) for a, b in [(series[k][d].get(t - 1), series[k][d].get(t))]
                  if a and b and a[0] == b[0] == "observado" and (a[1] or 0) > 0 and (b[1] or 0) > 0 and not b[2] for g in [math.log(b[1] / a[1])]]
            for lado in ("conservador", "agressivo"):
                ok = [c for c in competitivos if coerente(trajs[c["id"]].get(d), mod, y25, lado)]
                ant_id = m_pub["cenarios"][lado] if s.get(lado) else "nao_publicado"
                ant_2030 = s[lado][-1] if s.get(lado) else None
                if ok:
                    c = min(ok, key=lambda x: x["S"]["wape"])
                    v = trajs[c["id"]][d]
                    tipo, desc, motivo = "MODELO_INDEPENDENTE", descr(c), f"menor WAPE_S entre {len(ok)} candidato(s) competitivo(s) coerente(s) nesta DIST"
                else:
                    gm = math.log(mod[-1] / y25) / 5
                    alvo = (min(gh) if lado == "conservador" else max(gh)) if len(gh) >= PROTOCOLO["min_transicoes_condicional"] else None
                    v = [y25 * math.exp(h * alvo) for h in range(1, 6)] if alvo is not None else None
                    dentro = alvo is not None and p_lo is not None and p_lo <= alvo <= p_hi
                    if v and dentro and coerente(v, mod, y25, lado):
                        tipo, desc = "CONDICIONAL_DO_MODERADO", {"algoritmo": f"condicional de {mod_id}", "variaveis": "", "hiperparametros": json.dumps({"crescimento_log_anual": round(alvo, 6)}),
                                                                "mecanismo": f"ŷ(2025+h) = y(2025)·exp(h·g), g = {'mínimo' if lado == 'conservador' else 'máximo'} crescimento log de uma transição comparável da série ({len(gh)} transições)"}
                        motivo = f"nenhum modelo competitivo coerente; g={alvo:.4f} dentro de P01–P99 da métrica [{p_lo:.4f}; {p_hi:.4f}]"
                    else:
                        tipo, desc, v = "SEM_EVIDENCIA_COINCIDENTE", {"algoritmo": mod_id}, list(mod)
                        motivo = ("histórico com menos de 2 transições comparáveis" if alvo is None else "crescimento extremo da série fora do P01–P99 da métrica" if not dentro
                                  else "crescimento histórico não mais extremo que o Moderado de forma coerente") + "; cenário coincide com o Moderado e não é publicável como distinto"
                if disc and v:
                    v = [int(math.floor(x + 0.5)) for x in v]
                tipos[tipo] += 1
                fa = cands.get(ant_id, {}).get("F", {}).get("wape"); fn = desc.get("wape_F")
                matriz.append({**linha_base, "cenario": lado, "tipo_escolha": tipo, **desc, "valor_2030": v[-1] if v else None, "valor_2030_anterior": ant_2030, "modelo_anterior": ant_id,
                               "ganho_wape_F": None if fa is None or fn is None else fa - fn,
                               "estado_plausibilidade": "ACEITO" if tipo != "SEM_EVIDENCIA_COINCIDENTE" else "SEM_EVIDENCIA", "estado_homologacao": "experimental_nao_homologado", "motivo": motivo})
        # ---------- linhas por modelo
        for c in cands.values():
            S, F, H2 = c["S"], c["F"], c["H2"]
            mb = min(bF.items(), key=lambda x: x[1]["wape"]) if bF else (None, {})
            modelos_rows.append({"conceito": conc, "metrica": metr, "familia": familia.get(conc, ""), "modelo": c["id"], "origem": c.get("origem", "baseline"), "algoritmo": c["algo"],
                                 "variaveis": "|".join(c["variaveis"]), "hiperparametros": json.dumps(c["hiper"], sort_keys=True),
                                 **{f"{e}_{x}": (None if et.get(x) is None else round(et[x], 6)) for e, et in (("S", S), ("F", F), ("H2", H2))
                                    for x in ("wape", "mae", "rmse", "vies", "r2_estoque", "r2_variacao", "r2_crescimento", "wape_fisico")},
                                 "n_S": S.get("n"), "n_F": F.get("n"), "estabilidade": None if "wape" not in S or "wape" not in F else round(abs(F["wape"] - S["wape"]), 6),
                                 "melhor_baseline_F": mb[0], "wape_melhor_baseline_F": None if mb[0] is None else round(mb[1]["wape"], 6),
                                 "referencia": c.get("referencia", ""), "veredito": c.get("veredito", ""), "top3_importancia_S": "|".join(c.get("top3_S", []))})
        for c in cands.values():
            for etapa in ("F", "H2"):
                for d, y0, y, yh in c[etapa].get("pontos", []):
                    pontos_rows.append({"conceito": conc, "metrica": metr, "modelo": c["id"], "origem": c.get("origem", "baseline"), "etapa": etapa,
                                        "DIST": d, "y_origem": y0, "y_observado": y, "y_previsto": yh})
        tent_rows.extend(av.tentativas)
        resumo_m.append({"conceito": conc, "metrica": metr, "segundos": round(time.time() - t0, 1), "tentativas": len(av.tentativas), "variaveis_vivas": len(vivas),
                         "tipos": dict(tipos), "estado_publicado": m_pub["estado"]})
        print(f"{conc}/{metr}: {len(av.tentativas)} tentativas novas, {time.time() - t0:.1f}s, {dict(tipos)}", flush=True)
    cache_p.write_text(json.dumps(cache), encoding="utf-8")

    def wcsv(nome, rows):
        campos = list(dict.fromkeys(c for r in rows for c in r))
        with open(saida / nome, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=campos, lineterminator="\n"); w.writeheader(); w.writerows(rows)
    wcsv("MATRIZ_MODELOS_OTIMIZADOS.csv", matriz)
    wcsv("MODELOS_AVALIADOS.csv", modelos_rows)
    wcsv("VARIAVEIS_SELECAO.csv", var_rows)
    wcsv("PONTOS_AVALIACAO.csv", pontos_rows)
    if tent_rows:
        wcsv("BUSCA_TENTATIVAS.csv", tent_rows)
    res = resumo(pub, matriz, modelos_rows, var_rows, resumo_m)
    if not tent_rows and (saida / "BUSCA_TENTATIVAS.csv").exists():      # reexecução só com cache: custo é o da execução que fez os ajustes
        res["tentativas_total"] = sum(1 for _ in open(saida / "BUSCA_TENTATIVAS.csv", encoding="utf-8")) - 1
        res["tentativas_origem"] = "BUSCA_TENTATIVAS.csv da execução que fez os ajustes (esta reexecução usou só o cache)"
    res["reproducao_ridge_original_max_dif"] = max(reproducao) if reproducao else None
    res["protocolo"] = PROTOCOLO
    res["segundos_total"] = round(time.time() - t_ini, 1)
    (saida / "RESUMO_OTIMIZACAO.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res


def descr(c):
    if not c:
        return {}
    S, F = c.get("S", {}), c.get("F", {})
    mec = C.MODELOS.get(c.get("referencia") or c["id"], {}).get("formula", "") if c.get("tipo") == "painel" else C.MODELOS.get(c["id"], {}).get("formula", "")
    return {"algoritmo": c["id"], "variaveis": "|".join(c.get("variaveis", [])), "hiperparametros": json.dumps(c.get("hiper", {}), sort_keys=True),
            "mecanismo": mec + (" (variáveis e hiperparâmetros da busca)" if c.get("origem") == "otimizado" else ""),
            "r2_crescimento_F": F.get("r2_crescimento"), "r2_variacao_F": F.get("r2_variacao"), "wape_S": S.get("wape"), "wape_F": F.get("wape"), "mae_F": F.get("mae"),
            "rmse_F": F.get("rmse"), "vies_F": F.get("vies"), "horizonte_validado": "h=1 (origem 2024 → 2025); h=2 só diagnóstico",
            "veredito_otimizacao": c.get("veredito", "")}


def substituto(cands, mod_id):
    """Otimizado que melhora realmente (critério 5) e tem WAPE_S e WAPE_F menores que o Moderado publicado; entre vários, o de menor WAPE_S."""
    m = cands.get(mod_id)
    if not m or "wape" not in m.get("S", {}) or "wape" not in m.get("F", {}):
        return None
    ok = [c for c in cands.values() if c.get("veredito") == "MELHOROU_FORA_DA_AMOSTRA" and c["S"]["wape"] < m["S"]["wape"] and c["F"]["wape"] < m["F"]["wape"]]
    return min(ok, key=lambda c: c["S"]["wape"]) if ok else None


def resumo(pub, matriz, modelos, variaveis, resumo_m):
    antes = Counter(m["estado"] for m in pub["metricas"] if m["series"])
    subs = Counter()
    por_m = defaultdict(lambda: defaultdict(Counter))
    for r in matriz:
        if r["cenario"] != "moderado":
            por_m[(r["ativo"], r["metrica"])][r["DIST"]][r["tipo_escolha"]] += 1
        elif r["tipo_escolha"] == "MODERADO_SUBSTITUIDO_POR_OTIMIZADO":
            subs[(r["ativo"], r["metrica"])] += 1
    def completa(c):
        return sum(c[t] for t in ("MODELO_INDEPENDENTE", "CONDICIONAL_DO_MODERADO")) == 2
    serie_completa = {k: sum(1 for c in v.values() if completa(c)) for k, v in por_m.items()}
    com_mod = {k: sum(1 for c in v.values() if not c.get("SEM_MODERADO")) for k, v in por_m.items()}
    pub_completa = {(m["conceito"], m["metrica"]): sum(1 for s in m["series"].values() if s.get("conservador") and s.get("moderado") and s.get("agressivo")) for m in pub["metricas"]}
    otim = [r for r in modelos if r["origem"] == "otimizado"]
    tipos = Counter(r["tipo_escolha"] for r in matriz if r["cenario"] != "moderado")
    desc = Counter(r["variavel"] for r in variaveis if r["status_filtro"] == "DESCARTADA")
    imp_fam = defaultdict(lambda: defaultdict(list))
    for r in variaveis:
        for a in GRADES:
            v = r.get(f"importancia_S_{a}")
            if v is not None:
                imp_fam[next((m["familia"] for m in pub["metricas"] if m["conceito"] == r["conceito"]), "")][r["variavel"]].append(v)
    top_fam = {f: [n for n, _ in sorted(((n, float(np.median(v))) for n, v in d.items()), key=lambda x: -x[1])[:3]] for f, d in imp_fam.items()}
    pares = [(r, next(x for x in modelos if x["conceito"] == r["conceito"] and x["metrica"] == r["metrica"] and x["modelo"] == r["referencia"])) for r in otim]
    dw = [r["F_wape"] - o["F_wape"] for r, o in pares if r["F_wape"] is not None and o["F_wape"] is not None]
    dr = [r["F_r2_crescimento"] - o["F_r2_crescimento"] for r, o in pares if r["F_r2_crescimento"] is not None and o["F_r2_crescimento"] is not None]
    return {
        "q1_metricas_com_tres_cenarios_antes": antes.get("tres_cenarios", 0), "estados_antes": dict(antes),
        "q1b_series_com_tres_cenarios_antes": sum(pub_completa.values()),
        "q2_series_com_tres_cenarios_depois_registro_tecnico": sum(serie_completa.values()),
        "q2b_metricas_com_90pct_das_series_completas_depois": sum(1 for k in serie_completa if com_mod[k] and serie_completa[k] >= 0.9 * com_mod[k]),
        "moderado_substituido_por_otimizado": {"/".join(k): n for k, n in subs.items()},
        "q3_modelos_que_melhoraram_fora_da_amostra": sorted(f"{r['conceito']}/{r['metrica']}:{r['modelo']}" for r in otim if r["veredito"] == "MELHOROU_FORA_DA_AMOSTRA"),
        "q4_variaveis_descartadas": {"ocorrencias": sum(desc.values()), "por_variavel": dict(desc)},
        "q5_variaveis_mais_relevantes_por_familia_S": top_fam,
        "q6_cenarios_modelo_independente": tipos.get("MODELO_INDEPENDENTE", 0),
        "q7_cenarios_condicionais_do_moderado": tipos.get("CONDICIONAL_DO_MODERADO", 0),
        "q8_cenarios_sem_evidencia": tipos.get("SEM_EVIDENCIA_COINCIDENTE", 0), "cenarios_sem_moderado": tipos.get("SEM_MODERADO", 0),
        "q9_modelos_que_pioraram_fora_da_amostra": sorted(f"{r['conceito']}/{r['metrica']}:{r['modelo']}" for r in otim if r["veredito"] == "PIOROU_FORA_DA_AMOSTRA"),
        "q9b_sem_ganho_significativo": sum(1 for r in otim if r["veredito"] == "SEM_GANHO_SIGNIFICATIVO"),
        "q10_variacao_F_otimizado_menos_original": {"wape_mediana": float(np.median(dw)) if dw else None, "wape_melhorou_em": sum(1 for x in dw if x < 0), "wape_piorou_em": sum(1 for x in dw if x > 0),
                                                   "r2_crescimento_mediana": float(np.median(dr)) if dr else None, "r2_definido_em": len(dr), "pares": len(pares)},
        "por_metrica": resumo_m,
        "tentativas_total": sum(m["tentativas"] for m in resumo_m),
    }


if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    r = run(*sys.argv[1:6])
    print(json.dumps({k: v for k, v in r.items() if k not in ("por_metrica", "protocolo")}, ensure_ascii=False, indent=1))
