"""Pesquisa EXPERIMENTAL de recuperação dos cenários ausentes, conforme 04_PROTOCOLO_CANDIDATOS.md (versão recuperacao-1).

    D:/NUCLEO_BDGD_2025/.venv-motor/Scripts/python.exe HOMOLOGACAO/CIENTIFICA/RECUPERACAO_CENARIOS/recuperar.py <saida_dir>

Execução de referência para auditoria; não é a integração ao produto.
- Reusa motor_cenarios/cenarios.py e motor_cenarios/otimizacao/otimizar.py sem alterá-los.
- Lê o produto publicado e grava só em <saida_dir>.
- Usa só as competências BDGD 2022–2025 do contrato nacional, sem extração nova.
- RECUP_SO=conceito/metrica,... restringe a execução às métricas listadas (depuração).
"""
import csv
import hashlib
import json
import math
import os
import platform
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]                                   # nucleo-dados-bdgd
sys.path.insert(0, str(RAIZ / "motor_cenarios" / "otimizacao"))
import otimizar as OT  # noqa: E402  (importa também motor_cenarios/cenarios.py como OT.C)

C = OT.C
PROTOCOLO = dict(
    versao="recuperacao-1", tolerancia_erro=C.TOLERANCIA_ERRO, diferenca_minima_ano=C.DIFERENCA_MINIMA_PP / 100, diferenca_minima_unidades=1,
    razao_plausivel=list(C.RAZAO_PLAUSIVEL), percentis_modelo=[1, 99], percentis_condicional=[5, 95], min_transicoes_condicional=2,
    min_transicoes_metrica=20, guarda_F=C.TOLERANCIA_ERRO, n1_phi=[0.8, 0.9], n2_kappa=[1.0, 3.0], n2_grupo_min_dist=3,
    n5_tau={"conservador": 0.2, "agressivo": 0.8}, n5_calibracao=[0.10, 0.30], n5_min_pares_S=60,
    n6_ativos=[["medidores", "quantidade"], ["ramais", "extensao_km"], ["rede_bt", "extensao_km"], ["rede_mt", "extensao_km"],
               ["postes", "quantidade"], ["trafo_dist", "quantidade"]], n6_beta_max=3.0,
    bootstrap_replicas=2000, semente=20261104, bootstrap_min_dist=20, outliers_quantil=0.95, r2_min_pontos=5)
LADOS = ("conservador", "agressivo")
SINAL = {"conservador": -1, "agressivo": 1}
UC = ("consumidores", "quantidade")
SO = [x for x in (os.environ.get("RECUP_SO") or "").split(",") if x]
ENTRADAS = {
    "contrato": RAIZ / "output-historico/contrato-integracao/serie_fisica_nacional.csv",
    "publicado": RAIZ / "web/public/data/previsoes/cenarios-motor.json",
    "modelos_otimizacao": RAIZ / "motor_cenarios/otimizacao/saida/MODELOS_AVALIADOS.csv",
    "matriz_otimizacao": RAIZ / "motor_cenarios/otimizacao/saida/MATRIZ_MODELOS_OTIMIZADOS.csv",
    "estado_cientifico": RAIZ / "HOMOLOGACAO/CIENTIFICA/09_ESTADO_POR_METRICA_E_HORIZONTE.csv",
    "grupos": RAIZ / "etl/bdgd2025/config/grupos_2025.json",
    "conceitos": RAIZ / "etl/bdgd2025/config/conceitos_2025.json",
}
COD_ESTADO = {"observado": "o", "nao_homologado": "h", "ausente": "a", "zero_verificado": "z", "nao_aplicavel": "n"}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def r2(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < PROTOCOLO["r2_min_pontos"]:
        return None
    sst = float(((a - a.mean()) ** 2).sum())
    return None if sst <= 0 else 1 - float(((a - b) ** 2).sum()) / sst


# ------------------------------------------------------------------ harness de backtest (mesmos pontos do produto)
def backtest(segs, prever, ref):
    """prever(origem, alvos, H) -> {dist: [ŷ(origem+h)]}. Pontos idênticos aos de cenarios.executar_metrica.
    Retorna ({(h, o, d): (y0, y, ŷ)}, motivo) — motivo != None se o candidato não cobre os pontos de referência."""
    pts = {}
    for o in C.ORIGENS:
        alvos = {d: [p for p in s if p[0] <= o] for d, s in segs.items()}
        alvos = {d: h for d, h in alvos.items() if len(h) >= 2}
        prev = prever(o, alvos, C.BASE - o)
        if prev is None:
            return None, "TREINO_INSUFICIENTE"
        for d, traj in prev.items():
            real = dict(segs[d])
            for h in range(1, C.BASE - o + 1):
                if o + h in real:
                    pts[(h, o, d)] = (real[o], real[o + h], traj[h - 1])
    if ref and not set(ref) <= set(pts):
        return None, "BACKTEST_INCOMPLETO"
    return {k: pts[k] for k in sorted(ref)}, None


def etapa_de(key):
    h, o, _ = key
    return "S" if (h, o) == (1, 2023) else "F" if (h, o) == (1, 2024) else "H2"


def estat(lista):
    """lista: [(d, y0, y, ŷ)]. Estatísticas da seção 8 do protocolo."""
    if not lista:
        return {"n": 0}
    y0 = np.array([p[1] for p in lista], float); y = np.array([p[2] for p in lista], float); yh = np.array([p[3] for p in lista], float)
    e = yh - y
    dy = np.abs(y - y0).sum()
    var = np.abs(np.log(y / y0)); k = var <= np.quantile(var, PROTOCOLO["outliers_quantil"])
    return {"n": len(y), "wape": float(np.abs(e).sum() / np.abs(y).sum()), "mae": float(np.abs(e).mean()), "rmse": float(np.sqrt((e ** 2).mean())),
            "vies": float(e.sum() / y.sum()), "r2_estoque": r2(y, yh), "r2_crescimento": r2(np.log(y / y0), np.log(np.maximum(yh, 1e-9) / y0)),
            "r2_variacao": r2(y - y0, yh - y0), "wape_expansao": float(np.abs(e).sum() / dy) if dy > 0 else None,
            "wape_sem_outliers": float(np.abs(e[k]).sum() / np.abs(y[k]).sum())}


def plausivel_metrica(fut, segs):
    """Elegibilidade do gerador (escolher_cenarios): projeção não negativa e no máximo 5% das séries fora de RAZAO_PLAUSIVEL."""
    if not fut:
        return False, "SEM_PROJECAO_FINAL", None
    base = {d: segs[d][-1][1] for d in fut}
    razoes = [fut[d][-1] / base[d] for d in fut if base[d] > 0]
    implaus = sum(1 for r in razoes if not (C.RAZAO_PLAUSIVEL[0] <= r <= C.RAZAO_PLAUSIVEL[1]) or not math.isfinite(r))
    neg = any(v < 0 or not math.isfinite(v) for d in fut for v in fut[d])
    tot0 = sum(base.values()); tot5 = sum(fut[d][-1] for d in fut)
    cagr = (tot5 / tot0) ** (1 / 5) - 1 if tot0 > 0 and tot5 > 0 else None
    if neg:
        return False, "PROJECAO_NEGATIVA_OU_NAO_FINITA", cagr
    if razoes and implaus / len(razoes) > C.MAX_IMPLAUSIVEL:
        return False, f"TRAJETORIA_IMPLAUSIVEL ({implaus}/{len(razoes)})", cagr
    return True, None, cagr


# ------------------------------------------------------------------ candidatos
class Painel:
    """Candidato de painel (X ou N5): o mesmo pré-processamento do gerador (OT.ajustar ou quantílico equivalente)."""

    def __init__(self, motor, k, nomes, ajuste):
        self.motor, self.k, self.nomes, self.ajuste = motor, k, nomes, ajuste
        self.n_pares = {}

    def __call__(self, origem, alvos, H):
        self.motor.k = self.k
        X, g = self.motor.pares_treino(self.k, origem, self.nomes)
        self.n_pares[origem] = len(g)
        if len(g) < C.MIN_SERIES_PAINEL:
            return None
        mod = self.ajuste(X, g)
        ds = [d for d, h in alvos.items() if len(h) >= 1]
        if not ds:
            return {}
        gp = mod.predict(np.asarray([C.vetor(self.motor.feats(d, origem, alvos[d][-1][1]), self.nomes) for d in ds], float))
        return {d: [alvos[d][-1][1] * math.exp(h * float(gg)) for h in range(1, H + 1)] for d, gg in zip(ds, gp)}


def ajuste_quantil(tau):
    def f(X, g):
        from sklearn.impute import SimpleImputer
        from sklearn.linear_model import QuantileRegressor
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        lo, hi = np.quantile(g, [0.05, 0.95])
        m = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), QuantileRegressor(quantile=tau, alpha=0.0, solver="highs"))
        m.fit(np.asarray(X, float), np.clip(g, lo, hi))
        return m
    return f


