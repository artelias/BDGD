"""Infraestrutura por conjunto elétrico a partir dos Parquets da BDGD (somente leitura), DIST × ANO × CONJ.

    python -m confiabilidade.infra --dist 6600 [--anos 2025 2024] [--forcar]
    python -m confiabilidade.infra --todas

Um arquivo por DIST e ano em <trabalho>/derivado/infra/DIST=<d>/ANO=<a>.json, gravado de forma atômica. A execução é
idempotente: a assinatura (versão do código + identidade e tamanho dos Parquets lidos) decide se há trabalho a fazer, e
uma carga que falha não substitui o arquivo válido anterior.

Regras físicas (as mesmas do portal):
  * consumidores = unidades distintas (COD_ID anonimizado, PN_CON) com SIT_ATIV = 'AT', por entidade (regra UC v3);
  * rede = SUM(COMP)/1000 em km (comprimento declarado);
  * transformadores de distribuição = equipamentos EQTRMT com TUC 565, levados ao conjunto pela instalação (UNI_TR_MT → UNTRMT);
    instalações (UNTRMT) são contadas à parte e nunca somadas aos equipamentos;
  * seccionamento = instalações UNSEMT ativas por classe (TIP_UNID, domínio TUNI) e telecomando (TLCD); os equipamentos EQSE por
    TUC (160 chave, 210 disjuntor, 345 religador) são levados ao conjunto por UN_SE e também ficam à parte;
  * nenhum vínculo é criado por proximidade geográfica: só chaves cadastrais (CONJ, CTMT, UNI_TR_MT, UN_SE, UN_RE).
Colunas ausentes num arquivo viram métrica ausente (None) com registro na auditoria; nunca zero.
"""
import argparse
import csv
import hashlib
import json
import os
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .contrato import ANOS, CLASSES_SECCIONAMENTO, SUPRESSAO_K, VERSAO_CONTRATO, gini, participacao_maiores, suprimir

VERSAO_CODIGO = 'infra-3'
RAIZ = Path(__file__).resolve().parents[1]
TRABALHO = Path(os.environ.get('CONF_TRABALHO', 'D:/NUCLEO_BDGD_2025/confiabilidade'))
STAGING_2025 = Path(os.environ.get('CONF_STAGING_2025', 'D:/NUCLEO_BDGD_2025/staging_parquet'))
PARQUET_HIST = Path(os.environ.get('CONF_PARQUET_HIST', 'D:/NUCLEO_BDGD_2022_2024/parquet'))
CONTRATO_NACIONAL = RAIZ / 'output-historico/contrato-integracao/serie_fisica_nacional.csv'
ENTIDADES = ('CONJ', 'CTMT', 'SUB', 'UCBT', 'UCMT', 'UCAT', 'SSDMT', 'SSDBT', 'UNTRMT', 'EQTRMT', 'UNSEMT', 'EQSE', 'UNREMT', 'EQRE', 'UGBT', 'UGMT')
MESES = [f'{i:02d}' for i in range(1, 13)]


