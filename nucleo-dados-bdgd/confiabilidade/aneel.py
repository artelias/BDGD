"""Indicadores coletivos de continuidade (ANEEL, dados abertos): obtenção e normalização.

    python -m confiabilidade.aneel baixar  [--trabalho DIR]     # baixa só o que mudou (last_modified do CKAN)
    python -m confiabilidade.aneel preparar [--trabalho DIR]    # raw -> continuidade.parquet, limites.parquet, PROVENIENCIA.json

Fonte: https://dadosabertos.aneel.gov.br/dataset/indicadores-coletivos-de-continuidade-dec-e-fec (licença ODbL).
O que entra: DEC, FEC, componentes de origem e NumCon mensais por conjunto, 2022–2025, e os limites anuais.
O arquivo de atributos dos conjuntos da ANEEL só tem dados até 2014; por isso a infraestrutura vem da BDGD.
As linhas do arquivo oficial vêm duplicadas; a normalização remove duplicatas exatas e FALHA se houver valores
conflitantes para a mesma chave (conjunto, indicador, ano, mês).
"""
import argparse
import hashlib
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .contrato import ANOS, VERSAO_CONTRATO

DATASET = 'indicadores-coletivos-de-continuidade-dec-e-fec'
API = 'https://dadosabertos.aneel.gov.br/api/3/action/package_show?id=' + DATASET
RECURSOS = {   # nome do recurso no CKAN -> arquivo local
    'indicadores-continuidade-coletivos-2020-2029.parquet': 'indicadores-continuidade-coletivos-2020-2029.parquet',
    'indicadores-continuidade-coletivos-limite': 'indicadores-continuidade-coletivos-limite.csv',
    'dominio-indicadores-indqual': 'dominio-indicadores.csv',
}
INDICADORES = ('DEC', 'FEC', 'NumCon', 'DECXP', 'DECXN', 'DECIP', 'DECIND', 'FECXP', 'FECXN', 'FECIP', 'FECIND',
               'DECINC', 'DECINE', 'DECINO', 'DECIPC', 'DECXNC', 'DECXPC', 'FECINC', 'FECINE', 'FECINO', 'FECIPC', 'FECXNC', 'FECXPC')
