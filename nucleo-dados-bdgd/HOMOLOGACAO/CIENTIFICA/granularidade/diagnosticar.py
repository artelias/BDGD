"""Diagnóstico de viabilidade de painéis granulares 2022–2025 (diretriz de 04/11/2026: só competências 2022–2025 validadas).

    python HOMOLOGACAO/CIENTIFICA/granularidade/diagnosticar.py <saida_dir>

Não treina nem altera nada. Lê só o que já existe:
  * os agregados territoriais do Motor V2 (motor_v2/nacional/painel/<DIST>/<ativo>/<ano>/territorial.parquet), já extraídos dos
    Parquets originais com checkpoints e hashes (UCBT por MUN × CONJ × CTMT × área; transformadores por MUN × CONJ; redes por CONJ);
  * o contrato nacional (rupturas por DIST, ano e conceito), os eventos de sucessão e a ponte municipal pendente da Celesc 2023;
  * os METADADOS dos Parquets originais (rodapé: linhas, colunas e contagem de nulos por grupo de linhas), sem ler os dados.
Mede, por ativo e nível territorial (DIST, município, conjunto, circuito): unidades por ano, transições utilizáveis, continuidade
das chaves entre competências e a correlação intra-distribuidora do crescimento (efeito de desenho), que dá o número efetivo de
observações independentes. Milhões de registros espaciais não são milhões de observações temporais."""
import csv
import json
import math
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq

PAINEL = Path("D:/NUCLEO_BDGD_2025/motor_v2/nacional/painel")
CONTRATO = Path("D:/NUCLEO_BDGD_2025/wt-cientifica/nucleo-dados-bdgd/output-historico/contrato-integracao/serie_fisica_nacional.csv")
SUCESSAO = Path("D:/NUCLEO_BDGD_2025/output-historico/2022-2025/eventos_sucessao.csv")
INVENTARIO = Path("D:/NUCLEO_BDGD_2025/motor_v2/inventario_v2/INVENTARIO_PUBLICACOES_LOCAIS.csv")
PQ_2025 = Path("D:/NUCLEO_BDGD_2025/staging_parquet")
PQ_HIST = Path("D:/NUCLEO_BDGD_2022_2024/parquet")
ANOS = (2022, 2023, 2024, 2025)
CONTINUIDADE_MIN = 0.95          # parcela do estoque em unidades presentes nos dois anos (nos dois sentidos) para a chave ser estável
SALTO_SUSPEITO = math.log(2)      # |Δ ln| > ln 2 numa unidade: renumeração, perímetro ou cadastro (indicador, não filtro)
MUN_PENDENTE = {("5697", 2023)}   # recodificação municipal da Celesc 2023: ponte proposta, não homologada

ATIVOS = {   # painel -> (conceito do contrato para rupturas, níveis disponíveis e a coluna de cada nível, coluna do valor)
    "ucbt_quantidade": ("consumidores", {"DIST": None, "MUN": "MUN", "CONJ": "CONJ", "CTMT": "CTMT"}, "clientes_ativos"),
    "trafo_dist_quantidade": ("trafo_dist", {"DIST": None, "MUN": "UNIT", "CONJ": "CONJ"}, "value"),
    "trafo_dist_potencia_kva": ("trafo_dist", {"DIST": None, "MUN": "UNIT", "CONJ": "CONJ"}, "value"),
    "rede_bt_extensao_km": ("rede_bt", {"DIST": None, "CONJ": "CONJ"}, "value"),
    "rede_mt_extensao_km": ("rede_mt", {"DIST": None, "CONJ": "CONJ"}, "value"),
}
# variáveis candidatas: entidade -> colunas a verificar nos metadados (nomes do leiaute BDGD V11)
VARIAVEIS = {
    "UCBT": ["MUN", "CONJ", "CTMT", "ARE_LOC", "DAT_CON", "CAR_INST", "ENE_01", "ENE_12", "CEG_GD", "SIT_ATIV", "FAS_CON", "CLAS_SUB"],
    "UCMT": ["MUN", "CONJ", "CTMT", "ARE_LOC", "DAT_CON", "CAR_INST", "ENE_P_01", "CEG_GD"],
    "UGBT": ["MUN", "CONJ", "CTMT", "POT_INST", "DAT_CON", "CEG_GD"],
    "UNTRMT": ["MUN", "CONJ", "CTMT", "SUB", "POT_NOM", "DAT_CON", "ARE_LOC", "SIT_ATIV"],
    "EQTRMT": ["UNI_TR_MT", "POT_NOM", "TUC"],
    "SSDMT": ["CONJ", "CTMT", "COMP", "ARE_LOC", "SUB"],
    "SSDBT": ["CONJ", "CTMT", "COMP", "ARE_LOC", "UNI_TR_MT", "SUB"],
    "RAMLIG": ["CONJ", "CTMT", "COMP"],
    "CTMT": ["COD_ID", "SUB", "ENE_01", "PERD_B", "PNTMT_01", "TEN_NOM"],
    "SUB": ["COD_ID", "Shape_Area"],
    "CONJ": ["COD_ID", "NOME", "Shape_Area"],
    "PONNOT": ["CONJ", "CTMT", "MUN", "TIP_PN"],
}


