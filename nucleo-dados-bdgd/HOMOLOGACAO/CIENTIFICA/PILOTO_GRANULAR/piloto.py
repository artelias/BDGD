"""Piloto granular e hierárquico (protocolo: 01_PROTOCOLO.md, congelado em d988416).

    python HOMOLOGACAO/CIENTIFICA/PILOTO_GRANULAR/piloto.py entrada   # Gate 1: hashes, cobertura, exclusões, auditoria DAT_CON
    python HOMOLOGACAO/CIENTIFICA/PILOTO_GRANULAR/piloto.py selecao   # Gate 2: etapa S (2025 NÃO é carregado) + teste espacial
    python HOMOLOGACAO/CIENTIFICA/PILOTO_GRANULAR/piloto.py final     # Gate 3/4: etapa F, uma única vez, com a seleção congelada

Lê só os painéis territoriais já extraídos e o contrato nacional; nada é extraído, nada vai para o produto."""
import csv
import ctypes
import hashlib
import json
import math
import re
import sys
import time
import warnings
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]                                   # nucleo-dados-bdgd
sys.path.insert(0, str(RAIZ / "motor_cenarios"))
import cenarios as C  # noqa: E402  (modelo atual por DIST: mesmo código do produto)

PROTOCOLO_HASH = "6cfdf675cc2355b48d3f9187daa3fda49116aaeeb4d93136068cbb791733da08"
PAINEL = Path("D:/NUCLEO_BDGD_2025/motor_v2/nacional/painel")
CACHE = Path("D:/NUCLEO_BDGD_2025/piloto_granular_cache")
CONTRATO = RAIZ / "output-historico/contrato-integracao"
SUCESSAO = Path("D:/NUCLEO_BDGD_2025/output-historico/2022-2025/eventos_sucessao.csv")
INVENTARIO = Path("D:/NUCLEO_BDGD_2025/motor_v2/inventario_v2/INVENTARIO_PUBLICACOES_LOCAIS.csv")
EXTERNAS = RAIZ / "motor_cenarios/entrada/externas_ibge_municipal.csv"
ENTRADA = RAIZ / "motor_cenarios/entrada"
INDICE_V2 = RAIZ / "web/data-motor-v2/indice.json"
PRODUTO = RAIZ / "web/public/data/previsoes/cenarios-motor.json"
ANOS = (2022, 2023, 2024, 2025)
CONTINUIDADE_MIN = 0.95
SEMENTE_BOOT, REPLICAS = 20261104, 2000
ORDEM_SIMPLES = ["G-NULO", "H-NULO", "G-RIDGE", "G-HIER", "G-HGB", "G-RF", "G-KNN"]
GRADES = {"G-RIDGE": [{"alpha": a} for a in (0.1, 1.0, 10.0)], "G-HGB": [{"max_depth": d, "learning_rate": r} for d in (2, 3) for r in (0.05, 0.1)],
          "G-RF": [{"min_samples_leaf": l, "max_features": f} for l in (5, 20) for f in (0.5, 1.0)], "G-KNN": [{"k": k} for k in (15, 50)]}
PADRAO = {"G-RIDGE": {"alpha": 1.0}, "G-HGB": {"max_depth": 3, "learning_rate": 0.05}, "G-RF": {"min_samples_leaf": 5, "max_features": 0.5}, "G-KNN": {"k": 15}}
MAX_AJUSTES = 60

# ativo -> painel, conceito do contrato, métrica, natureza, níveis (hipótese primeiro), coluna de valor, modelo atual (Moderado do produto)
ATIVOS = {
    "ucbt": dict(painel="ucbt_quantidade", conceito="consumidores", metrica="quantidade", contagem=True, niveis=["MUN", "CONJ"], atual="ridge_painel"),
    "trafo_qtd": dict(painel="trafo_dist_quantidade", conceito="trafo_dist", metrica="quantidade", contagem=True, niveis=["MUN", "CONJ"], atual="knn_analogos"),
    "trafo_kva": dict(painel="trafo_dist_potencia_kva", conceito="trafo_dist", metrica="potencia_kva", contagem=False, niveis=["MUN", "CONJ"], atual="ridge_painel"),
    "rede_bt": dict(painel="rede_bt_extensao_km", conceito="rede_bt", metrica="extensao_km", contagem=False, niveis=["CONJ"], atual="ridge_painel"),
    "rede_mt": dict(painel="rede_mt_extensao_km", conceito="rede_mt", metrica="extensao_km", contagem=False, niveis=["CONJ"], atual="random_forest_painel"),
}
COMUNS = ["ln_estoque", "taxa_conexoes", "ln_kwh_cliente", "fracao_urbana", "ln_pib_pc_2021", "cresc_pop_2010_2022", "eletrificacao"]
VARIAVEIS = {"ucbt": COMUNS + ["ln_trafo_por_cliente", "ln_kva_por_cliente"],
             "trafo_qtd": COMUNS + ["ln_clientes_por_trafo", "ln_kva_por_trafo"],
             "trafo_kva": COMUNS + ["ln_kva_por_trafo", "ln_clientes_por_kva"],
             "rede_bt": COMUNS + ["ln_clientes_por_km_bt", "ln_trafo_por_km_bt", "ln_razao_mt_bt"],
             "rede_mt": COMUNS + ["ln_clientes_por_km_mt", "ln_trafo_por_km_mt", "ln_razao_bt_mt"]}
PENDENCIAS_MUN = {("5697", 2023): "RECODIFICACAO_MUN_PENDENTE_CELESC_2023", ("7019", 2023): "ANOMALIA_MUN_7019_2023"}