# ------------------------------------------------------------------ fontes
def publicacoes_do_contrato():
    """(dist, ano) -> (publicacao_id, sha256) da publicação com células observadas no contrato nacional 2022–2024."""
    votos = defaultdict(lambda: defaultdict(int))
    sha = {}
    with open(CONTRATO_NACIONAL, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r['estado'] == 'observado' and r['publicacao_id']:
                k = (int(r['dist']), int(r['ano']))
                votos[k][r['publicacao_id']] += 1
                sha[(k, r['publicacao_id'])] = r['sha256']
    out = {}
    for k, v in votos.items():
        item = max(v.items(), key=lambda x: (x[1], x[0]))[0]
        out[k] = (item, sha.get((k, item), ''))
    return out


def resolver_fonte(dist, ano, pubs=None):
    """-> dict(base, item, sha256, arquivos={entidade: [paths]}) ou dict(erro=...)."""
    if ano == 2025:
        base = STAGING_2025 / f'DIST={dist}' / 'DATA_BASE=2025-12-31'
        if not (base / 'conversao.json').exists():
            return dict(erro='sem staging 2025 concluído (conversao.json ausente)')
        conv = json.loads((base / 'conversao.json').read_text(encoding='utf-8'))
        # só entidades com a conversão concluída (_OK) entram; as demais ficam ausentes, não parciais
        arquivos = {e: (sorted((base / f'entidade={e}').glob('*.parquet')) if (base / f'entidade={e}' / '_OK').exists() else []) for e in ENTIDADES}
        return dict(base=str(base), item=conv.get('item_id', ''), sha256=conv.get('sha256_zip', ''), base_bdgd=conv.get('BASE', {}), arquivos=arquivos)
    pubs = pubs if pubs is not None else publicacoes_do_contrato()
    hit = pubs.get((dist, ano))
    if not hit:
        return dict(erro='sem publicação observada no contrato nacional para o ano')
    base = PARQUET_HIST / str(ano) / str(dist) / hit[0]
    if not base.exists():
        return dict(erro=f'publicação {hit[0]} do contrato não está nos Parquets locais')
    arquivos = {e: ([base / f'{e}.parquet'] if (base / f'{e}.parquet').exists() else []) for e in ENTIDADES}
    return dict(base=str(base), item=hit[0], sha256=hit[1], base_bdgd={}, arquivos=arquivos)


def assinatura(fonte):
    h = hashlib.sha256()
    h.update((VERSAO_CODIGO + '|' + VERSAO_CONTRATO + '|' + fonte['item'] + '|' + fonte['sha256']).encode())
    for e in ENTIDADES:
        for p in fonte['arquivos'][e]:
            st = p.stat()
            h.update(f'{e}|{p.name}|{st.st_size}|{int(st.st_mtime)}'.encode())
    return h.hexdigest()


# ------------------------------------------------------------------ SQL
def lit(p):
    return "'" + str(p).replace('\\', '/').replace("'", "''") + "'"


class Leitor:
    def __init__(self, con, fonte):
        self.con, self.cols, self.linhas = con, {}, {}
        for e in ENTIDADES:
            arqs = fonte['arquivos'][e]
            if not arqs:
                self.cols[e] = None
                continue
            con.execute(f"CREATE OR REPLACE TEMP VIEW v_{e} AS SELECT * FROM read_parquet([{', '.join(lit(a) for a in arqs)}], union_by_name=true)")
            self.cols[e] = {r[0] for r in con.execute(f'DESCRIBE v_{e}').fetchall()}

    def tem(self, e, *cols):
        return self.cols.get(e) is not None and set(cols) <= self.cols[e]

    def col(self, e, c, tipo='VARCHAR', padrao='NULL'):
        return f'try_cast({c} AS {tipo})' if self.tem(e, c) else f'{padrao}::{tipo}'

    def q(self, sql):
        return self.con.execute(sql).fetchall()


CONJ = "try_cast({e}.CONJ AS BIGINT)"
CTMT = "nullif(trim(CAST({e}.CTMT AS VARCHAR)), '')"


def consumidores(L, ent):
    """Por (conj) e (conj, ctmt): unidades ativas distintas, rurais, energia e numeradores DIC/FIC."""
    if not L.tem(ent, 'COD_ID', 'SIT_ATIV', 'CONJ'):
        return None
    pn = "coalesce(CAST(PN_CON AS VARCHAR), '')" if L.tem(ent, 'PN_CON') else "''"
    ctmt = "nullif(trim(CAST(CTMT AS VARCHAR)), '')" if L.tem(ent, 'CTMT') else 'NULL::VARCHAR'
    area = "CAST(ARE_LOC AS VARCHAR)" if L.tem(ent, 'ARE_LOC') else 'NULL::VARCHAR'
    ene_cols = [f'ENE_{m}' for m in MESES] if ent != 'UCAT' else [f'ENE_P_{m}' for m in MESES] + [f'ENE_F_{m}' for m in MESES]
    ene = ' + '.join(f'coalesce(try_cast({c} AS DOUBLE), 0)' for c in ene_cols) if all(L.tem(ent, c) for c in ene_cols) else 'NULL::DOUBLE'
    tem_dic = all(L.tem(ent, f'DIC_{m}') and L.tem(ent, f'FIC_{m}') for m in MESES)
    bruto = ', '.join((f'try_cast(DIC_{m} AS DOUBLE) d{m}, try_cast(FIC_{m} AS DOUBLE) f{m}' if tem_dic else f'NULL::DOUBLE d{m}, NULL::DOUBLE f{m}') for m in MESES)
    dic = ', '.join(f'SUM(d{m}) dic_{m}, SUM(f{m}) fic_{m}' for m in MESES)
    n_dic = 'COUNT(d01)' if tem_dic else 'NULL::BIGINT'
    rows = L.q(f"""WITH x AS (SELECT try_cast(CONJ AS BIGINT) conj, {ctmt} ctmt, CAST(COD_ID AS VARCHAR) id, {pn} pn, CAST(SIT_ATIV AS VARCHAR) sit, {area} area, {ene} ene, {bruto} FROM v_{ent})
        SELECT conj, ctmt, GROUPING(ctmt) total, COUNT(DISTINCT (id, pn)) FILTER (WHERE sit = 'AT') uc,
               COUNT(DISTINCT (id, pn)) FILTER (WHERE sit = 'AT' AND area = 'NU') uc_rural,
               COUNT(DISTINCT (id, pn)) FILTER (WHERE sit = 'AT' AND area IS NOT NULL) uc_com_area,
               COUNT(*) linhas, SUM(ene) FILTER (WHERE sit = 'AT') ene_kwh, {n_dic} n_dic, {dic}
        FROM x GROUP BY GROUPING SETS ((conj), (conj, ctmt))""")
    campos = ['conj', 'ctmt', 'total', 'uc', 'uc_rural', 'uc_com_area', 'linhas', 'ene_kwh', 'n_dic'] + [f'{k}_{m}' for m in MESES for k in ('dic', 'fic')]
    return [dict(zip(campos, r)) for r in rows], tem_dic


def rede(L, ent):
    if not L.tem(ent, 'COMP', 'CONJ'):
        return None
    ctmt = "nullif(trim(CAST(CTMT AS VARCHAR)), '')" if L.tem(ent, 'CTMT') else 'NULL::VARCHAR'
    area = "CAST(ARE_LOC AS VARCHAR)" if L.tem(ent, 'ARE_LOC') else 'NULL::VARCHAR'
    fas = "len(regexp_replace(upper(CAST(FAS_CON AS VARCHAR)), '[^ABC]', '', 'g'))" if L.tem(ent, 'FAS_CON') else 'NULL::INT'
    rows = L.q(f"""WITH x AS (SELECT try_cast(CONJ AS BIGINT) conj, {ctmt} ctmt, try_cast(COMP AS DOUBLE) comp, {area} area, {fas} nf FROM v_{ent})
        SELECT conj, ctmt, GROUPING(ctmt) total, SUM(comp) / 1000 km, coalesce(SUM(comp) FILTER (WHERE area = 'NU'), 0) / 1000 km_rural,
               coalesce(SUM(comp) FILTER (WHERE area IS NOT NULL), 0) / 1000 km_com_area, coalesce(SUM(comp) FILTER (WHERE nf = 3), 0) / 1000 km_tri,
               coalesce(SUM(comp) FILTER (WHERE nf IS NOT NULL), 0) / 1000 km_com_fase, COUNT(*) trechos
        FROM x GROUP BY GROUPING SETS ((conj), (conj, ctmt))""")
    return [dict(zip(['conj', 'ctmt', 'total', 'km', 'km_rural', 'km_com_area', 'km_tri', 'km_com_fase', 'trechos'], r)) for r in rows]


def transformadores(L):
    if not L.tem('UNTRMT', 'COD_ID', 'CONJ'):
        return None, {}
    tem_eq = L.tem('EQTRMT', 'UNI_TR_MT', 'TUC')
    eq = ("SELECT trim(CAST(UNI_TR_MT AS VARCHAR)) un, COUNT(*) FILTER (WHERE trim(CAST(TUC AS VARCHAR)) = '565') n565, COUNT(*) n FROM v_EQTRMT GROUP BY 1"
          if tem_eq else 'SELECT NULL::VARCHAR un, NULL::BIGINT n565, NULL::BIGINT n WHERE false')
    ctmt = "nullif(trim(CAST(u.CTMT AS VARCHAR)), '')" if L.tem('UNTRMT', 'CTMT') else 'NULL::VARCHAR'
    sit = "CAST(u.SIT_ATIV AS VARCHAR)" if L.tem('UNTRMT', 'SIT_ATIV') else "'AT'"
    pot = 'try_cast(u.POT_NOM AS DOUBLE)' if L.tem('UNTRMT', 'POT_NOM') else 'NULL::DOUBLE'
    mrt = 'try_cast(u.MRT AS INT)' if L.tem('UNTRMT', 'MRT') else 'NULL::INT'
    area = "CAST(u.ARE_LOC AS VARCHAR)" if L.tem('UNTRMT', 'ARE_LOC') else 'NULL::VARCHAR'
    soma565 = 'SUM(eq.n565)' if tem_eq else 'NULL::BIGINT'
    rows = L.q(f"""WITH eq AS ({eq}), x AS (SELECT try_cast(u.CONJ AS BIGINT) conj, {ctmt} ctmt, {sit} sit, {pot} pot, {mrt} mrt, {area} area, eq.n565 n565
            FROM v_UNTRMT u LEFT JOIN eq ON eq.un = trim(CAST(u.COD_ID AS VARCHAR)))
        SELECT conj, ctmt, GROUPING(ctmt) total, COUNT(*) FILTER (WHERE sit = 'AT') un_at, COUNT(*) un, {'coalesce(SUM(n565), 0)' if tem_eq else 'NULL::BIGINT'} eq565,
               SUM(pot) FILTER (WHERE sit = 'AT') pot_kva, COUNT(*) FILTER (WHERE sit = 'AT' AND mrt = 1) un_mrt, COUNT(*) FILTER (WHERE sit = 'AT' AND area = 'NU') un_rural
        FROM x GROUP BY GROUPING SETS ((conj), (conj, ctmt))""")
    aud = {}
    if tem_eq:
        t565, sem = L.q("""SELECT COUNT(*) FILTER (WHERE trim(CAST(e.TUC AS VARCHAR)) = '565'),
            COUNT(*) FILTER (WHERE trim(CAST(e.TUC AS VARCHAR)) = '565' AND u.COD_ID IS NULL)
            FROM v_EQTRMT e LEFT JOIN (SELECT DISTINCT trim(CAST(COD_ID AS VARCHAR)) COD_ID FROM v_UNTRMT) u ON u.COD_ID = trim(CAST(e.UNI_TR_MT AS VARCHAR))""")[0]
        aud = dict(eqtrmt_tuc565=t565, eqtrmt_tuc565_sem_instalacao=sem)
    return [dict(zip(['conj', 'ctmt', 'total', 'un_at', 'un', 'eq565', 'pot_kva', 'un_mrt', 'un_rural'], r)) for r in rows], aud


def seccionamento(L):
    if not L.tem('UNSEMT', 'COD_ID', 'CONJ'):
        return None, {}
    ctmt = "nullif(trim(CAST(u.CTMT AS VARCHAR)), '')" if L.tem('UNSEMT', 'CTMT') else 'NULL::VARCHAR'
    sit = "CAST(u.SIT_ATIV AS VARCHAR)" if L.tem('UNSEMT', 'SIT_ATIV') else "'AT'"
    tip = 'try_cast(u.TIP_UNID AS INT)' if L.tem('UNSEMT', 'TIP_UNID') else 'NULL::INT'
    tl = 'try_cast(u.TLCD AS INT)' if L.tem('UNSEMT', 'TLCD') else 'NULL::INT'
    na = "upper(CAST(u.P_N_OPE AS VARCHAR))" if L.tem('UNSEMT', 'P_N_OPE') else 'NULL::VARCHAR'
    tem_eq = L.tem('EQSE', 'UN_SE', 'TUC')
    eq = ("""SELECT trim(CAST(UN_SE AS VARCHAR)) un, COUNT(*) FILTER (WHERE trim(CAST(TUC AS VARCHAR)) = '160') n160,
             COUNT(*) FILTER (WHERE trim(CAST(TUC AS VARCHAR)) = '210') n210, COUNT(*) FILTER (WHERE trim(CAST(TUC AS VARCHAR)) = '345') n345 FROM v_EQSE GROUP BY 1"""
          if tem_eq else 'SELECT NULL::VARCHAR un, NULL::BIGINT n160, NULL::BIGINT n210, NULL::BIGINT n345 WHERE false')
    classes = ', '.join(f"COUNT(*) FILTER (WHERE sit = 'AT' AND tip IN ({', '.join(map(str, sorted(v)))})) sec_{k}" for k, v in CLASSES_SECCIONAMENTO.items())
    eqs = ', '.join(f"{'coalesce(SUM(' + c + '), 0)' if tem_eq else 'NULL::BIGINT'} eq{c[1:]}" for c in ('n160', 'n210', 'n345'))
    rows = L.q(f"""WITH eq AS ({eq}), x AS (SELECT try_cast(u.CONJ AS BIGINT) conj, {ctmt} ctmt, {sit} sit, {tip} tip, {tl} tl, {na} na, eq.n160, eq.n210, eq.n345
            FROM v_UNSEMT u LEFT JOIN eq ON eq.un = trim(CAST(u.COD_ID AS VARCHAR)))
        SELECT conj, ctmt, GROUPING(ctmt) total, COUNT(*) FILTER (WHERE sit = 'AT') sec, COUNT(*) sec_linhas, {classes},
               COUNT(*) FILTER (WHERE sit = 'AT' AND tl = 1) sec_tlcd, COUNT(*) FILTER (WHERE sit = 'AT' AND tl IS NOT NULL) sec_com_tlcd,
               COUNT(*) FILTER (WHERE sit = 'AT' AND na = 'A') sec_na, {eqs}
        FROM x GROUP BY GROUPING SETS ((conj), (conj, ctmt))""")
    campos = ['conj', 'ctmt', 'total', 'sec', 'sec_linhas'] + [f'sec_{k}' for k in CLASSES_SECCIONAMENTO] + ['sec_tlcd', 'sec_com_tlcd', 'sec_na', 'eq160', 'eq210', 'eq345']
    aud = {}
    if tem_eq:
        r = L.q("""SELECT trim(CAST(e.TUC AS VARCHAR)) tuc, COUNT(*), COUNT(*) FILTER (WHERE u.COD_ID IS NOT NULL)
            FROM v_EQSE e LEFT JOIN (SELECT DISTINCT trim(CAST(COD_ID AS VARCHAR)) COD_ID FROM v_UNSEMT) u ON u.COD_ID = trim(CAST(e.UN_SE AS VARCHAR))
            WHERE trim(CAST(e.TUC AS VARCHAR)) IN ('160', '210', '345') GROUP BY 1""")
        aud = {f'eqse_tuc{t}': dict(total=n, em_instalacao_mt=m) for t, n, m in r}
    return [dict(zip(campos, r)) for r in rows], aud


def reguladores(L):
    if not L.tem('UNREMT', 'COD_ID', 'CONJ'):
        return None
    tem_eq = L.tem('EQRE', 'UN_RE')
    eq = "SELECT trim(CAST(UN_RE AS VARCHAR)) un, COUNT(*) n FROM v_EQRE GROUP BY 1" if tem_eq else 'SELECT NULL::VARCHAR un, NULL::BIGINT n WHERE false'
    sit = "CAST(u.SIT_ATIV AS VARCHAR)" if L.tem('UNREMT', 'SIT_ATIV') else "'AT'"
    rows = L.q(f"""WITH eq AS ({eq}) SELECT try_cast(u.CONJ AS BIGINT) conj, COUNT(*) FILTER (WHERE {sit} = 'AT') reg_un,
        {'coalesce(SUM(eq.n), 0)' if tem_eq else 'NULL::BIGINT'} reg_eq FROM v_UNREMT u LEFT JOIN eq ON eq.un = trim(CAST(u.COD_ID AS VARCHAR)) GROUP BY 1""")
    return {r[0]: dict(reg_un=r[1], reg_eq=r[2]) for r in rows}


def geradores(L):
    out = defaultdict(int)
    algum = False
    for e in ('UGBT', 'UGMT'):
        if L.tem(e, 'CONJ', 'SIT_ATIV'):
            algum = True
            for c, n in L.q(f"SELECT try_cast(CONJ AS BIGINT), COUNT(*) FILTER (WHERE CAST(SIT_ATIV AS VARCHAR) = 'AT') FROM v_{e} GROUP BY 1"):
                out[c] += n
    return dict(out) if algum else None


# ------------------------------------------------------------------ montagem
def processar(dist, ano, fonte):
    import duckdb
    t0 = time.time()
    con = duckdb.connect()
    con.execute("SET memory_limit='3GB'; SET threads=3; SET preserve_insertion_order=false")
    con.execute(f"SET temp_directory={lit(TRABALHO / 'tmp_duckdb')}")
    L = Leitor(con, fonte)
    aud = dict(entidades={e: (None if L.cols[e] is None else L.q(f'SELECT COUNT(*) FROM v_{e}')[0][0]) for e in ENTIDADES}, ausencias=[])
    conj = defaultdict(dict)          # conj -> métricas
    alim = defaultdict(dict)          # (conj, ctmt) -> métricas

    nomes = {}
    if L.tem('CONJ', 'COD_ID'):
        for c, n in L.q(f"SELECT try_cast(COD_ID AS BIGINT), {L.col('CONJ', 'NOME')} FROM v_CONJ"):
            if c is not None:
                nomes[c] = (n or '').strip()
                conj[c]['nome'] = nomes[c]
    else:
        aud['ausencias'].append('CONJ: camada ausente; conjuntos identificados só pelas chaves das demais entidades')

    dic = {}
    for ent, niv in (('UCBT', 'bt'), ('UCMT', 'mt'), ('UCAT', 'at')):
        r = consumidores(L, ent)
        if r is None:
            aud['ausencias'].append(f'{ent}: sem COD_ID, SIT_ATIV ou CONJ')
            continue
        rows, tem_dic = r
        if not tem_dic:
            aud['ausencias'].append(f'{ent}: sem DIC/FIC mensais')
        for x in rows:
            if x['total']:
                d = conj[x['conj']]
                d[f'uc_{niv}'] = x['uc']; d[f'uc_{niv}_rural'] = x['uc_rural'] if x['uc_com_area'] else None
                d[f'uc_{niv}_linhas'] = x['linhas']
                d[f'ene_{niv}_mwh'] = None if x['ene_kwh'] is None else x['ene_kwh'] / 1000
                if tem_dic:
                    acc = dic.setdefault(x['conj'], dict(dic=[0.0] * 12, fic=[0.0] * 12, linhas=0, com_dic=0, entidades=[]))
                    for i, m in enumerate(MESES):
                        acc['dic'][i] += x[f'dic_{m}'] or 0.0; acc['fic'][i] += x[f'fic_{m}'] or 0.0
                    acc['linhas'] += x['linhas']; acc['com_dic'] += x['n_dic'] or 0; acc['entidades'].append(ent)
            elif niv != 'at':
                alim[(x['conj'], x['ctmt'])][f'uc_{niv}'] = x['uc']

    for ent, niv in (('SSDMT', 'mt'), ('SSDBT', 'bt')):
        rows = rede(L, ent)
        if rows is None:
            aud['ausencias'].append(f'{ent}: sem COMP ou CONJ')
            continue
        for x in rows:
            if x['total']:
                d = conj[x['conj']]
                d[f'km_{niv}'] = x['km']; d[f'km_{niv}_rural'] = x['km_rural'] if x['km_com_area'] else None
                if niv == 'mt':
                    d['km_mt_tri'] = x['km_tri'] if x['km_com_fase'] else None
            else:
                alim[(x['conj'], x['ctmt'])][f'km_{niv}'] = x['km']

    rows, a = transformadores(L)
    aud.update(a)
    if rows is None:
        aud['ausencias'].append('UNTRMT: sem COD_ID ou CONJ')
    else:
        for x in rows:
            alvo = conj[x['conj']] if x['total'] else alim[(x['conj'], x['ctmt'])]
            alvo['trafos'] = x['eq565']
            if x['total']:
                alvo.update(trafo_un=x['un_at'], trafo_pot_kva=x['pot_kva'], trafo_un_mrt=x['un_mrt'], trafo_un_rural=x['un_rural'])

    rows, a = seccionamento(L)
    aud.update(a)
    if rows is None:
        aud['ausencias'].append('UNSEMT: sem COD_ID ou CONJ')
    else:
        for x in rows:
            if x['total']:
                conj[x['conj']].update({k: x[k] for k in x if k not in ('conj', 'ctmt', 'total', 'sec_linhas', 'sec_com_tlcd')})
                if not x['sec_com_tlcd']:
                    conj[x['conj']]['sec_tlcd'] = None
            else:
                alim[(x['conj'], x['ctmt'])].update(sec=x['sec'], sec_religador=x['sec_religador'], sec_tlcd=x['sec_tlcd'] if x['sec_com_tlcd'] else None)

    r = reguladores(L)
    if r is None:
        aud['ausencias'].append('UNREMT: sem COD_ID ou CONJ')
    else:
        for c, v in r.items():
            conj[c].update(v)
    g = geradores(L)
    if g is not None:
        for c, n in g.items():
            conj[c]['ug'] = n

    # alimentadores: nome, subestação, tensão e energia injetada (do cadastro CTMT)
    ctmt_info = {}
    if L.tem('CTMT', 'COD_ID'):
        ene = ' + '.join(f'coalesce(try_cast(ENE_{m} AS DOUBLE), 0)' for m in MESES) if all(L.tem('CTMT', f'ENE_{m}') for m in MESES) else 'NULL::DOUBLE'
        for cid, nome, sub, ten, e in L.q(f"SELECT trim(CAST(COD_ID AS VARCHAR)), {L.col('CTMT', 'NOME')}, {L.col('CTMT', 'SUB')}, {L.col('CTMT', 'TEN_NOM')}, {ene} FROM v_CTMT"):
            ctmt_info[cid] = dict(nome=(nome or '').strip(), sub=(sub or '').strip() or None, ten=ten, ene_mwh=None if e is None else e / 1000)
    else:
        aud['ausencias'].append('CTMT: cadastro de alimentadores ausente')
    subs = {}
    if L.tem('SUB', 'COD_ID'):
        subs = {c: (n or '').strip() for c, n in L.q(f"SELECT trim(CAST(COD_ID AS VARCHAR)), {L.col('SUB', 'NOME')} FROM v_SUB")}

    # predominância: o conjunto em que o alimentador tem a maior extensão MT
    km_por_ctmt = defaultdict(dict)
    for (c, ct), v in alim.items():
        if ct and v.get('km_mt'):
            km_por_ctmt[ct][c] = v['km_mt']
    pred = {ct: max(d.items(), key=lambda kv: (kv[1], -(kv[0] or 0)))[0] for ct, d in km_por_ctmt.items()}
    aud['alimentadores'] = dict(com_rede_mt=len(km_por_ctmt), em_mais_de_um_conjunto=sum(len(d) > 1 for d in km_por_ctmt.values()),
                                no_cadastro_ctmt=len(ctmt_info), com_rede_fora_do_cadastro=sum(ct not in ctmt_info for ct in km_por_ctmt) if ctmt_info else None)

    lista_alim = defaultdict(list)
    for (c, ct), v in alim.items():
        if c is None or ct is None:
            continue
        info = ctmt_info.get(ct, {})
        km_tot = sum(km_por_ctmt.get(ct, {}).values()) or None
        lista_alim[c].append(dict(ctmt=ct, nome=info.get('nome') or None, sub=info.get('sub'), sub_nome=subs.get(info.get('sub') or '') or None, ten=info.get('ten'),
                                  km_mt=v.get('km_mt'), km_bt=v.get('km_bt'), km_mt_alimentador=km_tot, predominante=pred.get(ct) == c,
                                  uc_bt=suprimir(v.get('uc_bt')), uc_mt=suprimir(v.get('uc_mt')), uc_suprimido=any(v.get(k) is not None and suprimir(v.get(k)) is None for k in ('uc_bt', 'uc_mt')),
                                  _uc=(v.get('uc_bt') or 0) + (v.get('uc_mt') or 0), trafos=v.get('trafos'), sec=v.get('sec'), religadores=v.get('sec_religador'), telecomandadas=v.get('sec_tlcd')))

    saida = {}
    for c, d in conj.items():
        if c is None:
            continue
        al = sorted(lista_alim.get(c, []), key=lambda a: -(a['km_mt'] or 0))
        com_rede = [a for a in al if a['km_mt']]
        d['alim'] = len(com_rede) if 'km_mt' in d else None
        d['alim_pred'] = sum(a['predominante'] for a in com_rede) if 'km_mt' in d else None
        d['subs'] = len({a['sub'] for a in com_rede if a['sub']}) if (com_rede and ctmt_info) else None
        d['conc_km_gini'] = gini([a['km_mt'] for a in com_rede])
        d['conc_km_top1'] = participacao_maiores([a['km_mt'] for a in com_rede], 1)
        d['conc_uc_top1'] = participacao_maiores([a['_uc'] for a in al if a['_uc']], 1)
        d['conc_uc_top3'] = participacao_maiores([a['_uc'] for a in al if a['_uc']], 3)
        d['conc_uc_gini'] = gini([a['_uc'] for a in al if a['_uc']])
        d['km_mt_maior_alim'] = max((a['km_mt'] for a in com_rede), default=None)
        for a in al:
            a.pop('_uc')
        x = dic.get(c)
        saida[str(c)] = dict(metricas=d, alimentadores=al,
                             dic_fic=None if x is None else dict(soma_dic=[round(v, 4) for v in x['dic']], soma_fic=[round(v, 4) for v in x['fic']],
                                                                 linhas=x['linhas'], linhas_com_dic=x['com_dic'], entidades=x['entidades']))
    sem_conj = {k: v for k, v in conj.get(None, {}).items() if k != 'nome'}
    aud['sem_conjunto'] = sem_conj or None
    aud['conjuntos'] = dict(na_camada_conj=len(nomes), com_metricas=len(saida),
                            com_metricas_fora_da_camada=sorted(int(c) for c in saida if nomes and int(c) not in nomes)[:50])
    tot = lambda k: sum(v['metricas'].get(k) or 0 for v in saida.values()) + (sem_conj.get(k) or 0)
    aud['totais_dist'] = {k: tot(k) for k in ('uc_bt', 'uc_mt', 'uc_at', 'km_mt', 'km_bt', 'trafos', 'trafo_un', 'trafo_pot_kva', 'sec', 'eq160', 'eq210', 'eq345', 'reg_un', 'reg_eq')}
    aud['segundos'] = round(time.time() - t0, 1)
    return saida, aud


def executar(dist, ano, pubs=None, forcar=False, trabalho=TRABALHO):
    destino = Path(trabalho) / 'derivado' / 'infra' / f'DIST={dist}' / f'ANO={ano}.json'
    fonte = resolver_fonte(dist, ano, pubs)
    if 'erro' in fonte:
        return dict(dist=dist, ano=ano, status='SEM_FONTE', motivo=fonte['erro'])
    ass = assinatura(fonte)
    if destino.exists() and not forcar:
        try:
            if json.loads(destino.read_text(encoding='utf-8'))['meta']['assinatura'] == ass:
                return dict(dist=dist, ano=ano, status='INALTERADO')
        except (ValueError, KeyError):
            pass
    conj, aud = processar(dist, ano, fonte)
    doc = dict(meta=dict(contrato=VERSAO_CONTRATO, codigo=VERSAO_CODIGO, dist=dist, ano=ano, assinatura=ass, estado='DERIVADO_EXPLORATORIO',
                         fonte=dict(base=fonte['base'], item=fonte['item'], sha256_gdb=fonte['sha256'], base_bdgd=fonte.get('base_bdgd') or {}),
                         supressao_k=SUPRESSAO_K, gerado_em=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')),
               auditoria=aud, conjuntos=conj)
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix('.parcial')
    tmp.write_text(json.dumps(doc, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    tmp.replace(destino)
    return dict(dist=dist, ano=ano, status='PROCESSADO', conjuntos=len(conj), segundos=aud['segundos'])


def dists_disponiveis():
    return sorted(int(p.name.split('=')[1]) for p in STAGING_2025.glob('DIST=*') if (p / 'DATA_BASE=2025-12-31' / 'conversao.json').exists())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dist', type=int, nargs='*')
    ap.add_argument('--todas', action='store_true')
    ap.add_argument('--anos', type=int, nargs='*', default=list(reversed(ANOS)))
    ap.add_argument('--forcar', action='store_true')
    a = ap.parse_args()
    if any(y not in ANOS for y in a.anos):
        raise SystemExit(f'anos permitidos: {ANOS}')
    dists = dists_disponiveis() if a.todas else (a.dist or [])
    pubs = publicacoes_do_contrato()
    log = TRABALHO / 'derivado' / 'infra' / 'execucoes.jsonl'
    log.parent.mkdir(parents=True, exist_ok=True)
    for d in dists:
        for y in a.anos:
            try:
                r = executar(d, y, pubs, a.forcar)
            except Exception as e:  # uma falha não interrompe as demais nem troca o arquivo válido
                r = dict(dist=d, ano=y, status='FALHOU', motivo=f'{type(e).__name__}: {e}'[:400])
            r['em'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            print(json.dumps(r, ensure_ascii=False), flush=True)
            with open(log, 'a', encoding='utf-8') as f:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
