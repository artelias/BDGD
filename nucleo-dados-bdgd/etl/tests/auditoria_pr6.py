"""Auditoria independente dos agregados versionados; não abre nem altera GDB/checkpoint.

Usa csv/DictReader e statistics.linear_regression, independentes do gerador JS.
Execute da raiz nucleo-dados-bdgd: python etl/tests/auditoria_pr6.py
"""
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import linear_regression

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "web/public/data"


def carregar(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def auditoria():
    inventario = carregar(ROOT / "auditoria/fase4/MATRIZ_CONFORMIDADE_BDGD_ORDINARIA.csv")
    audit = json.loads((DATA / "historico/publicacoes-auditadas.json").read_text())
    origem = {r["item_id"]: r for r in inventario}
    assert len(origem) == len(audit["items"]) == 414
    for ano, dist, empresa, item, uso, fnl, base, versao, decisao, recomendacao, intervalo in audit["items"]:
        r = origem[item]
        assert (ano, dist, empresa, uso, fnl, base, versao, decisao, recomendacao, intervalo) == (
            int(r["ano_alvo"]), int(r["dist"]), r["empresa"], r["uso_na_serie"], r["DAT_FNL"],
            r["data_base_titulo"], r["versao_titulo"], r["DECISAO_HUMANA"], r["recomendacao"], r["classe_intervalo"])
    status = Counter(r[4] for r in audit["items"])
    assert status["par_divergente_pendente"] == 26
    assert status["excluido_competencia"] + status["par_item_excluido_competencia"] == 14

    pares = json.loads((DATA / "historico/pares-divergentes.json").read_text())
    decis = carregar(ROOT / "auditoria/fase4/DECISOES_DUPLICATAS_13_PARES.csv")
    for p in pares["pares"]:
        fonte = [r for r in decis if (int(r["dist"]), int(r["ano"])) == (p["dist"], p["ano"])]
        assert len(fonte) == 25 and p["decisao"] == "PENDENTE"
        assert all((r["item_A"], r["item_B"], r["DECISAO_HUMANA"]) == (p["itemA"], p["itemB"], "PENDENTE") for r in fonte)
        diferentes = sorted(r["ativo"] for r in fonte if r["valor_A"] != r["valor_B"])
        assert diferentes == sorted(p["ativosDiferentes"])
    assert len(pares["pares"]) == 13 and not pares["selecionadaAutomaticamente"]

    contrato_path = ROOT / "output-historico/contrato-integracao/serie_fisica_nacional.csv"
    contrato = carregar(contrato_path)
    faltantes = sorted({(int(r["ano"]), int(r["dist"]), r["empresa"]) for r in contrato if r["tipo_lacuna"] == "PUBLICACAO_NAO_LOCALIZADA"})
    assert faltantes == sorted(map(tuple, audit["publicacoesNaoLocalizadas"]))
    assert len(faltantes) == 11
    estados = json.loads((DATA / "historico/estados-contrato.json").read_text())
    assert sum(map(len, estados["celulas"].values())) == len(contrato) == 11400
    for conceito, linhas in estados["celulas"].items():
        original = {(int(r["dist"]), int(r["ano"])): r for r in contrato if r["conceitoId"] == conceito}
        for dist, ano, estado, causa, nao_somar in linhas:
            r = original[dist, ano]
            assert (estado, causa, nao_somar) == (r["estado"], r["tipo_lacuna"], r["nao_somar_em_agregados"] == "true")

    pacote = json.loads((DATA / "previsoes/cenarios-exploratorios-2026-2030.json").read_text())
    grupos = defaultdict(list)
    for r in contrato:
        grupos[tuple(r[k] for k in ["dist", "conceitoId", "metrica", "unidade", "perimetroId", "regraVersao"])].append(r)
    elegiveis = {}
    for chave, linhas in grupos.items():
        pontos = sorted(linhas, key=lambda r: int(r["ano"]))
        if len(pontos) != 4 or [int(r["ano"]) for r in pontos] != [2022, 2023, 2024, 2025]:
            continue
        if any(r["estado"] not in {"observado", "zero_verificado"} or r["cobertura"] != "1" or
               r["ruptura_desde_ano_anterior"] == "true" or r["nao_somar_em_agregados"] == "true" or
               r["perimetroBridgeId"] for r in pontos):
            continue
        elegiveis[int(chave[0]), chave[1]] = pontos
    assert len(elegiveis) == len(pacote["series"]) == 1555
    assert len({s[0] for s in pacote["series"]}) == 71
    assert len({s[2] for s in pacote["series"]}) == 25
    for s in pacote["series"]:
        pontos = elegiveis[s[0], s[2]]
        valores = [float(r["valor"]) for r in pontos]
        assert valores == s[5]
        assert [r["publicacao_id"] for r in pontos] == s[8]
        assert [r["status_homologacao"] for r in pontos] == s[9]
        assert ["Z" if r["estado"] == "zero_verificado" else "O" for r in pontos] == s[10]
        slope, intercept = linear_regression([2022, 2023, 2024, 2025], valores)
        for ano, valor in zip(range(2026, 2031), s[6]):
            assert math.isclose(valor, max(0, intercept + slope * ano), rel_tol=1e-9, abs_tol=1e-6)
        slope_bt, intercept_bt = linear_regression([2022, 2023, 2024], valores[:3])
        assert math.isclose(s[7][0], abs(valores[3] - valores[2]), abs_tol=1e-6)
        assert math.isclose(s[7][1], abs(valores[3] - max(0, intercept_bt + slope_bt * 2025)), rel_tol=1e-9, abs_tol=1e-6)
    raw = contrato_path.read_bytes()
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    assert pacote["blobShaOrigem"] == estados["blobShaOrigem"] == blob
    return {
        "publicacoes": len(inventario), "status_publicacoes": dict(status), "pares_pendentes": len(pares["pares"]),
        "nao_localizadas": len(faltantes), "celulas_sem_publicacao": len(faltantes) * 25,
        "estados_contrato": dict(Counter(r["estado"] for r in contrato)), "series_conferidas": len(elegiveis),
        "pontos_futuros_recalculados": len(elegiveis) * 5, "erros_backtest_conferidos": len(elegiveis) * 2,
        "zeros_tecnicos_incluidos": sum(s[10].count("Z") for s in pacote["series"]), "blob_origem": blob,
        "resultado": "PASSOU — conferência independente dos agregados; não certifica GDBs nem homologação humana",
    }


if __name__ == "__main__":
    print(json.dumps(auditoria(), ensure_ascii=False, indent=2))