# ------------------------------------------------------------------ utilidades
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def pico_memoria_mb():
    """PeakWorkingSetSize do processo (Windows, K32GetProcessMemoryInfo via ctypes; sem dependência nova)."""
    from ctypes import wintypes
    class PMC(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [(n, ctypes.c_size_t) for n in (
            "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage",
            "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
    try:
        k = ctypes.WinDLL("kernel32"); k.GetCurrentProcess.restype = wintypes.HANDLE
        f = k.K32GetProcessMemoryInfo; f.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]; f.restype = wintypes.BOOL
        c = PMC(); c.cb = ctypes.sizeof(PMC)
        return round(c.PeakWorkingSetSize / 2 ** 20, 1) if f(k.GetCurrentProcess(), ctypes.byref(c), c.cb) else None
    except Exception:
        return None


def ler_csv(p):
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def escrever(p, rows):
    campos = list(dict.fromkeys(k for r in rows for k in r))
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, lineterminator="\n"); w.writeheader(); w.writerows(rows)


def verificar_protocolo():
    s = (AQUI / "01_PROTOCOLO.md").read_text(encoding="utf-8")
    bloco = re.search(r"```\n(PROTOCOLO_DECISAO = \{.*?\n\})\n```", s, re.S).group(1)
    h = hashlib.sha256(bloco.encode()).hexdigest()
    if h != PROTOCOLO_HASH:
        sys.exit(f"BLOQUEADO: critérios de decisão do protocolo divergem do congelado ({h} != {PROTOCOLO_HASH})")


def chave(k, nivel):
    if k is None:
        return "SEM_CODIGO"
    k = str(k).strip()
    if nivel == "MUN":
        return k if len(k) == 7 and k.isdigit() else "SEM_CODIGO"
    return k if k not in ("", "0", "None") else "SEM_CODIGO"


# ------------------------------------------------------------------ dados
class Dados:
    """Painéis por DIST e ano (só anos ≤ ano_max), agregados por nível; rupturas, sucessões, grupos e externas."""
    def __init__(self, ano_max):
        self.anos = [a for a in ANOS if a <= ano_max]
        self.dists = sorted(p.name for p in PAINEL.iterdir() if p.is_dir() and p.name.isdigit())
        self.uc, self.tq, self.tk, self.bt, self.mt = {}, {}, {}, {}, {}
        self.rup_painel = set()
        self.arquivos = []
        for d in self.dists:
            for painel, destino in (("ucbt_quantidade", None), ("trafo_dist_quantidade", self.tq), ("trafo_dist_potencia_kva", self.tk),
                                    ("rede_bt_extensao_km", self.bt), ("rede_mt_extensao_km", self.mt)):
                r = PAINEL / d / painel / "result.json"
                if r.exists():
                    for h in json.loads(r.read_text(encoding="utf-8")).get("history", []):
                        if h.get("rupture") and h["year"] in self.anos:
                            self.rup_painel.add((painel, d, int(h["year"])))
                for a in self.anos:
                    p = PAINEL / d / painel / str(a) / "territorial.parquet"
                    if not p.exists():
                        continue
                    self.arquivos.append(p)
                    if painel == "ucbt_quantidade":
                        # pré-agregado por MUN × CONJ (o circuito sai): [clientes, conexoes_12m, kwh, denominador de energia, clientes urbanos]
                        t = pq.read_table(p, columns=["MUN", "CONJ", "ARE_LOC", "clientes_ativos", "energia_kwh", "energia_denominador", "conexoes_12m"])
                        agg = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0, 0.0])
                        for m, c, al, cl, kwh, den, cx in zip(*(t.column(i).to_pylist() for i in range(7))):
                            v = agg[(m, c)]; cl = cl or 0
                            v[0] += cl; v[1] += cx or 0; v[2] += kwh or 0; v[3] += den or 0; v[4] += cl if al == "UB" else 0
                        self.uc[(d, a)] = [(m, c, *v) for (m, c), v in agg.items()]
                        del t
                    else:
                        t = pq.read_table(p, columns=["UNIT", "CONJ", "value"]).to_pylist()
                        destino[(d, a)] = t
        self.rup_contrato = {(r["dist"], int(r["ano"]), r["conceitoId"], r["metrica"]) for r in ler_csv(CONTRATO / "serie_fisica_nacional.csv")
                             if r["ruptura_desde_ano_anterior"] == "true" and int(r["ano"]) <= ano_max}
        self.suc = set()
        for r in ler_csv(SUCESSAO):
            ano = int((r["data_efetivacao"] or r["data_autorizacao"])[:4])
            for d in (r["dist_destino_2025"], r["dist_origem"]):
                if d:
                    self.suc |= {(d, ano), (d, ano + 1)}
        ix = json.loads(INDICE_V2.read_text(encoding="utf-8"))
        self.grupo = {str(x["dist"]): x["grupo"] or f"DIST_{x['dist']}" for x in ix["dists"]}
        self.empresa = {str(x["dist"]): x["empresa"] for x in ix["dists"]}
        self.ext = {}
        for r in ler_csv(EXTERNAS):
            e = {k: float(v) for k, v in r.items() if k != "mun" and v not in ("", None)}
            a, b, p21, pib = e.get("pop_2010"), e.get("pop_2022"), e.get("pop_2021"), e.get("pib_2021_mil_reais")
            self.ext[r["mun"]] = dict(cresc_pop_2010_2022=(b / a) ** (1 / 12) - 1 if a and b else None,
                                      ln_pib_pc_2021=math.log(pib * 1000 / p21) if pib and p21 else None, pop_2022=b)
        self._agg = {}

    # agregados por unidade -----------------------------------------
    def estoque(self, ativo, nivel, d, a):
        """{unidade: estoque} do ativo no nível (inclui SEM_CODIGO), ou None sem painel."""
        k = (ativo, nivel, d, a)
        if k in self._agg:
            return self._agg[k]
        out = None
        if ativo == "ucbt":
            t = self.uc.get((d, a))
            if t is not None:
                out = defaultdict(float)
                j = 0 if nivel == "MUN" else 1
                for x in t:
                    out[chave(x[j], nivel)] += x[2]
        else:
            fonte = {"trafo_qtd": self.tq, "trafo_kva": self.tk, "rede_bt": self.bt, "rede_mt": self.mt}[ativo]
            t = fonte.get((d, a))
            if t is not None:
                out = defaultdict(float)
                col = "UNIT" if nivel == "MUN" else "CONJ"
                for x in t:
                    out[chave(x[col], nivel)] += x["value"] or 0
        if out is not None:
            out = {u: v for u, v in out.items() if v > 0}
        self._agg[k] = out
        return out

    def total(self, ativo, d, a):
        m = self.estoque(ativo, ATIVOS[ativo]["niveis"][0], d, a)
        return sum(m.values()) if m else None

    def uc_detalhe(self, nivel, d, a):
        """{unidade: dict(clientes, conexoes, kwh, den, urb)} e pesos MUN×CONJ."""
        k = ("ucdet", nivel, d, a)
        if k in self._agg:
            return self._agg[k]
        t = self.uc.get((d, a))
        out, mc = None, None
        if t is not None:
            out = defaultdict(lambda: dict(clientes=0.0, conexoes=0.0, kwh=0.0, den=0.0, urb=0.0)); mc = defaultdict(float)
            for m, cj, cl, cx, kwh, den, urb in t:
                u = chave(m if nivel == "MUN" else cj, nivel)
                o = out[u]; o["clientes"] += cl; o["conexoes"] += cx; o["kwh"] += kwh; o["den"] += den; o["urb"] += urb
                mc[(chave(m, "MUN"), chave(cj, "CONJ"))] += cl
        self._agg[k] = (out, mc)
        return out, mc

    # variáveis -------------------------------------------------------
    def variaveis(self, ativo, nivel, d, a):
        """{unidade: {variável: valor}} medidas na fotografia `a` (origem). Nada do ano-alvo."""
        k = ("feat", ativo, nivel, d, a)
        if k in self._agg:
            return self._agg[k]
        y = self.estoque(ativo, nivel, d, a) or {}
        ucd, mc = self.uc_detalhe(nivel, d, a)
        ucd = ucd or {}
        tq = self.estoque("trafo_qtd", nivel, d, a) or {}; tk = self.estoque("trafo_kva", nivel, d, a) or {}
        bt = self.estoque("rede_bt", "CONJ", d, a) or {} if nivel == "CONJ" else {}
        mt = self.estoque("rede_mt", "CONJ", d, a) or {} if nivel == "CONJ" else {}
        # externas: no município direto; no conjunto, média ponderada pelos clientes da interseção MUN×CONJ
        peso = defaultdict(list)
        if nivel == "CONJ" and mc:
            for (m, c), w in mc.items():
                peso[c].append((m, w))
        def ext(u, campo):
            if nivel == "MUN":
                return self.ext.get(u, {}).get(campo)
            vs = [(self.ext.get(m, {}).get(campo), w) for m, w in peso.get(u, [])]
            vs = [(v, w) for v, w in vs if v is not None]
            return sum(v * w for v, w in vs) / sum(w for _, w in vs) if vs and sum(w for _, w in vs) > 0 else None
        L = lambda x: math.log(x) if x and x > 0 else None
        out = {}
        for u, v in y.items():
            if u == "SEM_CODIGO":
                continue
            c = ucd.get(u)
            cl = c["clientes"] if c else None
            pop = ext(u, "pop_2022") if nivel == "MUN" else None
            f = dict(ln_estoque=L(v), taxa_conexoes=c["conexoes"] / cl if c and cl else None,
                     ln_kwh_cliente=L(c["kwh"] / c["den"]) if c and c["den"] else None, fracao_urbana=c["urb"] / cl if c and cl else None,
                     ln_pib_pc_2021=ext(u, "ln_pib_pc_2021"), cresc_pop_2010_2022=ext(u, "cresc_pop_2010_2022"),
                     eletrificacao=(cl / pop if cl and pop else None) if nivel == "MUN" else None)
            # eletrificação só no município: a população não se particiona por conjunto (sem denominador territorial válido)
            q, kva = tq.get(u), tk.get(u)
            if ativo == "ucbt":
                f.update(ln_trafo_por_cliente=L(q / cl) if q and cl else None, ln_kva_por_cliente=L(kva / cl) if kva and cl else None)
            elif ativo == "trafo_qtd":
                f.update(ln_clientes_por_trafo=L(cl / q) if cl and q else None, ln_kva_por_trafo=L(kva / q) if kva and q else None)
            elif ativo == "trafo_kva":
                f.update(ln_kva_por_trafo=L(kva / q) if kva and q else None, ln_clientes_por_kva=L(cl / kva) if cl and kva else None)
            elif ativo == "rede_bt":
                kb, km = bt.get(u), mt.get(u)
                f.update(ln_clientes_por_km_bt=L(cl / kb) if cl and kb else None, ln_trafo_por_km_bt=L(q / kb) if q and kb else None, ln_razao_mt_bt=L(km / kb) if km and kb else None)
            elif ativo == "rede_mt":
                kb, km = bt.get(u), mt.get(u)
                f.update(ln_clientes_por_km_mt=L(cl / km) if cl and km else None, ln_trafo_por_km_mt=L(q / km) if q and km else None, ln_razao_bt_mt=L(kb / km) if km and kb else None)
            out[u] = f
        self._agg[k] = out
        return out

    # comparabilidade -------------------------------------------------
    def elegivel(self, ativo, nivel, d, t):
        """(ok, motivo, continuidade) da transição t−1 → t no nível."""
        cfg = ATIVOS[ativo]
        m0, m1 = self.estoque(ativo, nivel, d, t - 1), self.estoque(ativo, nivel, d, t)
        if not m0 or not m1:
            return False, "PAINEL_AUSENTE", None
        if (cfg["painel"], d, t) in self.rup_painel or (cfg["painel"], d, t - 1) in self.rup_painel or (d, t, cfg["conceito"], cfg["metrica"]) in self.rup_contrato:
            return False, "RUPTURA", None
        if (d, t) in self.suc or (d, t - 1) in self.suc:
            return False, "SUCESSAO", None
        if nivel == "MUN":
            for (dd, aa), mot in PENDENCIAS_MUN.items():
                if d == dd and aa in (t - 1, t):
                    return False, mot, None
        comuns = [u for u in m1 if u in m0 and u != "SEM_CODIGO"]
        c = min(sum(m1[u] for u in comuns) / sum(m1.values()), sum(m0[u] for u in comuns) / sum(m0.values()))
        if c < CONTINUIDADE_MIN:
            return False, "CHAVE_INSTAVEL", c
        return True, "", c

    def elegivel_dist(self, ativo, nivel, d, o):
        """Coorte da DIST na avaliação o → o+1: comparável em o−1 → o (histórico das referências) e em o → o+1 no nível."""
        ok1, m1, _ = self.elegivel(ativo, nivel, d, o)
        ok2, m2, _ = self.elegivel(ativo, nivel, d, o + 1)
        return (ok1 and ok2), (m2 or m1)