def ler_csv(p):
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def rupturas():
    """{(dist, ano, conceito)}: a transição ano−1 → ano do conceito tem ruptura no contrato."""
    return {(r["dist"], int(r["ano"]), r["conceitoId"]) for r in ler_csv(CONTRATO) if r["ruptura_desde_ano_anterior"] == "true"}


def sucessoes():
    """{(dist, ano)}: transições que atravessam um evento societário (origem e destino), a excluir."""
    out = set()
    for r in ler_csv(SUCESSAO):
        ano = int((r["data_efetivacao"] or r["data_autorizacao"])[:4])
        for d in (r["dist_destino_2025"], r["dist_origem"]):
            if d:
                out |= {(d, ano), (d, ano + 1)}
    return out


def mapa(dist, ativo, ano, col, val):
    p = PAINEL / dist / ativo / str(ano) / "territorial.parquet"
    if not p.exists():
        return None
    t = pq.read_table(p, columns=[c for c in {col, val} if c])
    vals = t.column(val).to_pylist()
    chaves = t.column(col).to_pylist() if col else ["DIST"] * len(vals)
    m = defaultdict(float)
    for k, v in zip(chaves, vals):
        if v is not None:
            m["SEM_CODIGO" if k in (None, "", "0") else str(k)] += float(v)
    return {k: v for k, v in m.items() if v > 0}


def icc(grupos):
    """ICC de um sentido (estimador ANOVA) do crescimento log entre unidades da mesma DIST-transição."""
    gs = [g for g in grupos if len(g) >= 2]
    if len(gs) < 5:
        return None, None
    n = sum(len(g) for g in gs); k = len(gs)
    media = sum(sum(g) for g in gs) / n
    msb = sum(len(g) * (statistics.fmean(g) - media) ** 2 for g in gs) / (k - 1)
    msw = sum((x - statistics.fmean(g)) ** 2 for g in gs for x in g) / (n - k)
    n0 = (n - sum(len(g) ** 2 for g in gs) / n) / (k - 1)
    r = (msb - msw) / (msb + (n0 - 1) * msw) if msb + (n0 - 1) * msw > 0 else None
    return r, n / k


def painel(saida):
    rup, suc = rupturas(), sucessoes()
    dists = sorted(p.name for p in PAINEL.iterdir() if p.is_dir() and p.name.isdigit())
    por_ano, trans = [], []
    for ativo, (conc, niveis, val) in ATIVOS.items():
        for nivel, col in niveis.items():
            cont = {a: [0, 0] for a in ANOS}                       # dists com dado, unidades
            dados = {}
            for d in dists:
                for a in ANOS:
                    m = mapa(d, ativo, a, col, val)
                    if m is not None:
                        dados[(d, a)] = m
                        cont[a][0] += 1; cont[a][1] += len(m)
            for a in ANOS:
                por_ano.append(dict(ativo=ativo, nivel=nivel, ano=a, dist_com_dado=cont[a][0], unidades=cont[a][1]))
            for a in ANOS[1:]:
                n_tr = n_excl = n_instavel = n_estavel = 0
                pareadas = usaveis = saltos = 0
                conts, grupos = [], []
                for d in dists:
                    m0, m1 = dados.get((d, a - 1)), dados.get((d, a))
                    if not m0 or not m1:
                        continue
                    n_tr += 1
                    if (d, a, conc) in rup or (d, a) in suc or (nivel == "MUN" and ((d, a) in MUN_PENDENTE or (d, a - 1) in MUN_PENDENTE)):
                        n_excl += 1
                        continue
                    comuns = [k for k in m1 if k in m0 and k != "SEM_CODIGO"]
                    c1 = sum(m1[k] for k in comuns) / sum(m1.values()); c0 = sum(m0[k] for k in comuns) / sum(m0.values())
                    conts.append(min(c0, c1))
                    pareadas += len(comuns)
                    if min(c0, c1) < CONTINUIDADE_MIN and nivel != "DIST":
                        n_instavel += 1
                        continue
                    n_estavel += 1
                    g = [math.log(m1[k] / m0[k]) for k in comuns]
                    usaveis += len(g); saltos += sum(1 for x in g if abs(x) > SALTO_SUSPEITO)
                    grupos.append(g)
                r, m_medio = icc(grupos) if nivel != "DIST" else (None, 1.0)
                # ICC negativo (estimativa ruidosa) não reduz a dependência abaixo da independência: efeito de desenho ≥ 1
                deff = max(1.0, 1 + (m_medio - 1) * r) if r is not None and m_medio else None
                trans.append(dict(ativo=ativo, nivel=nivel, transicao=f"{a - 1}->{a}", dist_transicoes=n_tr, excluidas_ruptura_sucessao=n_excl,
                                  dist_chave_instavel=n_instavel, dist_chave_estavel=n_estavel, unidades_pareadas=pareadas, unidades_utilizaveis=usaveis,
                                  continuidade_mediana=round(statistics.median(conts), 4) if conts else None,
                                  saltos_suspeitos=saltos, icc_intra_dist=None if r is None else round(r, 4),
                                  unidades_por_dist=None if not m_medio else round(m_medio, 1), efeito_desenho=None if deff is None else round(deff, 2),
                                  n_efetivo=None if deff is None else round(usaveis / deff, 1) if nivel != "DIST" else usaveis))
            print(f"{ativo}/{nivel}: ok", flush=True)
    escrever(saida / "06a_UNIDADES_POR_ANO.csv", por_ano)
    escrever(saida / "06b_TRANSICOES_UTILIZAVEIS.csv", trans)
    return por_ano, trans


