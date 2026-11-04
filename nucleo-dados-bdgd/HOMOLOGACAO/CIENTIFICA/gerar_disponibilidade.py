"""Gera 02_DISPONIBILIDADE_HISTORICA.csv a partir do inventário do catálogo ANEEL já coletado (sem novo download).

    python HOMOLOGACAO/CIENTIFICA/gerar_disponibilidade.py <arcgis_gdb_raw.json> <saida_csv>

Para cada distribuidora e competência (data-base) publicada: quantas versões o catálogo lista, a data de geração de cada arquivo
(carimbo AAAAMMDD-HHMM do nome), a data de criação do item no portal e a defasagem entre a competência e a geração.
O carimbo de geração é a melhor evidência disponível de QUANDO a informação foi produzida; a criação do item no portal só diz quando
o arquivo foi (re)carregado. Nenhum dos dois comprova a data em que a versão ficou publicamente disponível."""
import collections
import csv
import datetime as dt
import json
import re
import sys

PAT = re.compile(r"^(?P<emp>.*)_(?P<dist>\d+)_(?P<ano>\d{4})-(?P<mes>\d{2})-(?P<dia>\d{2})(?:_(?P<mod>[MV]\d+))?(?:_(?P<ger>\d{8})-(?P<hora>\d{4}))?")
JANELA_PRIMEIRA_PUBLICACAO_DIAS = 400     # geração até ~13 meses após a data-base: compatível com o envio regular (não revisão tardia)


def main(raw, saida):
    j = json.load(open(raw, encoding="utf-8"))
    por = collections.defaultdict(list)
    for it in j["itens"]:
        m = PAT.match(it["title"] or it["name"])
        if not m:
            continue
        base = dt.date(int(m["ano"]), int(m["mes"]), int(m["dia"]))
        ger = dt.datetime.strptime(m["ger"], "%Y%m%d").date() if m["ger"] else None
        criado = dt.datetime.fromtimestamp(int(it["created"]) / 1000, dt.timezone.utc).date()
        por[(int(m["dist"]), base)].append(dict(empresa=m["emp"], modulo=m["mod"] or "", geracao=ger, criado_portal=criado, item=it["id"]))
    linhas = []
    for (d, base), vs in sorted(por.items()):
        gers = sorted(v["geracao"] for v in vs if v["geracao"])
        prim = gers[0] if gers else None
        defas = (prim - base).days if prim else None
        linhas.append(dict(
            DIST=d, empresa=vs[0]["empresa"], competencia=base.isoformat(), ano=base.year, versoes_no_catalogo=len(vs),
            modulos="|".join(sorted({v["modulo"] for v in vs if v["modulo"]})),
            geracao_mais_antiga=prim.isoformat() if prim else "", geracao_mais_recente=gers[-1].isoformat() if gers else "",
            defasagem_geracao_dias=defas if defas is not None else "",
            criado_portal_min=min(v["criado_portal"] for v in vs).isoformat(), criado_portal_max=max(v["criado_portal"] for v in vs).isoformat(),
            vintage_compativel_com_envio_regular=bool(defas is not None and 0 <= defas <= JANELA_PRIMEIRA_PUBLICACAO_DIAS),
            disponibilidade_publica_na_epoca_comprovada=False,
            situacao=("ANTERIOR_A_2022_NAO_PROCESSADA" if base.year < 2022 else "PROCESSADA_NO_NUCLEO") ,
        ))
    with open(saida, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]), lineterminator="\n"); w.writeheader(); w.writerows(linhas)
    resumo = collections.defaultdict(lambda: collections.Counter())
    for r in linhas:
        resumo[r["ano"]]["dist"] += 1
        resumo[r["ano"]]["vintage_regular"] += r["vintage_compativel_com_envio_regular"]
        resumo[r["ano"]]["multiplas_versoes"] += r["versoes_no_catalogo"] > 1
    print(json.dumps({a: dict(c) for a, c in sorted(resumo.items())}, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:3])