# ------------------------------------------------------------------ modelos granulares
def pares(D, ativo, nivel, t_max, nomes, grupos=None):
    X, g, w, ds = [], [], [], []
    for t in range(2023, t_max + 1):
        for d in D.dists:
            if grupos is not None and D.grupo.get(d, d) not in grupos:
                continue
            ok, _, _ = D.elegivel(ativo, nivel, d, t)
            if not ok:
                continue
            m0, m1 = D.estoque(ativo, nivel, d, t - 1), D.estoque(ativo, nivel, d, t)
            F = D.variaveis(ativo, nivel, d, t - 1)
            for u, v0 in m0.items():
                if u == "SEM_CODIGO" or u not in m1:
                    continue
                X.append([np.nan if F[u].get(n) is None else F[u][n] for n in nomes]); g.append(math.log(m1[u] / v0)); w.append(v0); ds.append(d)
    return np.array(X, float).reshape(len(g), len(nomes)), np.array(g), np.array(w), np.array(ds)


class Granular:
    def __init__(self, algo, nomes, hp):
        self.algo, self.nomes, self.hp = algo, list(nomes), dict(hp)

    def fit(self, X, g, w, ds):
        from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
        from sklearn.impute import SimpleImputer
        from sklearn.linear_model import Ridge
        from sklearn.neighbors import KNeighborsRegressor
        from sklearn.preprocessing import StandardScaler
        lo, hi = np.quantile(g, [0.05, 0.95]); g = np.clip(g, lo, hi)
        self.const = float(np.average(g, weights=w))
        self.alpha_d = {}
        if self.algo in ("G-NULO", "H-NULO"):
            if self.algo == "H-NULO":
                self.alpha_d = encolher(g - self.const, w, ds)
            return self
        cols_ok = [j for j in range(X.shape[1]) if np.isfinite(X[:, j]).any()]
        self.cols = cols_ok
        X = X[:, cols_ok]
        self.imp = SimpleImputer(strategy="median").fit(X); Z = self.imp.transform(X)
        self.sc = StandardScaler().fit(Z); Z = self.sc.transform(Z)
        if self.algo in ("G-RIDGE", "G-HIER"):
            self.est = Ridge(alpha=self.hp["alpha"])
            alvo = g.copy()
            for _ in range(10 if self.algo == "G-HIER" else 1):
                self.est.fit(Z, alvo, sample_weight=w)
                if self.algo != "G-HIER":
                    break
                self.alpha_d = encolher(g - self.est.predict(Z), w, ds)
                alvo = g - np.array([self.alpha_d.get(d, 0.0) for d in ds])
        elif self.algo == "G-HGB":
            self.est = HistGradientBoostingRegressor(max_iter=150, learning_rate=self.hp["learning_rate"], max_depth=self.hp["max_depth"], min_samples_leaf=20, random_state=42)
            self.est.fit(Z, g, sample_weight=w)
        elif self.algo == "G-RF":
            self.est = RandomForestRegressor(n_estimators=300, min_samples_leaf=self.hp["min_samples_leaf"], max_features=self.hp["max_features"], random_state=42, n_jobs=1)
            self.est.fit(Z, g, sample_weight=w)
        elif self.algo == "G-KNN":
            self.est = KNeighborsRegressor(n_neighbors=min(self.hp["k"], len(g))).fit(Z, g); self.y = g
        return self

    def predict(self, X, ds):
        base = np.full(len(X), self.const)
        if self.algo not in ("G-NULO", "H-NULO"):
            Z = self.sc.transform(self.imp.transform(X[:, self.cols]))
            if self.algo == "G-KNN":
                base = np.median(self.y[self.est.kneighbors(Z, return_distance=False)], axis=1)
            else:
                base = self.est.predict(Z)
        return base + np.array([self.alpha_d.get(d, 0.0) for d in ds])