def transicoes(series, k, ate):
    """Transições comparáveis (observado → observado, positivas, sem ruptura) com t ≤ ate: [(dist, t, g)]."""
    out = []
    for d, anos in series[k].items():
        for t in range(2023, ate + 1):
            a, b = anos.get(t - 1), anos.get(t)
            if a and b and a[0] == b[0] == "observado" and (a[1] or 0) > 0 and (b[1] or 0) > 0 and not b[2]:
                out.append((d, t, math.log(b[1] / a[1])))
    return out


def n1(phi):
    def prever(origem, alvos, H):
        out = {}
        for d, hist in alvos.items():
            (t0, y0), (t1, y1) = hist[0], hist[-1]
            b = math.log(y1 / y0) / (t1 - t0)
            out[d] = [y1 * math.exp(b * sum(phi ** j for j in range(1, h + 1))) for h in range(1, H + 1)]
        return out
    return prever


def n2(series, k, kappa, grupo=None):
    def prever(origem, alvos, H):
        tr = transicoes(series, k, origem)
        if not tr:
            return None
        mu_nac = float(np.median([g for _, _, g in tr]))
        mu_grp = {}
        if grupo is not None:
            por = defaultdict(list); dists = defaultdict(set)
            for d, _, g in tr:
                if grupo.get(d):
                    por[grupo[d]].append(g); dists[grupo[d]].add(d)
            mu_grp = {gr: float(np.median(v)) for gr, v in por.items() if len(dists[gr]) >= PROTOCOLO["n2_grupo_min_dist"]}
        out = {}
        for d, hist in alvos.items():
            (t0, y0), (t1, y1) = hist[0], hist[-1]
            n = t1 - t0
            gbar = math.log(y1 / y0) / n
            mu = mu_grp.get(grupo.get(d)) if grupo is not None and grupo.get(d) in mu_grp else mu_nac
            w = n / (n + kappa)
            g = w * gbar + (1 - w) * mu
            out[d] = [y1 * math.exp(h * g) for h in range(1, H + 1)]
        return out
    return prever


# ------------------------------------------------------------------ regras de qualidade (seção 6)
def publicar(v, natureza):
    return [C.mc.physical_prediction(x, natureza) for x in v] if natureza == "discrete_count" else [round(x, 3) for x in v]


def checar(E, Epub, M, Mpub, y25, lado, disc, p01, p99):
    s = SINAL[lado]
    if not E:
        return "SEM_PROJECAO", {}
    q = {}
    q["Q1"] = all(math.isfinite(v) and v >= 0 for v in E)
    r = E[-1] / y25 if y25 > 0 and q["Q1"] else float("nan")
    q["Q2"] = bool(q["Q1"] and PROTOCOLO["razao_plausivel"][0] <= r <= PROTOCOLO["razao_plausivel"][1])
    gE = math.log(E[-1] / y25) / 5 if q["Q1"] and E[-1] > 0 else float("-inf")
    g26 = math.log(E[0] / y25) if q["Q1"] and E[0] > 0 else float("-inf")
    q["Q3"] = bool(p01 <= gE <= p99)
    q["Q4"] = bool(p01 <= g26 <= p99)
    tol = 1e-9 * max(1.0, y25)
    gaps = [s * (e - m) for e, m in zip(E, M)]
    q["Q5"] = all(x >= -tol for x in gaps)
    q["Q6"] = bool(Epub) and all(s * (a - b) >= 0 for a, b in zip(Epub, Mpub))
    gM = math.log(M[-1] / y25) / 5
    q["Q7"] = bool(math.isfinite(gE) and s * (gE - gM) >= PROTOCOLO["diferenca_minima_ano"] - 1e-12)
    q["Q8"] = (not disc) or bool(Epub and s * (E[-1] - M[-1]) >= PROTOCOLO["diferenca_minima_unidades"] and s * (Epub[-1] - Mpub[-1]) >= PROTOCOLO["diferenca_minima_unidades"])
    q["Q9"] = (not disc) or bool(Epub and all(type(v) is int for v in Epub))
    if all(x <= tol for x in gaps):
        st = "LADO_OPOSTO" if any(x < -tol for x in gaps) else "COINCIDE"
    elif not (q["Q1"] and q["Q2"] and q["Q3"] and q["Q4"]):
        st = "IMPLAUSIVEL"
    elif not (q["Q5"] and q["Q6"]):
        st = "CRUZA"
    elif not (q["Q7"] and q["Q8"]):
        st = "COINCIDE"
    elif not q["Q9"]:
        st = "IMPLAUSIVEL"
    else:
        st = "COERENTE"
    q.update({"razao_2030_2025": r, "g_extremo": gE, "g_moderado": gM, "g_2026": g26})
    return st, q


PREC_ESTADO = ["COERENTE", "IMPLAUSIVEL", "CRUZA", "COINCIDE", "LADO_OPOSTO", "SEM_PROJECAO"]
CAUSA_DE_ESTADO = {"COERENTE": "I", "IMPLAUSIVEL": "E", "CRUZA": "C", "COINCIDE": "D", "LADO_OPOSTO": "A2", "SEM_PROJECAO": "F"}


def causa_moderado_ausente(motivo, anos, segs_d):
    """Seção 3.1: causa do primeiro ano que interrompe o segmento, de 2025 para trás."""
    if motivo == "TRAJETORIA_IMPLAUSIVEL_NA_SERIE":
        return "E", "trajetória do Moderado com razão 2030/2025 fora de [0,5; 3]"
    if not anos:
        return "F", "sem registro no contrato para a série"
    for a in reversed(C.ANOS):
        e = anos.get(a)
        if not e:
            return "F", f"{a}: sem registro"
        est, v, rup = e[0], e[1], e[2]
        if est != "observado" or not (v or 0) > 0:
            if est == "nao_homologado":
                return "G", f"{a}: competência não homologada ({e[4] or 'bloqueio'})"
            return "F", f"{a}: {est}" + (f" ({e[4]})" if e[4] else "")
        if rup:
            return "G", f"{a}: ruptura desde o ano anterior ({e[3] or 'sem tipo'})"
    return "J", "segmento completo, mas sem projeção do Moderado"