TRABALHO = Path(os.environ.get('CONF_TRABALHO', 'D:/NUCLEO_BDGD_2025/confiabilidade'))


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def baixar(trabalho=TRABALHO):
    """Baixa os recursos cujo last_modified mudou. O arquivo válido anterior só é trocado depois do download completo."""
    raw = Path(trabalho) / 'aneel_raw'
    raw.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(API, timeout=60) as r:
        pacote = json.load(r)['result']
    estado_p = raw / 'recursos.json'
    estado = json.loads(estado_p.read_text(encoding='utf-8')) if estado_p.exists() else {}
    for rec in pacote['resources']:
        destino = RECURSOS.get(rec['name'])
        if not destino:
            continue
        alvo = raw / destino
        if alvo.exists() and estado.get(destino, {}).get('last_modified') == rec.get('last_modified'):
            print('inalterado', destino)
            continue
        tmp = alvo.with_suffix(alvo.suffix + '.parcial')
        urllib.request.urlretrieve(rec['url'], tmp)
        tmp.replace(alvo)
        estado[destino] = dict(nome=rec['name'], url=rec['url'], last_modified=rec.get('last_modified'), bytes=alvo.stat().st_size,
                               sha256=sha256(alvo), baixado_em=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
        print('baixado', destino, estado[destino]['bytes'])
    estado_p.write_text(json.dumps(estado, ensure_ascii=False, indent=1), encoding='utf-8')
    return estado


def preparar(trabalho=TRABALHO, anos=ANOS):
    import duckdb
    trabalho = Path(trabalho)
    raw, out = trabalho / 'aneel_raw', trabalho / 'derivado'
    out.mkdir(parents=True, exist_ok=True)
    ind = raw / RECURSOS['indicadores-continuidade-coletivos-2020-2029.parquet']
    lim = raw / RECURSOS['indicadores-continuidade-coletivos-limite']
    con = duckdb.connect()
    con.execute("SET memory_limit='2GB'; SET threads=4")
    con.execute(f"SET temp_directory='{(trabalho / 'tmp_duckdb').as_posix()}'")
    a0, a1 = min(anos), max(anos)
    lista = ','.join(f"'{i}'" for i in INDICADORES)
    con.execute(f"""CREATE TEMP TABLE t AS SELECT DISTINCT IdeConjUndConsumidoras::BIGINT conj, trim(SigAgente) agente, NumCNPJ::BIGINT cnpj,
        trim(DscConjUndConsumidoras) nome, SigIndicador ind, AnoIndice::INT ano, NumPeriodoIndice::INT mes, VlrIndiceEnviado valor, DatGeracaoConjuntoDados gerado
        FROM read_parquet('{ind.as_posix()}') WHERE AnoIndice BETWEEN {a0} AND {a1} AND SigIndicador IN ({lista})""")
    conflitos = con.execute("SELECT COUNT(*) FROM (SELECT conj, ind, ano, mes FROM t GROUP BY ALL HAVING COUNT(DISTINCT valor) > 1)").fetchone()[0]
    if conflitos:
        raise SystemExit(f'ANEEL: {conflitos} chaves (conjunto, indicador, ano, mês) com valores conflitantes; nada foi gravado')
    multi = con.execute("SELECT COUNT(*) FROM (SELECT conj, ano FROM t GROUP BY ALL HAVING COUNT(DISTINCT agente) > 1)").fetchone()[0]
    if multi:
        raise SystemExit(f'ANEEL: {multi} conjuntos com mais de um agente no mesmo ano; nada foi gravado')
    cols = ', '.join(f"max(valor) FILTER (WHERE ind = '{i}') AS {i}" for i in INDICADORES)
    tmp = out / 'continuidade.parquet.parcial'
    con.execute(f"""COPY (SELECT conj, ano, mes, any_value(agente) agente, any_value(cnpj) cnpj, any_value(nome) nome, max(gerado) gerado, {cols}
        FROM t GROUP BY conj, ano, mes ORDER BY conj, ano, mes) TO '{tmp.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD)""")
    tmp.replace(out / 'continuidade.parquet')
    L = f"read_csv('{lim.as_posix()}', delim=';', header=true, all_varchar=true, quote='\"')"
    con.execute(f"""CREATE TEMP TABLE l AS SELECT DISTINCT IdeConjUndConsumidoras::BIGINT conj, trim(SigAgente) agente, SigIndicador ind, AnoLimiteQualidade::INT ano,
        replace(VlrLimite, ',', '.')::DOUBLE limite FROM {L} WHERE AnoLimiteQualidade::INT BETWEEN {a0} AND {a1} AND SigIndicador IN ('DEC', 'FEC')""")
    conf_l = con.execute("SELECT COUNT(*) FROM (SELECT conj, ind, ano FROM l GROUP BY ALL HAVING COUNT(DISTINCT limite) > 1)").fetchone()[0]
    if conf_l:
        raise SystemExit(f'ANEEL: {conf_l} limites conflitantes; nada foi gravado')
    tmp = out / 'limites.parquet.parcial'
    con.execute(f"""COPY (SELECT conj, ano, max(limite) FILTER (WHERE ind = 'DEC') lim_dec, max(limite) FILTER (WHERE ind = 'FEC') lim_fec
        FROM l GROUP BY conj, ano ORDER BY conj, ano) TO '{tmp.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD)""")
    tmp.replace(out / 'limites.parquet')
    C = f"read_parquet('{(out / 'continuidade.parquet').as_posix()}')"
    resumo = [dict(ano=a, conjuntos=n, conjunto_meses=m, agentes=g, sem_fec=sf, sem_numcon=sn) for a, n, m, g, sf, sn in con.execute(
        f"SELECT ano, COUNT(DISTINCT conj), COUNT(*), COUNT(DISTINCT agente), SUM((FEC IS NULL)::INT), SUM((NumCon IS NULL OR NumCon <= 0)::INT) FROM {C} GROUP BY 1 ORDER BY 1").fetchall()]
    # DEC/FEC apurados = componentes internas (IP + IND); externas (XP, XN) e expurgos são informativos e não compõem o indicador.
    identidade = con.execute(f"""SELECT COUNT(*), SUM((abs(DEC - (DECIP + DECIND)) <= 0.011)::INT), SUM((abs(FEC - (FECIP + FECIND)) <= 0.011)::INT)
        FROM {C} WHERE DEC IS NOT NULL AND FEC IS NOT NULL""").fetchone()
    estado_p = raw / 'recursos.json'
    prov = dict(contrato=VERSAO_CONTRATO, dataset=DATASET, licenca='Open Data Commons Open Database License (ODbL)',
                url='https://dadosabertos.aneel.gov.br/dataset/' + DATASET, anos=list(anos),
                gerado_pela_aneel_em=str(con.execute(f"SELECT max(gerado) FROM {C}").fetchone()[0]),
                recursos=json.loads(estado_p.read_text(encoding='utf-8')) if estado_p.exists() else {
                    f.name: dict(bytes=f.stat().st_size, sha256=sha256(f)) for f in (ind, lim)},
                duplicatas_exatas_removidas=True, conflitos=0, resumo_por_ano=resumo,
                identidade_componentes=dict(conjunto_meses=identidade[0], dec_igual_internas=identidade[1], fec_igual_internas=identidade[2],
                                            nota='DEC = DECIP + DECIND e FEC = FECIP + FECIND dentro do arredondamento de 2 casas; '
                                                 'componentes externas (XP, XN) e expurgos não compõem o indicador apurado'),
                preparado_em=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
    (out / 'PROVENIENCIA_ANEEL.json').write_text(json.dumps(prov, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(dict(resumo=resumo, identidade=prov['identidade_componentes']), ensure_ascii=False))
    return prov


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('acao', choices=['baixar', 'preparar'])
    ap.add_argument('--trabalho', default=str(TRABALHO))
    a = ap.parse_args()
    (baixar if a.acao == 'baixar' else preparar)(a.trabalho)