def encolher(r, w, ds):
    """Intercepto por DIST por Bayes empírico (momentos ponderados): α_d = k_d · média_d(r), k_d = τ²/(τ² + σ²/n_eff,d)."""
    por = defaultdict(list)
    for ri, wi, d in zip(r, w, ds):
        por[d].append((ri, wi))
    m, ne, s2 = {}, {}, []
    for d, xs in por.items():
        a = np.array(xs); sw = a[:, 1].sum()
        m[d] = float((a[:, 0] * a[:, 1]).sum() / sw); ne[d] = sw ** 2 / (a[:, 1] ** 2).sum()
        if len(xs) > 1:
            s2.append(float((a[:, 1] * (a[:, 0] - m[d]) ** 2).sum() / sw))
    sigma2 = float(np.mean(s2)) if s2 else 0.0
    mv = np.array(list(m.values()))
    tau2 = max(0.0, float(mv.var()) - float(np.mean([sigma2 / ne[d] for d in m])))
    return {d: (tau2 / (tau2 + sigma2 / ne[d]) if tau2 + sigma2 / ne[d] > 0 else 0.0) * m[d] for d in m}


def prever_dist(D, ativo, nivel, modelo, dists, o):
    """{dist: (previsão agregada da DIST em o+1, unidades previstas)}; contagens arredondadas por unidade e somadas (reconciliado)."""
    cfg = ATIVOS[ativo]
    out = {}
    for d in dists:
        m0 = D.estoque(ativo, nivel, d, o)
        F = D.variaveis(ativo, nivel, d, o)
        us = [u for u in m0 if u != "SEM_CODIGO"]
        X = np.array([[np.nan if F[u].get(n) is None else F[u][n] for n in modelo.nomes] for u in us], float).reshape(len(us), len(modelo.nomes))
        gh = modelo.predict(X, np.array([d] * len(us))) if us else np.array([])
        yh = [m0[u] * math.exp(float(x)) for u, x in zip(us, gh)] + [m0.get("SEM_CODIGO", 0.0)]
        if cfg["contagem"]:
            yh = [math.floor(v + 0.5) for v in yh]
        out[d] = (float(sum(yh)), len(us), {u: v for u, v in zip(us, yh)})
    return out


# ------------------------------------------------------------------ referências por DIST (mesmo código do produto)
def referencias(D, ativo, o, dists):
    """Previsões de o+1 por DIST: persistência, deriva, CAGR e todos os modelos de painel do produto, reexecutados sobre a série do painel."""
    cfg = ATIVOS[ativo]
    series, _, _ = C.carregar_contrato(CONTRATO)
    k = ("PAINEL_" + ativo, cfg["metrica"])
    nivel = cfg["niveis"][0]
    series[k] = {}
    for d in D.dists:
        anos = {}
        for a in D.anos:
            v = D.total(ativo, d, a)
            if v:
                ok = (cfg["painel"], d, a) not in D.rup_painel and (d, a, cfg["conceito"], cfg["metrica"]) not in D.rup_contrato and (d, a) not in D.suc
                anos[a] = ("observado", v, not ok)
        series[k][d] = anos
    fi = C.internas_por_dist(series, ENTRADA)
    fe, _ = C.externas_por_dist(ENTRADA, ENTRADA)
    motor = C.Motor(series, fi, fe)
    alvos = {d: [(a, series[k][d][a][1]) for a in (o - 1, o)] for d in dists if all(a in series[k].get(d, {}) for a in (o - 1, o))}
    prev, _ = motor.prever(k, o, alvos)
    out = defaultdict(dict)
    for m, por in prev.items():
        for d, traj in por.items():
            v = traj[0]
            out[d][m] = math.floor(v + 0.5) if cfg["contagem"] and v >= 0 else v
    return out