# ------------------------------------------------------------------ execução
def main(saida):
    t_ini = time.time()
    saida = Path(saida); saida.mkdir(parents=True, exist_ok=True)
    contrato_dir = ENTRADAS["contrato"].parent
    entrada = RAIZ / "motor_cenarios" / "entrada"
    pub = json.loads(ENTRADAS["publicado"].read_text(encoding="utf-8"))
    pubm = {(m["conceito"], m["metrica"]): m for m in pub["metricas"]}
    series, empresas, unidades = C.carregar_contrato(contrato_dir)
    pot, _ = C.carregar_potencia(entrada, series)
    for kk, v in pot.items():
        series[kk] = v; unidades[kk] = "kVA"
    fi = C.internas_por_dist(series, entrada)
    fe, _ = C.externas_por_dist(entrada, entrada)
    motorC = C.Motor(series, fi, fe)
    motorX = OT.MotorX(series, fi, fe)
    # contrato bruto: estado, valor, ruptura, tipo de ruptura, tipo de lacuna, status de homologação
    bruto = defaultdict(dict)
    for r in csv.DictReader(open(ENTRADAS["contrato"], encoding="utf-8")):
        bruto[(r["conceitoId"], r["metrica"], r["dist"])][int(r["ano"])] = (
            r["estado"], float(r["valor"]) if r["valor"] else None, r["ruptura_desde_ano_anterior"] == "true", r["tipo_ruptura"], r["tipo_lacuna"], r["status_homologacao"])
    gj = json.loads(ENTRADAS["grupos"].read_text(encoding="utf-8"))
    grupo = {str(d): g["grupo_id"] for g in gj["grupos"] for d in g["dists"]}
    cat = json.loads(ENTRADAS["conceitos"].read_text(encoding="utf-8"))
    nomes = {a["id"]: (a["nome"], a.get("familia", "")) for a in cat["ativos"]}
    cient = {(r["conceito"], r["metrica"]): r for r in csv.DictReader(open(ENTRADAS["estado_cientifico"], encoding="utf-8")) if r["horizonte"] == "1"}
    otim = defaultdict(list)
    for r in csv.DictReader(open(ENTRADAS["modelos_otimizacao"], encoding="utf-8")):
        if r["origem"] == "otimizado":
            otim[(r["conceito"], r["metrica"])].append(r)
    rng = np.random.default_rng(PROTOCOLO["semente"])
    chaves = sorted(k for k in series if k in pubm and pubm[k]["series"] and (not SO or f"{k[0]}/{k[1]}" in SO))
    chaves.sort(key=lambda k: (k != UC, k))            # consumidores primeiro: N6 usa os extremos de consumidores
    linhas02, linhas03, linhas05, linhas06, reproducao, congelado = [], [], [], [], [], {"protocolo": PROTOCOLO["versao"], "metricas": {}}
    registro = {}                                      # (k, d) -> {lado: {...}} para N6 e para o resumo
    for k in chaves:
        t0 = time.time()
        conc, metr = k
        pm = pubm[k]
        natureza = C.mc.nature_of(unidades.get(k, "")); disc = natureza == "discrete_count"
        kva = metr == "potencia_kva"
        # ---------- O: os 9 modelos originais, reexecutados sem alteração
        segs, bt, prev, _, _ = C.executar_metrica(motorC, k)
        met, cen, _ = C.escolher_cenarios(bt, prev, segs)
        if cen != pm["cenarios"]:
            raise SystemExit(f"ABORTADO {k}: escolha reexecutada {cen} ≠ publicada {pm['cenarios']}")
        dif_wape = max((abs((met[m]["erros"]["wape"] or 0) - (pm["modelos"][m]["wape"] or 0)) for m in met), default=0.0)
        mod_id = cen["moderado"]
        ref = sorted({(h, o, d) for _, _, h, o, d in (bt.get("persistencia") or [])})
        y0_de = lambda key: dict(segs[key[2]])[key[1]]
        cands = {}
        for m, x in met.items():
            pts = {(h, o, d): (y0_de((h, o, d)), y, yh) for y, yh, h, o, d in (bt.get(m) or [])}
            cands[m] = {"id": m, "cat": "O", "algoritmo": m, "variaveis": "|".join(C.PAINEL.get(m, [])), "hiper": "", "complexidade": C.MODELOS[m]["complexidade"],
                        "pts": pts or None, "traj": prev.get(m, {}), "wape_prod": pm["modelos"][m]["wape"], "elegivel": x["elegivel"], "motivo": x["motivo"],
                        "cagr": x["cagr_agregado"], "reproducao": None}
        # reprodução das trajetórias publicadas (tolerância de cenarios.comparar_produtos)
        n_cont, n_folga, n_erro, dmax_cont = 0, 0, 0, 0.0
        for d, s in pm["series"].items():
            for slot in ("conservador", "moderado", "agressivo"):
                if not s.get(slot):
                    continue
                v = publicar(prev[cen[slot]][d], natureza)
                for a, b in zip(v, s[slot]):
                    if disc:
                        n_cont += 1
                        dd = abs(a - b)
                        if dd > 5e-3 * max(abs(a), abs(b)):
                            n_folga += dd <= 1; n_erro += dd > 1
                    else:
                        dmax_cont = max(dmax_cont, abs(a - b))
                        n_erro += abs(a - b) > max(5e-3 * max(abs(a), abs(b)), 1e-4)
        reproducao.append({"conceito": conc, "metrica": metr, "escolha_identica": True, "dif_max_wape_publicado": dif_wape, "contagens_comparadas": n_cont,
                           "contagens_na_folga_1_unidade": n_folga, "divergencias": n_erro, "dif_max_continua": dmax_cont})
        if n_erro:
            raise SystemExit(f"ABORTADO {k}: {n_erro} valores publicados não reproduzidos")
        # ---------- X: configurações da otimização (verificação nos pontos da otimização, depois nos pontos do produto)
        for r in otim.get(k, []):
            nomes_v = [v for v in r["variaveis"].split("|") if v]
            hp = json.loads(r["hiperparametros"])
            av = OT.Avaliador(motorX, k, disc, {})
            S = av.avaliar(r["algoritmo"], nomes_v, hp, 2023, "S"); F = av.avaliar(r["algoritmo"], nomes_v, hp, 2024, "F")
            ok_rep = "wape" in S and "wape" in F and r["S_wape"] and r["F_wape"] and abs(S["wape"] - float(r["S_wape"])) <= 5e-7 and abs(F["wape"] - float(r["F_wape"])) <= 5e-7
            pr = Painel(motorX, k, nomes_v, (lambda a, h: (lambda X, g: OT.ajustar(a, h, X, g)))(r["algoritmo"], hp))
            pts, mot = backtest(segs, pr, ref)
            alvos = {d: s for d, s in segs.items() if len(s) >= 3}
            traj = pr(C.BASE, alvos, 5) or {}
            el, motivo, cagr = plausivel_metrica(traj, segs)
            if not ok_rep:
                el, motivo = False, "REPRODUCAO_FALHOU"
            cands[r["modelo"]] = {"id": r["modelo"], "cat": "X", "algoritmo": r["algoritmo"], "variaveis": "|".join(nomes_v), "hiper": r["hiperparametros"],
                                  "complexidade": C.MODELOS[r["referencia"]]["complexidade"] + 0.5, "pts": pts, "traj": traj, "elegivel": el and pts is not None,
                                  "motivo": motivo or mot, "cagr": cagr, "veredito": r["veredito"],
                                  "reproducao": {"S_wape": S.get("wape"), "S_wape_registrado": r["S_wape"], "F_wape": F.get("wape"), "F_wape_registrado": r["F_wape"], "ok": bool(ok_rep)}}
        # ---------- N1, N2n, N2g: escolha de φ e κ só pelo WAPE da etapa S
        escolhas = {}
        familias = {"N1": [(f"phi={p}", n1(p), 1.5) for p in PROTOCOLO["n1_phi"]],
                    "N2n": [(f"kappa={kp:g}", n2(series, k, kp), 2.5) for kp in PROTOCOLO["n2_kappa"]],
                    "N2g": [(f"kappa={kp:g}", n2(series, k, kp, grupo), 2.6) for kp in PROTOCOLO["n2_kappa"]]}
        for fam, variantes in familias.items():
            res = []
            for nome_v, fn, cx in variantes:
                pts, mot = backtest(segs, fn, ref)
                if pts is None:
                    continue
                wS = estat([(kk[2], *v) for kk, v in pts.items() if etapa_de(kk) == "S"]).get("wape")
                res.append((wS if wS is not None else 9e9, nome_v, fn, cx, pts))
            if not res:
                continue
            wS, nome_v, fn, cx, pts = min(res, key=lambda x: (x[0], x[1]))
            escolhas[fam] = {"variante": nome_v, "wape_S": wS, "alternativas": {x[1]: x[0] for x in res}}
            alvos = {d: s for d, s in segs.items() if len(s) >= 3}
            traj = fn(C.BASE, alvos, 5) or {}
            el, motivo, cagr = plausivel_metrica(traj, segs)
            cands[fam] = {"id": fam, "cat": "N", "algoritmo": fam, "variaveis": "", "hiper": nome_v, "complexidade": cx, "pts": pts, "traj": traj,
                          "elegivel": el, "motivo": motivo, "cagr": cagr}
        # ---------- estatísticas por candidato e etapa (seção 8)
        for c in cands.values():
            c["est"] = {}
            if c["pts"]:
                for et in ("S", "F", "H2"):
                    c["est"][et] = estat([(kk[2], *v) for kk, v in c["pts"].items() if etapa_de(kk) == et])
                c["est"]["PRODUTO"] = estat([(kk[2], *v) for kk, v in c["pts"].items()])
                if c["cat"] != "O":
                    c["wape_prod"] = c["est"]["PRODUTO"]["wape"]
        mod = cands[mod_id]
        w_mod, wF_mod = mod["wape_prod"], mod["est"]["F"]["wape"]
        w_mod_reexec = mod["est"]["PRODUTO"]["wape"]
        for c in cands.values():
            if c["id"] == mod_id:
                c["competitivo"], c["por_que"] = False, "MODERADO_PUBLICADO"
                continue
            if not c["pts"] or not c["elegivel"]:
                c["competitivo"], c["por_que"] = False, c["motivo"] or "BACKTEST_INCOMPLETO"
                continue
            if c["cat"] == "O":
                ok = c["wape_prod"] <= PROTOCOLO["tolerancia_erro"] * w_mod
                c["competitivo"], c["por_que"] = ok, None if ok else "WAPE_ACIMA_DA_TOLERANCIA"
            else:              # X e N: mesma plataforma do Moderado reexecutado e guarda F (escolhas feitas na etapa S)
                ok1 = c["wape_prod"] <= PROTOCOLO["tolerancia_erro"] * w_mod_reexec
                ok2 = c["est"]["F"]["wape"] <= PROTOCOLO["guarda_F"] * wF_mod
                c["competitivo"] = ok1 and ok2
                c["por_que"] = None if c["competitivo"] else ("WAPE_ACIMA_DA_TOLERANCIA" if not ok1 else "GUARDA_F_REPROVADA")
        # ---------- bootstrap por grupo (comparação com baselines e com o Moderado)
        cluster = lambda d: grupo.get(d, f"DIST_{d}")
        for et in ("S", "F", "H2", "PRODUTO"):
            keys = [kk for kk in ref if et == "PRODUTO" or etapa_de(kk) == et]
            if not keys:
                continue
            dists = {kk[2] for kk in keys}
            gs = sorted({cluster(d) for d in dists})
            gi = {g: i for i, g in enumerate(gs)}
            idx = np.array([gi[cluster(kk[2])] for kk in keys])
            yv = np.array([mod["pts"][kk][1] for kk in keys], float)
            cont = None
            if len(dists) >= PROTOCOLO["bootstrap_min_dist"]:
                sorteio = rng.integers(0, len(gs), size=(PROTOCOLO["bootstrap_replicas"], len(gs)))
                cont = np.stack([np.bincount(lin, minlength=len(gs)) for lin in sorteio])
                Yg = np.bincount(idx, weights=np.abs(yv), minlength=len(gs))
            def ag(c):
                e = np.array([abs(c["pts"][kk][2] - c["pts"][kk][1]) for kk in keys], float)
                return np.bincount(idx, weights=e, minlength=len(gs))
            refs = {b: cands[b] for b in ("persistencia", "deriva", "crescimento_geometrico", mod_id) if b in cands and cands[b]["pts"]}
            for c in cands.values():
                if not c["pts"]:
                    continue
                c.setdefault("ic", {})[et] = {}
                for nome_ref, rc in refs.items():
                    if nome_ref == c["id"]:
                        continue
                    if cont is None:
                        c["ic"][et][nome_ref] = None
                        continue
                    a, b = cont @ ag(c), cont @ ag(rc)
                    dif = a / (cont @ Yg) - b / (cont @ Yg)
                    c["ic"][et][nome_ref] = [float(np.percentile(dif, 2.5)), float(np.percentile(dif, 97.5))]
        # robustez por distribuidora (etapa F)
        kF = [kk for kk in ref if etapa_de(kk) == "F"]
        for c in cands.values():
            if not c["pts"] or not kF:
                continue
            melhor = sum(1 for kk in kF if abs(c["pts"][kk][2] - c["pts"][kk][1]) <= abs(mod["pts"][kk][2] - mod["pts"][kk][1]) + 1e-12)
            c["frac_dist_melhor_ou_igual_moderado_F"] = melhor / len(kF)
            por_g = defaultdict(list)
            for kk in kF:
                por_g[cluster(kk[2])].append(kk)
            ws = [sum(abs(c["pts"][kk][2] - c["pts"][kk][1]) for kk in v) / sum(abs(c["pts"][kk][1]) for kk in v) for g, v in por_g.items() if len(v) >= 3]
            c["wape_F_pior_grupo"] = max(ws) if ws else None
        # ---------- N5: quantílico condicional (calibração nas etapas S e F)
        n5 = {}
        for lado, tau in PROTOCOLO["n5_tau"].items():
            pr = Painel(motorC, k, C.FEAT_INT, ajuste_quantil(tau))
            pts, mot = backtest(segs, pr, ref)
            info = {"tau": tau, "pares_S": pr.n_pares.get(2023), "calibrado": False}
            if pts is not None and (pr.n_pares.get(2023) or 0) >= PROTOCOLO["n5_min_pares_S"]:
                for et in ("S", "F"):
                    kk_et = [kk for kk in pts if etapa_de(kk) == et]
                    obs = [math.log(pts[kk][1] / pts[kk][0]) for kk in kk_et]; prv = [math.log(pts[kk][2] / pts[kk][0]) for kk in kk_et]
                    info[f"frac_{et}"] = (sum(o < p for o, p in zip(obs, prv)) if lado == "conservador" else sum(o > p for o, p in zip(obs, prv))) / len(kk_et)
                lo, hi = PROTOCOLO["n5_calibracao"]
                info["calibrado"] = all(lo <= info[f"frac_{et}"] <= hi for et in ("S", "F"))
            else:
                info["motivo"] = mot or f"pares na etapa S < {PROTOCOLO['n5_min_pares_S']}"
            if info["calibrado"]:
                info["traj"] = pr(C.BASE, {d: s for d, s in segs.items() if len(s) >= 3}, 5) or {}
            n5[lado] = info
        # ---------- N6: elasticidade à carga (amostras S e completa; bootstrap por grupo)
        n6 = None
        if [conc, metr] in PROTOCOLO["n6_ativos"]:
            def amostra(ate, so_t=None):
                ga = {(d, t): g for d, t, g in transicoes(series, k, ate) if so_t is None or t == so_t}
                gu = {(d, t): g for d, t, g in transicoes(series, UC, ate) if so_t is None or t == so_t}
                return [(d, gu[(d, t)], ga[(d, t)]) for (d, t) in sorted(set(ga) & set(gu))]
            def beta(am):
                if len(am) < 10:
                    return None, None
                x = np.array([a[1] for a in am]); y = np.array([a[2] for a in am])
                b = float(np.cov(x, y, bias=True)[0, 1] / np.var(x)) if np.var(x) > 0 else None
                gs = sorted({cluster(a[0]) for a in am}); gi = {g: i for i, g in enumerate(gs)}
                idx = np.array([gi[cluster(a[0])] for a in am])
                bs = []
                for lin in rng.integers(0, len(gs), size=(PROTOCOLO["bootstrap_replicas"], len(gs))):
                    sel = np.concatenate([np.flatnonzero(idx == g) for g in lin])
                    vx = np.var(x[sel])
                    bs.append(np.cov(x[sel], y[sel], bias=True)[0, 1] / vx if vx > 0 else np.nan)
                return b, [float(np.nanpercentile(bs, 2.5)), float(np.nanpercentile(bs, 97.5))]
            bS, icS = beta(amostra(2023, 2023)); bT, icT = beta(amostra(2025))
            aprov = bool(bS is not None and bT is not None and 0 < bT <= PROTOCOLO["n6_beta_max"] and bS > 0 and icS[0] > 0 and icT[0] > 0)
            n6 = {"beta_S": bS, "ic95_S": icS, "beta": bT, "ic95": icT, "aprovado": aprov}
        congelado["metricas"][f"{conc}/{metr}"] = {"N_escolhas_S": escolhas, "N5": {l: {kk: v for kk, v in i.items() if kk != "traj"} for l, i in n5.items()}, "N6": n6}
        # ---------- percentis de plausibilidade da métrica
        gs_m = [g for _, _, g in transicoes(series, k, C.BASE)]
        if len(gs_m) >= PROTOCOLO["min_transicoes_metrica"]:
            p01, p99 = np.percentile(gs_m, PROTOCOLO["percentis_modelo"]); p05, p95 = np.percentile(gs_m, PROTOCOLO["percentis_condicional"])
        else:
            p01 = p99 = p05 = p95 = None
        # ---------- por série
        cs = cient.get(k, {})
        ord_p2 = sorted([c for c in cands.values() if c["cat"] in "OX" and c["competitivo"]], key=lambda c: (c["wape_prod"], c["complexidade"], c["id"]))
        ord_p3 = sorted([c for c in cands.values() if c["cat"] == "N" and c["competitivo"]], key=lambda c: (c["wape_prod"], c["complexidade"], c["id"]))
        o_comp = [c for c in cands.values() if c["cat"] == "O" and c["competitivo"]]
        o_eleg = [c for c in cands.values() if c["cat"] == "O" and c["id"] != mod_id and c["elegivel"] and c["pts"]]
        coer = defaultdict(lambda: {"conservador": 0, "agressivo": 0})
        for d, s in sorted(pm["series"].items(), key=lambda x: int(x[0])):
            anos_b = bruto.get((conc, metr, d), {})
            anos_s = series[k].get(d, {})
            padrao = "".join((COD_ESTADO.get(anos_s[a][0], "-") if a in anos_s else "-") + ("R" if a in anos_s and anos_s[a][2] else "") for a in C.ANOS)
            seg = segs.get(d) or []
            n_tr = sum(1 for dd, t, g in transicoes(series, k, C.BASE) if dd == d)
            restr = [f"{a}:{e[5]}" for a, e in sorted(anos_b.items()) if e[5] in ("APTO_COM_RESSALVAS", "PENDENTE_DECISAO", "BLOQUEADO")]
            restr += [f"{a}:ruptura:{e[3]}" for a, e in sorted(anos_b.items()) if e[2]] + [f"{a}:{e[4]}" for a, e in sorted(anos_b.items()) if e[4] and e[4] not in ("ATIVO_NAO_APLICAVEL",)]
            y25 = s["hist"][-1][1] if s["hist"] and s["hist"][-1][0] == C.BASE else None
            Mpub = s.get("moderado")
            base = {"DIST": d, "empresa": empresas.get(d, ""), "grupo": grupo.get(d, ""), "conceito": conc, "ativo": nomes.get(conc, (conc, ""))[0],
                    "familia": nomes.get(conc, ("", ""))[1], "metrica": metr, "unidade": unidades.get(k, ""), "natureza": natureza, "experimental_kva": kva}
            pub_comp = sum(1 for sl in ("conservador", "moderado", "agressivo") if s.get(sl))
            linha = {**base, "padrao_estados_2022_2025": padrao, "segmento_contiguo": "-".join(str(a) for a, _ in seg), "transicoes_comparaveis": n_tr,
                     "restricoes_qualidade": "|".join(dict.fromkeys(restr)), "y_2025": y25,
                     "moderado_modelo": mod_id if Mpub else "", "moderado_2030": Mpub[-1] if Mpub else "",
                     "completude_publicada": "COMPLETA" if pub_comp == 3 else "PARCIAL" if pub_comp else "SEM_PREVISAO",
                     "wape_moderado_metrica": w_mod, "wape_moderado_F": wF_mod, "r2_crescimento_moderado_F": mod["est"]["F"].get("r2_crescimento"),
                     "mdape_moderado_serie": s.get("erro_moderado"),
                     "ape_moderado_F_serie": (lambda kk: abs(mod["pts"][kk][2] - mod["pts"][kk][1]) / mod["pts"][kk][1] if kk in mod["pts"] else "")((1, 2024, d)),
                     "estado_cientifico_moderado_h1": cs.get("estado_cientifico", ""),
                     "competitivos_originais": "|".join(c["id"] for c in o_comp), "competitivos_otimizados": "|".join(c["id"] for c in ord_p2 if c["cat"] == "X")}
            if not Mpub or not y25:
                mot = (s.get("motivos") or {}).get("moderado", "")
                cod, txt = causa_moderado_ausente(mot, anos_b if not kva else {a: (e[0], e[1], e[2], "", "", "") for a, e in anos_s.items()}, seg)
                rec = "IRRECUPERAVEL_" + cod
                if len(seg) == 2 and mod_id in C.PAINEL:
                    rec = "MODERADO_RECUPERAVEL_SOB_DECISAO_DE_CONTRATO"
                linha.update({"causa_moderado": cod, "causa_moderado_detalhe": txt})
                for lado in LADOS:
                    linha.update({f"{lado}_publicado_modelo": "", f"{lado}_publicado_2030": "", f"{lado}_estado_publicado": "", f"causa_{lado}": "H",
                                  f"causa_{lado}_detalhe": f"sem Moderado publicado (causa {cod})", f"{lado}_final_etapa": "", f"{lado}_final_categoria": "INDISPONIVEL",
                                  f"{lado}_final_modelo": "", f"{lado}_final_2030": "", f"{lado}_gateB_etapa": "", f"causa_final_{lado}": "H"})
                linha.update({"completude_defensavel_antes": "SEM_PREVISAO", "classe_gateB": "SEM_PREVISAO", "classe_gateB_so_originais": "SEM_PREVISAO",
                              "classe_gateB_originais_e_otimizados": "SEM_PREVISAO", "classe_final": "SEM_PREVISAO", "possibilidade_recuperacao": rec,
                              "estado_cientifico_extremos": "nao_aplicavel"})
                linhas02.append(linha)
                registro[(k, d)] = {"classe_final": "SEM_PREVISAO"}
                continue
            M = prev[mod_id][d]
            reg = {}
            for lado in LADOS:
                tentativas = []                                   # (etapa, candidato, estado, q, E, Epub)
                pub_m = cen[lado] if s.get(lado) else None
                def tentar(etapa, cid, E, Epub=None):
                    if E is not None and Epub is None and all(math.isfinite(v) and v >= 0 for v in E):
                        Epub = publicar(E, natureza)
                    st, q = checar(E, Epub, M, Mpub, y25, lado, disc, p01, p99)
                    tentativas.append((etapa, cid, st, q, E, Epub))
                    return st
                if pub_m:
                    tentar("P1", pub_m, prev[pub_m].get(d), s[lado])
                for c in ord_p2:
                    tentar("P2", c["id"], c["traj"].get(d))
                for c in ord_p3:
                    tentar("P3", c["id"], c["traj"].get(d))
                # P4 B-HIST
                gh = [g for dd, t, g in transicoes(series, k, C.BASE) if dd == d]
                if len(gh) >= PROTOCOLO["min_transicoes_condicional"] and p05 is not None:
                    gc = min(gh) if lado == "conservador" else max(gh)
                    if p05 <= gc <= p95:
                        tentar("P4", "B_HIST", [y25 * math.exp(h * gc) for h in range(1, 6)])
                    else:
                        tentativas.append(("P4", "B_HIST", "FORA_P05_P95", {"g": gc}, None, None))
                else:
                    tentativas.append(("P4", "B_HIST", "TRANSICOES_INSUFICIENTES", {"n": len(gh)}, None, None))
                reg[lado] = tentativas
            # P5 N6 usa os extremos de consumidores (categoria A) — resolvido após P1–P4 desta série
            linha_reg = {}
            for lado in LADOS:
                tent = reg[lado]
                if n6 and n6["aprovado"]:
                    ucr = registro.get((UC, d), {}).get(lado)
                    if ucr and ucr["categoria"].startswith("A") and ucr.get("E_cont") and ucr.get("M_cont"):
                        E = [m_ * (ue / um) ** n6["beta"] for m_, ue, um in zip(M, ucr["E_cont"], ucr["M_cont"])]
                        Epub = publicar(E, natureza) if all(math.isfinite(v) and v >= 0 for v in E) else None
                        st, q = checar(E, Epub, M, Mpub, y25, lado, disc, p01, p99)
                        tent.append(("P5", "N6_ELASTICIDADE", st, q, E, Epub))
                    else:
                        tent.append(("P5", "N6_ELASTICIDADE", "SEM_EXTREMO_A_DE_CONSUMIDORES", {}, None, None))
                if n5[lado]["calibrado"]:
                    E = n5[lado]["traj"].get(d)
                    Epub = publicar(E, natureza) if E and all(math.isfinite(v) and v >= 0 for v in E) else None
                    st, q = checar(E, Epub, M, Mpub, y25, lado, disc, p01, p99)
                    tent.append(("P6", f"N5_QUANTIL_{PROTOCOLO['n5_tau'][lado]}", st, q, E, Epub))
                def escolhe(etapas):
                    for t in tent:
                        if t[0] in etapas and t[2] == "COERENTE":
                            return t
                    return None
                final = escolhe(("P1", "P2", "P3", "P4", "P5", "P6"))
                gateB = escolhe(("P1", "P2", "P4"))
                gateB_o = next((t for t in tent if t[0] in ("P1", "P2") and t[2] == "COERENTE" and (t[0] == "P1" or cands[t[1]]["cat"] == "O")), None)
                gateB_ox = escolhe(("P1", "P2"))
                def categoria(t):
                    if not t: return "INDISPONIVEL"
                    if t[0] == "P1": return "A_PUBLICADO_MANTIDO"
                    if t[0] == "P2": return "A_ORIGINAL" if cands[t[1]]["cat"] == "O" else "A_OTIMIZADO"
                    if t[0] == "P3": return "A_NOVO"
                    return {"P4": "B_HIST", "P5": "B_ELASTICIDADE", "P6": "B_QUANTIL"}[t[0]]
                # causa (antes): só os originais, critério do produto (seção 3.2)
                p1 = next((t for t in tent if t[0] == "P1"), None)
                if p1:
                    causa = "PUBLICADO_APROVADO" if p1[2] == "COERENTE" else "PUBLICADO_REPROVADO_" + CAUSA_DE_ESTADO[p1[2]]
                    det = f"{p1[1]}: {p1[2]}"
                elif pm["cenarios"][lado]:
                    mot = (s.get("motivos") or {}).get(lado, "")
                    causa, det = ("E", "removido por implausibilidade na série") if mot == "TRAJETORIA_IMPLAUSIVEL_NA_SERIE" else ("F", mot or "sem projeção na série")
                elif not o_eleg:
                    causa, det = "A1", "nenhum outro modelo original elegível na métrica"
                elif not o_comp:
                    causa, det = "B", f"{len(o_eleg)} elegíveis, nenhum com WAPE ≤ 1,25 × o do Moderado"
                else:
                    sts = [t for t in tent if t[0] == "P2" and cands[t[1]]["cat"] == "O"]
                    best = min(sts, key=lambda t: PREC_ESTADO.index(t[2])) if sts else None
                    causa = CAUSA_DE_ESTADO[best[2]] if best else "F"
                    det = "; ".join(f"{t[1]}:{t[2]}" for t in sts)
                # causa final (depois): melhor estado entre todos os candidatos de modelo testados
                if final:
                    causa_f = "RECUPERADO" if not p1 or p1[2] != "COERENTE" else "PUBLICADO_APROVADO"
                else:
                    sts = [t for t in tent if t[0] in ("P1", "P2", "P3")]
                    if sts:
                        causa_f = CAUSA_DE_ESTADO[min(sts, key=lambda t: PREC_ESTADO.index(t[2]))[2]]
                    elif not [c for c in cands.values() if c["id"] != mod_id and c["elegivel"] and c["pts"]]:
                        causa_f = "A1"
                    else:
                        causa_f = "B"
                cat_f = categoria(final)
                for t in tent:
                    if t[0] in ("P2", "P3") and t[2] == "COERENTE":
                        coer[t[1]][lado] += 1
                linha_reg[lado] = {"categoria": cat_f, "etapa": final[0] if final else "", "modelo": final[1] if final else "", "E_cont": final[4] if final else None,
                                   "M_cont": M, "gateB": categoria(gateB), "gateB_o": categoria(gateB_o), "gateB_ox": categoria(gateB_ox)}
                linha.update({f"{lado}_publicado_modelo": pub_m or "", f"{lado}_publicado_2030": s[lado][-1] if s.get(lado) else "",
                              f"{lado}_estado_publicado": p1[2] if p1 else "", f"causa_{lado}": causa, f"causa_{lado}_detalhe": det,
                              f"{lado}_final_etapa": final[0] if final else "", f"{lado}_final_categoria": cat_f, f"{lado}_final_modelo": final[1] if final else "",
                              f"{lado}_final_2030": final[5][-1] if final else "", f"{lado}_gateB_etapa": gateB[0] if gateB else "", f"causa_final_{lado}": causa_f,
                              # gabarito por opção de integração (09): só originais, originais + otimizados, Gate B completo
                              **{f"{lado}_{op}_{campo}": (t[1] if campo == "modelo" else t[5][-1]) if t else ""
                                 for op, t in (("so_originais", gateB_o), ("originais_otimizados", gateB_ox), ("gateB", gateB)) for campo in ("modelo", "2030")}})
                for t in tent:
                    if t[0] == "P1" or t is final:
                        q = t[3]
                        linhas06.append({**base, "lado": lado, "origem_extremo": "PUBLICADO" if t[0] == "P1" else "FINAL_" + t[0], "candidato": t[1], "estado": t[2],
                                         **{qq: q.get(qq) for qq in ("Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "Q9")},
                                         "razao_2030_2025": q.get("razao_2030_2025"), "g_extremo": q.get("g_extremo"), "g_moderado": q.get("g_moderado"), "g_2026": q.get("g_2026"),
                                         "p01": p01, "p99": p99, "y_2025": y25, "moderado_2026": Mpub[0], "moderado_2030": Mpub[-1],
                                         "extremo_2026": t[5][0] if t[5] else "", "extremo_2030": t[5][-1] if t[5] else "", "selecionado": t is final,
                                         "estados_testados": "|".join(f"{x[0]}:{x[1]}:{x[2]}" for x in tent)})
            def classe(cats):
                a = [c for c in cats if c.startswith("A")]; b = [c for c in cats if c.startswith("B")]
                if len(a) + len(b) < 2:
                    return "PARCIAL"
                return "COMPLETA_INDEPENDENTE" if len(a) == 2 else "COMPLETA_MISTA" if a else "COMPLETA_CONDICIONAL"
            cl_f = classe([linha_reg[l]["categoria"] for l in LADOS])
            cl_b = classe([linha_reg[l]["gateB"] for l in LADOS])
            ok_antes = all(linha.get(f"{l}_estado_publicado") == "COERENTE" for l in LADOS)
            linha.update({"causa_moderado": "", "causa_moderado_detalhe": "",
                          "completude_defensavel_antes": "COMPLETA" if ok_antes else "PARCIAL", "classe_gateB": cl_b,
                          "classe_gateB_so_originais": classe([linha_reg[l]["gateB_o"] for l in LADOS]),
                          "classe_gateB_originais_e_otimizados": classe([linha_reg[l]["gateB_ox"] for l in LADOS]),
                          "classe_final": cl_f,
                          "possibilidade_recuperacao": ("JA_COMPLETA_E_DEFENSAVEL" if ok_antes else "RECUPERADA" if cl_f.startswith("COMPLETA") else
                                                        "PARCIAL_" + "+".join(sorted({linha[f"causa_final_{l}"] for l in LADOS if linha_reg[l]["categoria"] == "INDISPONIVEL"}))),
                          "estado_cientifico_extremos": "|".join(sorted({("simulacao_condicional" if linha_reg[l]["categoria"].startswith("B") else
                                                                          "simulacao_comparada_retrospectivamente_experimental") for l in LADOS if linha_reg[l]["categoria"] != "INDISPONIVEL"}))})
            linhas02.append(linha)
            registro[(k, d)] = {**linha_reg, "classe_final": cl_f}
        # ---------- inventário (03) e comparação (05)
        mod_cagr = cands[mod_id]["cagr"]
        for c in cands.values():
            if c["id"] == mod_id:
                classe_c = "MODERADO_PUBLICADO"
            elif not c["pts"] or (c.get("reproducao") and not c["reproducao"]["ok"]):
                classe_c = "SEM_EVIDENCIA_SUFICIENTE"
            elif not c["competitivo"]:
                classe_c = "REJEITADO"
            else:
                nac = c["cagr"] is not None and mod_cagr is not None and abs(c["cagr"] - mod_cagr) >= PROTOCOLO["diferenca_minima_ano"]
                dist_ok = coer[c["id"]]["conservador"] + coer[c["id"]]["agressivo"] > 0
                classe_c = "|".join(([("VALIDO_PARA_MEDIA_NACIONAL")] if nac else []) + (["VALIDO_NA_DISTRIBUIDORA"] if dist_ok else [])) or "VALIDO_APENAS_RETROSPECTIVAMENTE"
            linhas03.append({"conceito": conc, "metrica": metr, "familia": nomes.get(conc, ("", ""))[1], "candidato": c["id"], "categoria": c["cat"],
                             "algoritmo": c["algoritmo"], "variaveis": c["variaveis"], "hiperparametros": c["hiper"],
                             "origem_resultado": {"O": "cenarios.py (reexecutado, sem alteração)", "X": "otimizar.py @997c4d7 (reexecutado)", "N": "recuperar.py (novo, recuperacao-1)"}[c["cat"]],
                             "reproducao_ok": (c["reproducao"]["ok"] if c.get("reproducao") else (dif_wape < 1e-9 if c["cat"] == "O" else "")),
                             "elegivel_produto": c["elegivel"], "motivo_inelegivel": c["motivo"] or "", "competitivo": c["competitivo"], "motivo_nao_competitivo": c.get("por_que") or "",
                             "veredito_otimizacao": c.get("veredito", ""), "wape_produto": c["wape_prod"], "wape_S": c["est"].get("S", {}).get("wape"),
                             "wape_F": c["est"].get("F", {}).get("wape"), "wape_H2": c["est"].get("H2", {}).get("wape"),
                             "r2_crescimento_F": c["est"].get("F", {}).get("r2_crescimento"), "cagr_agregado_2025_2030": c["cagr"],
                             "series_coerentes_conservador": coer[c["id"]]["conservador"], "series_coerentes_agressivo": coer[c["id"]]["agressivo"], "classe": classe_c})
            for et, e in c["est"].items():
                ic = (c.get("ic") or {}).get(et, {})
                linhas05.append({"conceito": conc, "metrica": metr, "candidato": c["id"], "categoria": c["cat"], "etapa": et, **{x: e.get(x) for x in
                                 ("n", "wape", "mae", "rmse", "vies", "r2_estoque", "r2_crescimento", "r2_variacao", "wape_expansao", "wape_sem_outliers")},
                                 "moderado": c["id"] == mod_id, "competitivo": c["competitivo"],
                                 **{f"ic95_dif_wape_vs_{nm}": (json.dumps([round(v, 6) for v in ic[nm]]) if ic.get(nm) else "") for nm in ("persistencia", "deriva", "crescimento_geometrico")},
                                 "ic95_dif_wape_vs_moderado": json.dumps([round(v, 6) for v in ic[mod_id]]) if ic.get(mod_id) else "",
                                 "frac_dist_melhor_ou_igual_moderado_F": c.get("frac_dist_melhor_ou_igual_moderado_F") if et == "F" else "",
                                 "wape_F_pior_grupo": c.get("wape_F_pior_grupo") if et == "F" else ""})
        linhas03.append({"conceito": conc, "metrica": metr, "familia": nomes.get(conc, ("", ""))[1], "candidato": "B_HIST", "categoria": "B-HIST",
                         "algoritmo": "regra condicional (otimização 6.4, guardas recuperacao-1)", "classe": "REGRA_CONDICIONAL"})
        for lado, i in n5.items():
            linhas03.append({"conceito": conc, "metrica": metr, "familia": nomes.get(conc, ("", ""))[1], "candidato": f"N5_QUANTIL_{i['tau']}", "categoria": "N5",
                             "algoritmo": "QuantileRegressor (highs, alpha=0)", "variaveis": "|".join(C.FEAT_INT),
                             "hiperparametros": json.dumps({k_: i.get(k_) for k_ in ("tau", "pares_S", "frac_S", "frac_F")}), "classe": "CONDICIONAL_CALIBRADO" if i["calibrado"] else "CONDICIONAL_NAO_CALIBRADO"})
        if n6:
            linhas03.append({"conceito": conc, "metrica": metr, "familia": nomes.get(conc, ("", ""))[1], "candidato": "N6_ELASTICIDADE", "categoria": "N6",
                             "algoritmo": "MQO g_ativo ~ g_UC", "hiperparametros": json.dumps({k_: n6[k_] for k_ in ("beta_S", "ic95_S", "beta", "ic95")}),
                             "classe": "CONDICIONAL_APROVADO" if n6["aprovado"] else "CONDICIONAL_REPROVADO"})
        for pid in ("H_G_HIER_rede_bt", "H_G_RIDGE_kva"):
            if (pid.endswith("rede_bt") and conc == "rede_bt") or (pid.endswith("kva") and k == ("trafo_dist", "potencia_kva")):
                linhas03.append({"conceito": conc, "metrica": metr, "familia": nomes.get(conc, ("", ""))[1], "candidato": pid, "categoria": "H",
                                 "algoritmo": "piloto granular (conjunto × ano), configuração congelada 9be843b", "classe": "NAO_APLICAVEL_AO_PAINEL_DIST"})
        print(f"{conc}/{metr}: {time.time() - t0:.1f}s; competitivos O/X/N = {sum(1 for c in cands.values() if c['competitivo'] and c['cat'] == 'O')}/"
              f"{sum(1 for c in cands.values() if c['competitivo'] and c['cat'] == 'X')}/{sum(1 for c in cands.values() if c['competitivo'] and c['cat'] == 'N')}", flush=True)
    # ------------------------------------------------------------------ arquivos
    def wcsv(nome, rows):
        campos = list(dict.fromkeys(c for r in rows for c in r))
        with open(saida / nome, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=campos, lineterminator="\n"); w.writeheader()
            for r in rows:
                w.writerow({c: (round(v, 6) if isinstance(v, float) and math.isfinite(v) else ("" if isinstance(v, float) else v)) for c, v in r.items()})
    wcsv("02_MATRIZ_SERIES_CENARIOS.csv", linhas02)
    wcsv("03_INVENTARIO_MODELOS_EXISTENTES.csv", linhas03)
    wcsv("05_COMPARACAO_RETROSPECTIVA.csv", linhas05)
    wcsv("06_AUDITORIA_PLAUSIBILIDADE.csv", linhas06)
    wcsv("REPRODUCAO.csv", reproducao)
    cobertura(linhas02, saida, wcsv)
    txt = json.dumps(congelado, ensure_ascii=False, indent=1, sort_keys=True, default=float)
    (saida / "selecao_congelada.json").write_text(txt, encoding="utf-8", newline="\n")
    (saida / "selecao_congelada.sha256").write_text(hashlib.sha256(txt.encode("utf-8")).hexdigest() + "\n", encoding="utf-8")
    import scipy
    import sklearn
    man = {"protocolo": PROTOCOLO, "entradas_sha256": {n: sha(p) for n, p in ENTRADAS.items()}, "codigo_sha256": {"recuperar.py": sha(__file__),
           "cenarios.py": sha(RAIZ / "motor_cenarios/cenarios.py"), "otimizar.py": sha(RAIZ / "motor_cenarios/otimizacao/otimizar.py")},
           "ambiente": {"python": sys.version.split()[0], "numpy": np.__version__, "scipy": scipy.__version__, "scikit_learn": sklearn.__version__, "plataforma": platform.platform()},
           "metricas": len(chaves), "series": len(linhas02), "segundos": round(time.time() - t_ini, 1),
           "saidas_sha256": {p.name: sha(p) for p in sorted(saida.glob("*.csv"))}}
    (saida / "MANIFESTO.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(f"OK: {len(linhas02)} séries, {time.time() - t_ini:.0f}s")


def cobertura(linhas, saida, wcsv):
    """07: antes e depois por nível (nacional, empresa, métrica, família), com e sem kVA."""
    def conta(rs):
        c = Counter()
        for r in rs:
            c["series"] += 1
            c["antes_publicado_" + r["completude_publicada"]] += 1
            c["antes_defensavel_COMPLETA"] += r["completude_defensavel_antes"] == "COMPLETA"
            for et in ("classe_gateB_so_originais", "classe_gateB_originais_e_otimizados", "classe_gateB", "classe_final"):
                v = r.get(et) or r["classe_final"]
                c[f"{et}_{'COMPLETA' if v.startswith('COMPLETA') else v}"] += 1
            c["final_" + r["classe_final"]] += 1
            c["moderado_recuperavel_sob_decisao"] += r["possibilidade_recuperacao"] == "MODERADO_RECUPERAVEL_SOB_DECISAO_DE_CONTRATO"
            for lado in LADOS:
                cat = r.get(f"{lado}_final_categoria", "")
                c[f"extremos_final_{cat}"] += 1
                cp = r.get(f"causa_{lado}", "")
                if cp.startswith("PUBLICADO_REPROVADO"):
                    c["extremos_publicados_reprovados"] += 1
                if cat == "INDISPONIVEL":
                    c[f"extremos_bloqueados_causa_{r.get(f'causa_final_{lado}', '')}"] += 1
        return c
    rows = []
    for nivel, chave in (("nacional", lambda r: "todas"), ("nacional_sem_kva", lambda r: "todas" if not r["experimental_kva"] else None),
                         ("empresa", lambda r: f"{r['DIST']} {r['empresa']}"), ("metrica", lambda r: f"{r['conceito']}/{r['metrica']}"), ("familia", lambda r: r["familia"])):
        grupos = defaultdict(list)
        for r in linhas:
            kk = chave(r)
            if kk is not None:
                grupos[kk].append(r)
        for kk, rs in sorted(grupos.items()):
            rows.append({"nivel": nivel, "chave": kk, **conta(rs)})
    campos = sorted({c for r in rows for c in r if c not in ("nivel", "chave")})
    wcsv("07_COBERTURA_ANTES_DEPOIS.csv", [{"nivel": r["nivel"], "chave": r["chave"], **{c: r.get(c, 0) for c in campos}} for r in rows])


if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore", category=UserWarning)
    main(sys.argv[1])