def arquivos(ent):
    """{ano: [arquivos do item do contrato]}: 2025 em staging_parquet; 2022–2024 no item selecionado no contrato."""
    sel = {(r["dist"], int(r["competencia"])): r["item_id"] for r in ler_csv(INVENTARIO) if r["tipo"] == "selecionada_no_contrato"}
    out = defaultdict(list)
    for (d, a), item in sel.items():
        if a == 2025:
            out[a] += sorted((PQ_2025 / f"DIST={d}" / "DATA_BASE=2025-12-31" / f"entidade={ent}").glob("*.parquet"))
        else:
            p = PQ_HIST / str(a) / d / item / f"{ent}.parquet"
            if p.exists():
                out[a].append(p)
    return out


def metadados(saida):
    linhas = []
    for ent, cols in VARIAVEIS.items():
        for a, fs in sorted(arquivos(ent).items()):
            n_rows, presentes, nulos, sem_stat = 0, Counter(), Counter(), Counter()
            dists = set()
            for f in fs:
                md = pq.ParquetFile(f).metadata
                n_rows += md.num_rows
                dists.add(f.parts[-3] if a < 2025 else f.parts[-4])
                nomes = [md.schema.column(i).name for i in range(md.num_columns)]
                for c in cols:
                    if c not in nomes:
                        continue
                    presentes[c] += md.num_rows
                    j = nomes.index(c)
                    for g in range(md.num_row_groups):
                        st = md.row_group(g).column(j).statistics
                        if st is None or not st.has_null_count:
                            sem_stat[c] += md.row_group(g).num_rows
                        else:
                            nulos[c] += st.null_count
            for c in cols:
                linhas.append(dict(entidade=ent, coluna=c, ano=a, dist_arquivos=len(dists), linhas=n_rows,
                                   linhas_com_coluna=presentes[c], fracao_com_coluna=round(presentes[c] / n_rows, 4) if n_rows else None,
                                   fracao_nula=round(nulos[c] / (presentes[c] - sem_stat[c]), 4) if presentes[c] - sem_stat[c] > 0 else None,
                                   linhas_sem_estatistica=sem_stat[c]))
        print(f"metadados {ent}: ok", flush=True)
    escrever(saida / "06c_VARIAVEIS_COBERTURA.csv", linhas)
    return linhas


def escrever(p, rows):
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n"); w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    saida = Path(sys.argv[1]); saida.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    por_ano, trans = painel(saida)
    t1 = time.time()
    md = metadados(saida)
    resumo = dict(segundos_paineis=round(t1 - t0, 1), segundos_metadados=round(time.time() - t1, 1),
                  linhas_originais_por_entidade_ano={f"{r['entidade']}/{r['ano']}": r["linhas"] for r in md if r["coluna"] == VARIAVEIS[r["entidade"]][0]})
    (saida / "06d_RESUMO.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(resumo, ensure_ascii=False)[:600])