# ------------------------------------------------------------------ métricas
def r2(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 5:
        return None
    sst = float(((a - a.mean()) ** 2).sum())
    return None if sst <= 0 else 1 - float(((a - b) ** 2).sum()) / sst


def metricas(y0, y, yh):
    y0, y, yh = (np.asarray(v, float) for v in (y0, y, yh))
    e = yh - y
    return dict(n=len(y), wape=float(np.abs(e).sum() / np.abs(y).sum()), mae=float(np.abs(e).mean()), rmse=float(np.sqrt((e ** 2).mean())),
                vies=float(e.sum() / y.sum()), r2_estoque=r2(y, yh), r2_variacao=r2(y - y0, yh - y0), mae_variacao=float(np.abs((yh - y0) - (y - y0)).mean()),
                r2_crescimento=r2(np.log(y / y0), np.log(np.maximum(yh, 1e-9) / y0)))


def correlacao(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 6 or np.std(a[ok]) == 0 or np.std(b[ok]) == 0:
        return 0.0
    return float(np.corrcoef(a[ok], b[ok])[0, 1])


def wape(y, yh):
    return float(np.abs(np.asarray(yh) - np.asarray(y)).sum() / np.abs(np.asarray(y)).sum())


def bootstrap(D, dists, y, a, b, semente=SEMENTE_BOOT):
    """IC95% de WAPE(a) − WAPE(b) reamostrando grupos econômicos inteiros."""
    rng = np.random.default_rng(semente)
    gs = sorted({D.grupo.get(d, d) for d in dists})
    idx = {g: [i for i, d in enumerate(dists) if D.grupo.get(d, d) == g] for g in gs}
    y, a, b = (np.asarray(v, float) for v in (y, a, b))
    dif = []
    for _ in range(REPLICAS):
        s = [i for g in rng.choice(gs, size=len(gs), replace=True) for i in idx[g]]
        dif.append(wape(y[s], a[s]) - wape(y[s], b[s]))
    return [float(np.percentile(dif, 2.5)), float(np.percentile(dif, 97.5))], len(gs)


# ------------------------------------------------------------------ etapa S (seleção) — 2025 não é carregado
def cohort(D, ativo, niveis, o):
    """DIST comparáveis em todos os níveis candidatos (para comparar granularidades no mesmo conjunto)."""
    out, excl = [], Counter()
    for d in D.dists:
        motivos = [f"{n}:{m}" for n in niveis for ok, m in [D.elegivel_dist(ativo, n, d, o)] if not ok]
        if motivos:
            excl[motivos[0]] += 1
        else:
            out.append(d)
    return out, excl


def avaliar(D, ativo, nivel, modelo, dists, o, ref_total=None):
    t_max = o
    X, g, w, ds = pares(D, ativo, nivel, t_max, modelo.nomes)
    if len(g) < 30:
        return None, None
    modelo.fit(X, g, w, ds)
    p = prever_dist(D, ativo, nivel, modelo, dists, o)
    return p, len(g)


def selecao():
    verificar_protocolo()
    t0 = time.time()
    D = Dados(ano_max=2024)                                   # garantia de vazamento: 2025 não existe nesta etapa
    assert 2025 not in D.anos
    o = 2023
    resultados, sel, espacial, variaveis_rows = [], {}, [], []
    for ativo, cfg in ATIVOS.items():
        dists, excl = cohort(D, ativo, cfg["niveis"], o)
        ref = referencias(D, ativo, o, dists)
        dists = [d for d in dists if cfg["atual"] in ref.get(d, {})]
        y0 = [D.total(ativo, d, o) for d in dists]; y = [D.total(ativo, d, o + 1) for d in dists]
        linhas_ref = {}
        for m in sorted({m for d in dists for m in ref[d]}):
            if all(m in ref[d] for d in dists):
                mt = metricas(y0, y, [ref[d][m] for d in dists]); linhas_ref[m] = mt
                resultados.append(dict(ativo=ativo, etapa="S", tipo="referencia_dist", modelo=m, nivel="DIST", variaveis="", hiper="", **mt))
        melhor_ref = min(v["wape"] for v in linhas_ref.values())
        cands, ajustes = [], 0
        for nivel in cfg["niveis"]:
            nomes_all = VARIAVEIS[ativo]
            # filtros no treino S: disponibilidade, constância, redundância
            X, g, w, ds = pares(D, ativo, nivel, o, nomes_all)
            vivas, status = [], {}
            for j, n in enumerate(nomes_all):
                col = X[:, j]; disp = float(np.isfinite(col).mean()) if len(col) else 0.0
                if disp < 0.5:
                    status[n] = ("DESCARTADA", f"disponibilidade {disp:.0%} < 50% no treino S")
                elif np.nanstd(col) < 1e-9:
                    status[n] = ("DESCARTADA", "constante no treino S")
                else:
                    ruim = next((v for v in vivas if abs(correlacao(X[:, nomes_all.index(v)], col)) > 0.95), None)
                    if ruim:
                        status[n] = ("DESCARTADA", f"redundante com {ruim} (|r| > 0,95)")
                    else:
                        status[n] = ("CANDIDATA", f"disponibilidade {disp:.0%}"); vivas.append(n)

            def tentar(algo, nomes, hp):
                nonlocal ajustes
                ajustes += 1
                p, n_pares = avaliar(D, ativo, nivel, Granular(algo, nomes, hp), dists, o)
                if p is None:
                    return None
                mt = metricas(y0, y, [p[d][0] for d in dists])
                c = dict(ativo=ativo, etapa="S", tipo="granular", modelo=algo, nivel=nivel, variaveis="|".join(nomes), hiper=json.dumps(hp, sort_keys=True),
                         pares_treino=n_pares, unidades_previstas=sum(p[d][1] for d in dists), **mt)
                resultados.append(c); cands.append(c)
                return c
            tentar("G-NULO", [], {}); tentar("H-NULO", [], {})
            # importância por permutação (G-RIDGE com todas as vivas, validação S, WAPE da DIST agregada)
            base = Granular("G-RIDGE", vivas, PADRAO["G-RIDGE"])
            p0, _ = avaliar(D, ativo, nivel, base, dists, o)
            w0 = wape(y, [p0[d][0] for d in dists])
            rng = np.random.default_rng(42); imp = {}
            for j, n in enumerate(vivas):
                inc = []
                for _ in range(5):
                    pr = {}
                    for d in dists:
                        m0 = D.estoque(ativo, nivel, d, o); F = D.variaveis(ativo, nivel, d, o); us = [u for u in m0 if u != "SEM_CODIGO"]
                        Xd = np.array([[np.nan if F[u].get(nn) is None else F[u][nn] for nn in vivas] for u in us], float).reshape(len(us), len(vivas))
                        pr[d] = (m0, us, Xd)
                    allX = np.vstack([pr[d][2] for d in dists if len(pr[d][1])])
                    perm = rng.permutation(allX[:, j]); k0 = 0
                    tot = []
                    for d in dists:
                        m0, us, Xd = pr[d]
                        if len(us):
                            Xd = Xd.copy(); Xd[:, j] = perm[k0:k0 + len(us)]; k0 += len(us)
                            gh = base.predict(Xd, np.array([d] * len(us)))
                            v = sum(m0[u] * math.exp(float(x)) for u, x in zip(us, gh)) + m0.get("SEM_CODIGO", 0.0)
                        else:
                            v = m0.get("SEM_CODIGO", 0.0)
                        tot.append(v)
                    inc.append(wape(y, tot) - w0)
                imp[n] = float(np.mean(inc))
            ordem = sorted(vivas, key=lambda n: -imp[n])
            for n in nomes_all:
                variaveis_rows.append(dict(ativo=ativo, nivel=nivel, variavel=n, status_filtro=status[n][0], motivo_filtro=status[n][1],
                                           importancia_permutacao_S=None if n not in imp else round(imp[n], 7), ordem=ordem.index(n) + 1 if n in ordem else None))

            def prefixos(algo):
                melhor, sem = None, 0
                for i in range(1, min(8, len(ordem)) + 1):
                    c = tentar(algo, ordem[:i], PADRAO[algo])
                    if c is None:
                        break
                    if melhor is None or c["wape"] < melhor["wape"] - 1e-12:
                        melhor, sem = c, 0
                    else:
                        sem += 1
                        if sem >= 2:
                            break
                if melhor is None:
                    return None
                for hp in GRADES[algo]:
                    c = tentar(algo, melhor["variaveis"].split("|"), hp)
                    if c and c["wape"] < melhor["wape"] - 1e-12:
                        melhor = c
                return melhor
            br = prefixos("G-RIDGE")
            if br:
                tentar("G-HIER", br["variaveis"].split("|"), json.loads(br["hiper"]))
            prefixos("G-HGB")
            melhor_ate_aqui = min((c["wape"] for c in cands if c["nivel"] == nivel), default=9)
            if melhor_ate_aqui <= 1.25 * melhor_ref and ajustes < MAX_AJUSTES * len(cfg["niveis"]):
                prefixos("G-RF"); prefixos("G-KNN")
            else:
                resultados.append(dict(ativo=ativo, etapa="S", tipo="parada", modelo="G-RF|G-KNN", nivel=nivel,
                                       motivo=f"melhor granular WAPE_S {melhor_ate_aqui:.5f} > 1,25 × melhor referência {melhor_ref:.5f}: RF e KNN não executados"))
        # seleção congelada: menor WAPE_S; empate → mais simples e nível da hipótese
        rank = lambda c: (round(c["wape"], 6), ORDEM_SIMPLES.index(c["modelo"]), cfg["niveis"].index(c["nivel"]))
        best = min(cands, key=rank)
        sel[ativo] = dict(modelo=best["modelo"], nivel=best["nivel"], variaveis=best["variaveis"].split("|") if best["variaveis"] else [], hiper=json.loads(best["hiper"]),
                          wape_S=best["wape"], dists_S=len(dists), exclusoes_coorte_S=dict(excl), ajustes_S=ajustes,
                          melhor_referencia_S=min(linhas_ref, key=lambda m: linhas_ref[m]["wape"]), wape_melhor_referencia_S=melhor_ref,
                          wape_modelo_atual_S=linhas_ref[cfg["atual"]]["wape"])
        # teste espacial (mesmo ano 2022 → 2023): grupos econômicos retidos, 5 dobras
        espacial += teste_espacial(D, ativo, sel[ativo])
        print(f"{ativo}: selecionado {best['modelo']} {best['nivel']} WAPE_S {best['wape']:.5f} (atual {sel[ativo]['wape_modelo_atual_S']:.5f}, melhor ref {melhor_ref:.5f}); {ajustes} ajustes", flush=True)
    escrever(AQUI / "resultados_S.csv", resultados)
    escrever(AQUI / "03_MATRIZ_VARIAVEIS.csv", variaveis_rows + matriz_variaveis_estatica())
    escrever(AQUI / "espacial_E.csv", espacial)
    corpo = json.dumps(sel, ensure_ascii=False, indent=1, sort_keys=True)
    (AQUI / "selecao_congelada.json").write_text(corpo, encoding="utf-8")
    (AQUI / "selecao_congelada.sha256").write_text(hashlib.sha256(corpo.encode()).hexdigest() + "\n", encoding="utf-8")
    (AQUI / "custo_S.json").write_text(json.dumps(dict(segundos=round(time.time() - t0, 1), pico_memoria_mb=pico_memoria_mb()), indent=1), encoding="utf-8")


def teste_espacial(D, ativo, s):
    """Generalização para grupos não vistos no MESMO ano (pares 2022 → 2023): treino em 4/5 dos grupos, previsão do 2023 dos grupos retidos."""
    rows = []
    grupos = sorted({D.grupo.get(d, d) for d in D.dists})
    rng = np.random.default_rng(7); rng.shuffle(grupos)
    dobras = [set(grupos[i::5]) for i in range(5)]
    ys, yp, yb, dd = [], [], [], []
    for ret in dobras:
        X, g, w, ds = pares(D, ativo, s["nivel"], 2023, s["variaveis"], grupos=set(grupos) - ret)
        if len(g) < 30:
            continue
        m = Granular(s["modelo"], s["variaveis"], s["hiper"]).fit(X, g, w, ds)
        alvo = [d for d in D.dists if D.grupo.get(d, d) in ret and D.elegivel(ativo, s["nivel"], d, 2023)[0]]
        p = prever_dist(D, ativo, s["nivel"], m, alvo, 2022)
        for d in alvo:
            ys.append(D.total(ativo, d, 2023)); yp.append(p[d][0]); yb.append(D.total(ativo, d, 2022)); dd.append(d)
    if ys:
        rows.append(dict(ativo=ativo, teste="espacial_grupos_nao_vistos_2022_2023", modelo=s["modelo"], nivel=s["nivel"], dists=len(ys),
                         grupos=len({D.grupo.get(d, d) for d in dd}), wape=wape(ys, yp), wape_persistencia=wape(ys, yb), r2_crescimento=r2(np.log(np.array(ys) / np.array(yb)), np.log(np.maximum(yp, 1e-9) / np.array(yb))),
                         nota="mesmo ano; não prova capacidade de prever anos futuros; efeito por DIST = 0 para DIST não vista"))
    return rows


def matriz_variaveis_estatica():
    """Variáveis consideradas e não usadas, com o motivo (vazamento, disponibilidade, escopo)."""
    nao = [("crescimento_anterior_do_ativo", "exige 2021 para pares com origem 2022 (proibido); indisponível no treino S"),
           ("crescimento_contemporaneo_de_consumidores_ou_trafos", "informação do ano-alvo (futuro em relação à origem)"),
           ("densidade_territorial_area", "sem área servida validada no painel (o painel UCBT registra 'no validated served area denominator')"),
           ("circuito_CTMT_como_unidade", "reconfiguração frequente (diagnóstico 06); não é unidade-alvo"),
           ("caracteristicas_TUC_565_detalhadas", "o painel já restringe a TUC 565 com vínculo EQ→UN bijetivo; atributos adicionais exigem extração nova"),
           ("geracao_distribuida_UGBT", "sem painel extraído; extração nova não autorizada nesta etapa"),
           ("conexoes_DAT_CON_do_ano_alvo", "proibido: conexões de 2024 não prevêem 2024 a partir de 2023")]
    return [dict(ativo="todos", nivel="", variavel=n, status_filtro="NAO_USADA", motivo_filtro=m) for n, m in nao]


# ------------------------------------------------------------------ etapa F (avaliação final, uma vez)
def final():
    verificar_protocolo()
    saida = AQUI / "04_RESULTADOS_BACKTEST.csv"
    if saida.exists():
        sys.exit("BLOQUEADO: a avaliação final já foi executada (o alvo de 2025 só pode ser usado uma vez).")
    corpo = (AQUI / "selecao_congelada.json").read_text(encoding="utf-8")
    if hashlib.sha256(corpo.encode()).hexdigest() != (AQUI / "selecao_congelada.sha256").read_text(encoding="utf-8").strip():
        sys.exit("BLOQUEADO: seleção congelada alterada depois do registro do hash.")
    sel = json.loads(corpo)
    t0 = time.time()
    D = Dados(ano_max=2025)
    o = 2024
    res, comp, por_dist, cobertura = [], [], [], []
    resS = ler_csv(AQUI / "resultados_S.csv")
    for ativo, cfg in ATIVOS.items():
        s = sel[ativo]
        dists, excl = cohort(D, ativo, [s["nivel"]], o)
        ref = referencias(D, ativo, o, dists)
        dists = [d for d in dists if cfg["atual"] in ref.get(d, {})]
        y0 = np.array([D.total(ativo, d, o) for d in dists]); y = np.array([D.total(ativo, d, o + 1) for d in dists])
        ref_m = {}
        for m in sorted({m for d in dists for m in ref[d]}):
            if all(m in ref[d] for d in dists):
                ref_m[m] = np.array([ref[d][m] for d in dists], float)
                res.append(dict(ativo=ativo, etapa="F", tipo="referencia_dist", modelo=m, nivel="DIST", **metricas(y0, y, ref_m[m])))
        # candidato congelado
        mod = Granular(s["modelo"], s["variaveis"], s["hiper"])
        p, n_pares = avaliar(D, ativo, s["nivel"], mod, dists, o)
        cand = np.array([p[d][0] for d in dists])
        mc = metricas(y0, y, cand)
        res.append(dict(ativo=ativo, etapa="F", tipo="granular_congelado", modelo=s["modelo"], nivel=s["nivel"], variaveis="|".join(s["variaveis"]), hiper=json.dumps(s["hiper"]),
                        pares_treino=n_pares, unidades_previstas=sum(p[d][1] for d in dists), **mc))
        # exploratórios (todas as configurações da etapa S, sem uso em decisão)
        for r in resS:
            if r["ativo"] != ativo or r.get("tipo") != "granular":
                continue
            if r["modelo"] == s["modelo"] and r["nivel"] == s["nivel"] and r["variaveis"] == "|".join(s["variaveis"]) and json.loads(r["hiper"]) == s["hiper"]:
                continue
            if r["nivel"] != s["nivel"]:
                continue                                              # outra granularidade tem outra coorte; não comparável aqui
            mm = Granular(r["modelo"], r["variaveis"].split("|") if r["variaveis"] else [], json.loads(r["hiper"]))
            pp, _ = avaliar(D, ativo, s["nivel"], mm, dists, o)
            if pp:
                res.append(dict(ativo=ativo, etapa="F", tipo="granular_exploratorio", modelo=r["modelo"], nivel=r["nivel"], variaveis=r["variaveis"], hiper=r["hiper"],
                                **metricas(y0, y, [pp[d][0] for d in dists])))
        # decisões
        bases = {b: ref_m[b] for b in ("persistencia", "deriva", "crescimento_geometrico") if b in ref_m}
        mb = min(bases, key=lambda b: wape(y, bases[b]))
        atual = ref_m[cfg["atual"]]
        w_c, w_a, w_b = wape(y, cand), wape(y, atual), wape(y, bases[mb])
        ic_b, ngr = bootstrap(D, dists, y, cand, bases[mb])
        ic_a, _ = bootstrap(D, dists, y, cand, atual)
        fis_ok = bool(np.all(cand >= 0) and (not cfg["contagem"] or np.all(np.mod(cand, 1) == 0)))
        mv_a = metricas(y0, y, atual)
        vies_ok = abs(mc["vies"]) <= abs(mv_a["vies"]) + 0.01
        competitiva = w_c <= 0.95 * w_a and w_c <= w_b and fis_ok and vies_ok
        # sensibilidade 1: sem a DIST de maior contribuição absoluta à diferença contra o melhor baseline
        contrib = np.abs(cand - y) - np.abs(bases[mb] - y)
        k = int(np.argmax(np.abs(contrib))); keep = np.arange(len(y)) != k
        sens1 = (wape(y[keep], cand[keep]) - wape(y[keep], bases[mb][keep])) < 0 if (w_c - w_b) < 0 else (wape(y[keep], cand[keep]) - wape(y[keep], bases[mb][keep])) >= 0
        # sensibilidade 2: sem as 5% maiores variações relativas observadas
        var = np.abs(np.log(y / y0)); keep2 = var <= np.quantile(var, 0.95)
        sens2 = (wape(y[keep2], cand[keep2]) - wape(y[keep2], bases[mb][keep2])) < 0 if (w_c - w_b) < 0 else (wape(y[keep2], cand[keep2]) - wape(y[keep2], bases[mb][keep2])) >= 0
        validado = competitiva and ic_b[1] < 0 and len(dists) >= 20 and ngr >= 12 and sens1 and sens2
        if not fis_ok:
            classe = "REJEITADO"
        elif validado:
            classe = "VALIDADO_RETROSPECTIVAMENTE_COM_RESTRICOES"
        elif competitiva:
            classe = "MELHORIA_COMPETITIVA_EXPERIMENTAL"
        elif w_c > w_a and s["wape_S"] < s["wape_modelo_atual_S"]:
            classe = "REJEITADO"                 # ganhou só na etapa S e piorou fora da amostra
        else:
            classe = "SEM_GANHO"
        comp.append(dict(ativo=ativo, nivel=s["nivel"], candidato=s["modelo"], variaveis="|".join(s["variaveis"]), hiper=json.dumps(s["hiper"]),
                         dists=len(dists), grupos=ngr, unidades=sum(p[d][1] for d in dists), pares_treino=n_pares,
                         wape_candidato=w_c, wape_modelo_atual=w_a, modelo_atual=cfg["atual"], wape_melhor_baseline=w_b, melhor_baseline=mb,
                         ganho_vs_atual=1 - w_c / w_a, ganho_vs_baseline=1 - w_c / w_b, ic95_dif_vs_baseline=json.dumps([round(x, 6) for x in ic_b]),
                         ic95_dif_vs_atual=json.dumps([round(x, 6) for x in ic_a]),
                         r2_crescimento_candidato=mc["r2_crescimento"], r2_crescimento_atual=mv_a["r2_crescimento"], r2_crescimento_baseline=metricas(y0, y, bases[mb])["r2_crescimento"],
                         r2_variacao_candidato=mc["r2_variacao"], r2_variacao_atual=mv_a["r2_variacao"], mae_variacao_candidato=mc["mae_variacao"], mae_variacao_atual=mv_a["mae_variacao"],
                         vies_candidato=mc["vies"], vies_atual=mv_a["vies"], restricoes_fisicas=fis_ok, vies_ok=vies_ok, sensibilidade_sem_maior_dist=sens1,
                         sensibilidade_sem_5pct_variacoes=sens2, wape_S_candidato=s["wape_S"], wape_S_atual=s["wape_modelo_atual_S"], classe=classe))
        for i, d in enumerate(dists):
            por_dist.append(dict(ativo=ativo, DIST=d, empresa=D.empresa.get(d, ""), grupo=D.grupo.get(d, d), etapa="F", y_2024=y0[i], y_2025=y[i],
                                 prev_candidato=cand[i], prev_modelo_atual=atual[i], prev_melhor_baseline=bases[mb][i],
                                 erro_abs_candidato=abs(cand[i] - y[i]), erro_abs_atual=abs(atual[i] - y[i]), erro_abs_baseline=abs(bases[mb][i] - y[i]),
                                 delta_observado=y[i] - y0[i], delta_candidato=cand[i] - y0[i], delta_atual=atual[i] - y0[i], unidades=p[d][1]))
        cobertura.append(dict(ativo=ativo, etapa="F", nivel=s["nivel"], dists_avaliadas=len(dists), exclusoes=json.dumps(dict(excl), ensure_ascii=False)))
        print(f"{ativo}: {classe} | WAPE_F cand {w_c:.5f} atual {w_a:.5f} base {w_b:.5f} | r2g cand {mc['r2_crescimento']} atual {mv_a['r2_crescimento']}", flush=True)
    escrever(saida, [dict(r) for r in ler_csv(AQUI / "resultados_S.csv")] + res)
    escrever(AQUI / "05_COMPARACAO_MODELOS.csv", comp)
    escrever(AQUI / "06_RESULTADOS_POR_DISTRIBUIDORA.csv", por_dist)
    escrever(AQUI / "cobertura_F.csv", cobertura)
    (AQUI / "custo_F.json").write_text(json.dumps(dict(segundos=round(time.time() - t0, 1), pico_memoria_mb=pico_memoria_mb()), indent=1), encoding="utf-8")


# ------------------------------------------------------------------ Gate 1: entrada
def entrada():
    verificar_protocolo()
    t0 = time.time()
    CACHE.mkdir(parents=True, exist_ok=True)
    D = Dados(ano_max=2025)
    # hashes: agregados contra os checkpoints da extração
    divergentes, ok = [], 0
    for p in D.arquivos:
        ck = json.loads((p.parent / "checkpoint.json").read_text(encoding="utf-8"))
        h = sha(p)
        if h == ck.get("output_sha256"):
            ok += 1
        else:
            divergentes.append(str(p))
    manifest = dict(protocolo_commit="d988416", agregados_verificados=ok, agregados_divergentes=divergentes,
                    contratos={str(q.relative_to(RAIZ)) if RAIZ in q.parents else str(q): sha(q) for q in
                               (CONTRATO / "serie_fisica_nacional.csv", SUCESSAO, EXTERNAS, INDICE_V2, PRODUTO, RAIZ / "motor_cenarios/cenarios.py",
                                ENTRADA / "uc_por_municipio.csv", ENTRADA / "energia_uc.csv", ENTRADA / "externas_ibge_municipal.csv", INVENTARIO)},
                    manifesto_painel_sha256=sha(PAINEL / "MANIFESTO_PAINEL.json"))
    # cobertura e exclusões por ativo × nível × transição × DIST
    rows = []
    for ativo, cfg in ATIVOS.items():
        for nivel in cfg["niveis"]:
            for t in (2023, 2024, 2025):
                for d in D.dists:
                    m0, m1 = D.estoque(ativo, nivel, d, t - 1), D.estoque(ativo, nivel, d, t)
                    okk, mot, c = D.elegivel(ativo, nivel, d, t)
                    uni = len([u for u in (m0 or {}) if u != "SEM_CODIGO"]); est = sum((m0 or {}).values())
                    par = len([u for u in (m1 or {}) if u in (m0 or {}) and u != "SEM_CODIGO"]) if m0 and m1 else 0
                    rows.append(dict(ativo=ativo, nivel=nivel, transicao=f"{t - 1}->{t}", DIST=d, grupo=D.grupo.get(d, d), incluida=okk, motivo=mot or "",
                                     unidades_origem=uni, unidades_pareadas=par, estoque_origem=round(est, 3),
                                     estoque_sem_codigo_origem=round((m0 or {}).get("SEM_CODIGO", 0.0), 3), continuidade=None if c is None else round(c, 4)))
    escrever(AQUI / "02_COBERTURA_E_EXCLUSOES.csv", rows)
    resumo = Counter((r["ativo"], r["nivel"], r["transicao"], r["motivo"] or "INCLUIDA") for r in rows)
    manifest["exclusoes_resumo"] = {"|".join(k): v for k, v in sorted(resumo.items())}
    manifest["auditoria_dat_con"] = auditar_datcon()
    manifest["segundos"] = round(time.time() - t0, 1); manifest["pico_memoria_mb"] = pico_memoria_mb()
    (AQUI / "00_MANIFESTO_ENTRADA.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in manifest.items() if k != "exclusoes_resumo"}, ensure_ascii=False, indent=1)[:3000])


def auditar_datcon(dists=("26", "6600", "5707")):
    """Amostra: as conexões de 2023 vistas na fotografia de 2023 × na de 2024, e a reescrita de DAT_CON entre fotografias (mesma UC)."""
    import duckdb
    sel = {(r["dist"], int(r["competencia"])): r["item_id"] for r in ler_csv(INVENTARIO) if r["tipo"] == "selecionada_no_contrato"}
    con = duckdb.connect()
    tmp = CACHE / "duckdb_tmp"; tmp.mkdir(parents=True, exist_ok=True)
    con.execute(f"SET memory_limit='2GB'; SET temp_directory='{tmp.as_posix()}'; SET threads=2")
    out = []
    for d in dists:
        ps = {a: Path(f"D:/NUCLEO_BDGD_2022_2024/parquet/{a}/{d}/{sel[(d, a)]}/UCBT.parquet") for a in (2023, 2024) if (d, a) in sel}
        if len(ps) < 2 or not all(p.exists() for p in ps.values()):
            out.append(dict(DIST=d, estado="SEM_PARQUET")); continue
        q = lambda p: (f"SELECT CAST(COD_ID AS VARCHAR) id, coalesce(CAST(PN_CON AS VARCHAR),'') pn, try_strptime(CAST(DAT_CON AS VARCHAR),'%d/%m/%Y')::DATE dc "
                       f"FROM read_parquet('{p.as_posix()}') WHERE CAST(SIT_ATIV AS VARCHAR)='AT'")
        con.execute(f"CREATE OR REPLACE TEMP TABLE a AS {q(ps[2023])}"); con.execute(f"CREATE OR REPLACE TEMP TABLE b AS {q(ps[2024])}")
        jan = "dc > DATE '2022-12-31' AND dc <= DATE '2023-12-31'"
        n23 = con.execute(f"SELECT count(*) FROM a WHERE {jan}").fetchone()[0]
        n24 = con.execute(f"SELECT count(*) FROM b WHERE {jan}").fetchone()[0]
        tot, mud, sumiu = con.execute("SELECT count(*), count(*) FILTER(WHERE b.id IS NOT NULL AND a.dc IS DISTINCT FROM b.dc), count(*) FILTER(WHERE b.id IS NULL) "
                                      "FROM (SELECT DISTINCT id,pn,dc FROM a) a LEFT JOIN (SELECT id,pn,min(dc) dc FROM b GROUP BY id,pn) b USING (id,pn)").fetchone()
        out.append(dict(DIST=d, conexoes_2023_na_foto_2023=n23, conexoes_2023_na_foto_2024=n24, razao=round(n24 / n23, 4) if n23 else None,
                        ucs_2023=tot, ucs_com_dat_con_reescrita=mud, fracao_reescrita=round(mud / tot, 5) if tot else None,
                        ucs_2023_ausentes_em_2024=sumiu, fracao_ausente=round(sumiu / tot, 4) if tot else None))
    con.close()
    return out


if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    {"entrada": entrada, "selecao": selecao, "final": final}[sys.argv[1]]()
