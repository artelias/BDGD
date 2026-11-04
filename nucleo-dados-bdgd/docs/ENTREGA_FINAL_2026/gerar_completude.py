"""Gera 14_COMPLETUDE_CENARIOS.csv: por produto, distribuidora, ativo e métrica, quantos cenários estão publicados e por quê faltam.

    python docs/ENTREGA_FINAL_2026/gerar_completude.py

Lê só os produtos publicados no repositório (web/public/data/previsoes/cenarios-motor.json e web/data-motor-v2); não recalcula nada.
Estados: COMPLETA (3 cenários), PARCIAL (Moderado sem um ou os dois extremos), SEM_PREVISAO (nenhum cenário publicável)."""
import collections
import csv
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SAIDA = Path(__file__).parent / "14_COMPLETUDE_CENARIOS.csv"
PUB = ("conservador", "moderado", "agressivo")
V2 = ("Conservador", "Moderado", "Agressivo")
MOTIVOS = {
    "TRAJETORIA_IMPLAUSIVEL_NA_SERIE": "trajetória 2030/2025 fora de [0,5; 3] nesta distribuidora",
    "HISTORICO_CONTIGUO_INSUFICIENTE": "menos de três anos contíguos comparáveis",
    "MODELO_SEM_PROJECAO_NA_SERIE": "o modelo do cenário não projeta esta distribuidora",
    "SEM_MODERADO_NA_SERIE": "sem Moderado publicável: extremo não é publicado sozinho",
}


def estado(pub, mod):
    return "COMPLETA" if len(pub) == 3 else "PARCIAL" if mod in pub else "SEM_PREVISAO"


def linhas():
    p = json.loads((RAIZ / "web/public/data/previsoes/cenarios-motor.json").read_text(encoding="utf-8"))
    for m in p["metricas"]:
        for d, s in sorted(m["series"].items(), key=lambda x: int(x[0])):
            pub = [c for c in PUB if s.get(c)]
            falta = {c: (m["justificativas"][c].replace("Indisponível: ", "") if not m["cenarios"][c] else MOTIVOS.get((s.get("motivos") or {}).get(c), "sem trajetória"))
                     for c in PUB if c not in pub}
            yield dict(produto="publico_cenarios_motor", DIST=d, empresa=p["empresas"].get(d, ""), ativo=m["conceito"], metrica=m["metrica"],
                       completude=estado(pub, "moderado"), cenarios_publicados="|".join(pub), n_publicados=len(pub),
                       motivos_nao_publicados=" | ".join(f"{c}: {t}" for c, t in falta.items()))
    for f in sorted((RAIZ / "web/data-motor-v2/distribuidoras").glob("*.json"), key=lambda x: int(x.stem)):
        dj = json.loads(f.read_text(encoding="utf-8"))
        for s in dj["series"]:
            if not s["cenarios"] and s["estado"] != "BLOQUEIO_PLAUSIBILIDADE":
                continue                     # sem previsão por estado da série (sucessão, não aplicável...): fora da contagem de cenários
            c = s["completude_cenarios"]
            yield dict(produto="motor_v2_homologacao", DIST=dj["dist"], empresa=dj["empresa"], ativo=s["objetivo"], metrica=s["metrica"],
                       completude=c["estado"], cenarios_publicados="|".join(c["publicados"]), n_publicados=len(c["publicados"]),
                       motivos_nao_publicados=" | ".join(f"{k}: {v}" for k, v in c["nao_publicados"].items()))


def main():
    rows = list(linhas())
    with open(SAIDA, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n"); w.writeheader(); w.writerows(rows)
    tot = collections.Counter((r["produto"], r["completude"]) for r in rows)
    por = collections.defaultdict(collections.Counter)
    for r in rows:
        por[(r["produto"], r["ativo"], r["metrica"])][r["completude"]] += 1
    print(json.dumps({"total": {f"{a}|{b}": n for (a, b), n in sorted(tot.items())},
                      "por_metrica": {"|".join(k): dict(v) for k, v in sorted(por.items())}}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
