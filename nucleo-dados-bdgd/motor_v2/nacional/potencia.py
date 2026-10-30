"""Power audit of four equipment families, kept SEPARATE: distribution transformers (TUC 565), power transformers (TUC 570),
instrument transformers (TUC 575) and voltage regulators.

    python -m motor_v2.nacional.potencia

Semantics come from the BDGD knowledge base (Manual BDGD / DDA Modulo 10, REV5, C:/GEOIA/GEOIA_DATA_HUB/knowledge):
  EQTRMT.POT_NOM, EQTRAT.POT_NOM, EQRE.POT_NOM -> DDA table TPOTAPRT = APPARENT power, kVA (code -> value);
  UNTRMT.POT_NOM = apparent power, kVA (numeric); UNTRAT.POT_NOM = apparent power, MVA (numeric; x1000 is a change of scale of
  the same quantity, not a conversion between quantities); EQTRAT.POT_F01/F02 = ratings with forced ventilation (other operating
  condition, never added to the nominal rating); EQRE.COR_NOM = current (A), not power; UNCR*.POT_NOM -> TPOTRTV = REACTIVE power
  (kVAr); EQTRM (instrument transformer) has no power field at all.
No kVA <-> kW <-> kVAr conversion is made anywhere (it would need a power factor that the BDGD does not carry).

Read only: the ordinary publication the national contract selects for each DIST x competence (runner.resolve_sources), entity
Parquets already on disk, a few columns each. Per DIST x year and family: records, valid / zero ('nao informado') / unknown / null
power codes, kVA by the equipment code (EQ) and by the linked installation (UN), and their agreement. Release rule proposed for an
experimental kVA series (the same gate already used by the Level A distribution-transformer kVA): every record with a valid,
positive power code (no 'nao informado', unknown or null code) and quantity equal to the contract quantity of the concept."""
import csv
import json
import time
from collections import defaultdict
from pathlib import Path

import duckdb

from . import CONTRACT, ROOT_OUT
from .relatorio import write_csv
from ..runner import atomic, digest, resolve_sources

KNOW = Path('C:/GEOIA/GEOIA_DATA_HUB/knowledge')
OUT = ROOT_OUT / 'potencia'
FAMILIAS = {  # family -> (contract concept, TUC, equipment entities)
    'trafo_dist_565': ('trafo_dist', '565', ('EQTRMT', 'EQTRAT')),
    'trafo_forca_570': ('trafo_forca', '570', ('EQTRMT', 'EQTRAT')),
    'trafo_medida_575': ('trafo_medida', '575', ('EQTRM', 'EQTRMT', 'EQTRAT')),
    'reguladores': ('reguladores', None, ('EQRE',)),
}
LINK = {'EQTRMT': ('UNI_TR_MT', 'UNTRMT', 1.0), 'EQTRAT': ('UNI_TR_AT', 'UNTRAT', 1000.0)}


def dda():
    d = json.loads((KNOW / 'BDGD_DDA_CATALOG_M10.json').read_text(encoding='utf-8'))
    t = {x['table']: {str(v['COD_ID']).strip(): v.get('POT') for v in x['values']} for x in d['tables']}
    return t['TPOTAPRT'], digest(KNOW / 'BDGD_DDA_CATALOG_M10.json')


def path(src, e):
    b = Path(src['base'])
    return b / f'entidade={e}' / 'part-0.parquet' if src['year'] == 2025 else b / f'{e}.parquet'


def contract_qty():
    out = {}
    with open(CONTRACT, encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            if r['metrica'] == 'quantidade':
                out[int(r['dist']), r['conceitoId'], int(r['ano'])] = (float(r['valor']) if r['valor'] else None, r['estado'])
    return out


def audit_one(con, src, fam, tuc, ents):
    rec = dict(registros=0, cod_valido=0, cod_zero_nao_informado=0, cod_desconhecido=0, cod_nulo=0, kva_eq=0.0,
               vinculo_un=0, kva_un=0.0, un_com_potencia=0, diverge_eq_un_1pct=0, com_ventilacao_forcada=0, sem_campo_potencia=0, entidades={})
    for e in ents:
        p = path(src, e)
        if not p.exists():
            continue
        cols = {r[0] for r in con.execute('DESCRIBE SELECT * FROM read_parquet(?)', [str(p)]).fetchall()}
        where = f"WHERE trim(CAST(TUC AS VARCHAR)) = '{tuc}'" if tuc and 'TUC' in cols else ('' if not tuc else 'WHERE false')
        n = con.execute(f'SELECT count(*) FROM read_parquet(?) {where}', [str(p)]).fetchall()[0][0]
        if not n:
            continue
        rec['entidades'][e] = n; rec['registros'] += n
        if 'POT_NOM' not in cols:
            rec['sem_campo_potencia'] += n
            continue
        con.execute(f"CREATE OR REPLACE TEMP TABLE q AS SELECT trim(CAST(POT_NOM AS VARCHAR)) cod, "
                    f"{'trim(CAST(' + LINK[e][0] + ' AS VARCHAR))' if e in LINK and LINK[e][0] in cols else 'NULL::VARCHAR'} un, "
                    f"{'(coalesce(TRY_CAST(POT_F01 AS DOUBLE),0) > 0 OR coalesce(TRY_CAST(POT_F02 AS DOUBLE),0) > 0)' if 'POT_F01' in cols else 'false'} vf "
                    f"FROM read_parquet(?) {where}", [str(p)])
        con.execute('CREATE OR REPLACE TEMP TABLE q2 AS SELECT q.*, t.pot FROM q LEFT JOIN tpot t ON t.cod = q.cod')
        a = con.execute("SELECT count(*) FILTER (WHERE pot > 0), count(*) FILTER (WHERE pot = 0), count(*) FILTER (WHERE cod IS NOT NULL AND cod <> '' AND pot IS NULL), "
                        "count(*) FILTER (WHERE cod IS NULL OR cod = ''), coalesce(sum(pot) FILTER (WHERE pot > 0), 0), count(*) FILTER (WHERE vf) FROM q2").fetchall()[0]
        rec['cod_valido'] += a[0]; rec['cod_zero_nao_informado'] += a[1]; rec['cod_desconhecido'] += a[2]; rec['cod_nulo'] += a[3]
        rec['kva_eq'] += float(a[4]); rec['com_ventilacao_forcada'] += a[5]
        if e in LINK:
            fk, un, scale = LINK[e]; pu = path(src, un)
            if fk in cols and pu.exists():
                ucols = {r[0] for r in con.execute('DESCRIBE SELECT * FROM read_parquet(?)', [str(pu)]).fetchall()}
                if 'POT_NOM' in ucols:
                    # installation power is counted once per installation (an installation may hold several equipment units)
                    b = con.execute(f"""WITH u AS (SELECT trim(CAST(COD_ID AS VARCHAR)) k, TRY_CAST(POT_NOM AS DOUBLE) * {scale} kva FROM read_parquet(?)),
                        j AS (SELECT q2.*, u.kva FROM q2 JOIN u ON u.k = q2.un)
                        SELECT count(*), (SELECT coalesce(sum(kva), 0) FROM u WHERE k IN (SELECT DISTINCT un FROM q2) AND kva > 0),
                               count(*) FILTER (WHERE kva > 0),
                               count(*) FILTER (WHERE pot > 0 AND kva > 0 AND abs(pot - kva) > 0.01 * kva) FROM j""", [str(pu)]).fetchall()[0]
                    rec['vinculo_un'] += b[0]; rec['kva_un'] += float(b[1]); rec['un_com_potencia'] += b[2]; rec['diverge_eq_un_1pct'] += b[3]
    return rec


def run():
    t0 = time.monotonic()
    OUT.mkdir(parents=True, exist_ok=True)
    tpot, dsha = dda()
    con = duckdb.connect(); con.execute("SET memory_limit='768MB'; SET threads=1")
    con.execute('CREATE TEMP TABLE tpot(cod VARCHAR, pot DOUBLE)')
    con.executemany('INSERT INTO tpot VALUES (?, ?)', [(k, v) for k, v in tpot.items() if v is not None])
    qty = contract_qty()
    dists = sorted({d for d, _, _ in qty})
    rows, errors = [], []
    for d in dists:
        srcs = {s['year']: s for s in resolve_sources(d, 'trafo_dist') if not s.get('error')}
        for fam, (concept, tuc, ents) in FAMILIAS.items():
            for y, s in sorted(srcs.items()):
                try:
                    r = audit_one(con, s, fam, tuc, ents)
                except Exception as e:
                    errors.append(dict(DIST=d, ano=y, familia=fam, erro=str(e))); continue
                cq, est = qty.get((d, concept, y), (None, None))
                val = r['registros'] and r['cod_valido'] == r['registros']
                rows.append(dict(DIST=d, ano=y, familia=fam, conceito_contrato=concept, item=s['item'], quantidade_contrato=cq, estado_contrato=est,
                                 registros_auditados=r['registros'], quantidade_confere_contrato=(cq is not None and abs(cq - r['registros']) < .5),
                                 cod_potencia_valido=r['cod_valido'], cod_nao_informado=r['cod_zero_nao_informado'], cod_desconhecido=r['cod_desconhecido'],
                                 cod_nulo=r['cod_nulo'], sem_campo_potencia=r['sem_campo_potencia'],
                                 cobertura_potencia_valida=r['cod_valido'] / r['registros'] if r['registros'] else None,
                                 kva_aparente_eq=round(r['kva_eq'], 3), vinculo_instalacao=r['vinculo_un'], kva_aparente_instalacao=round(r['kva_un'], 3),
                                 instalacoes_com_potencia=r['un_com_potencia'], diverge_eq_instalacao_mais_1pct=r['diverge_eq_un_1pct'],
                                 com_ventilacao_forcada_nao_somada=r['com_ventilacao_forcada'], entidades=json.dumps(r['entidades']),
                                 gate_liberacao_experimental=bool(val and cq is not None and abs(cq - r['registros']) < .5)))
        print(d, len(rows), round(time.monotonic() - t0), flush=True)
    con.close()
    write_csv(OUT / 'POTENCIA_POR_DIST_ANO.csv', rows)
    matrix = summarize(rows)
    write_csv(OUT / 'MATRIZ_POTENCIAS.csv', matrix)
    atomic(OUT / 'MANIFESTO_POTENCIA.json', dict(dda_sha256=dsha, contrato_sha256=digest(CONTRACT), erros=errors, linhas=len(rows),
                                                 segundos=round(time.monotonic() - t0, 1)))
    return matrix


SEMANTICA = {
    'trafo_dist_565': ('aparente', 'kVA', 'EQTRMT/EQTRAT.POT_NOM -> TPOTAPRT; UNTRMT.POT_NOM kVA; UNTRAT.POT_NOM MVA x1000'),
    'trafo_forca_570': ('aparente', 'kVA', 'EQTRAT/EQTRMT.POT_NOM -> TPOTAPRT; UNTRAT.POT_NOM MVA x1000; POT_F01/F02 (ventilacao forcada) nao somadas'),
    'trafo_medida_575': ('nao_aplicavel', None, 'EQTRM nao tem campo de potencia (transformador de instrumento: relacao e classe de exatidao, nao potencia de transformacao)'),
    'reguladores': ('aparente', 'kVA', 'EQRE.POT_NOM -> TPOTAPRT (kVA); EQRE.COR_NOM e corrente (A), nao potencia'),
}


def plausibility(rows):
    """National 2025 sums of the gated DIST and the value quantiles of EQRE.POT_NOM (all 2025 publications)."""
    import glob
    tpot, _ = dda()
    con = duckdb.connect(); con.execute('CREATE TEMP TABLE t(cod VARCHAR, pot DOUBLE)')
    con.executemany('INSERT INTO t VALUES (?, ?)', [(k, v) for k, v in tpot.items() if v is not None])
    fs = glob.glob('D:/NUCLEO_BDGD_2025/staging_parquet/DIST=*/DATA_BASE=2025-12-31/entidade=EQRE/part-0.parquet')
    q = con.execute(f"SELECT quantile_cont(t.pot, [0.1, 0.5, 0.9]) FROM read_parquet({fs!r}, union_by_name=true) e "
                    "JOIN t ON t.cod = trim(CAST(e.POT_NOM AS VARCHAR)) WHERE t.pot > 0").fetchall()[0][0] if fs else None
    con.close()
    g = lambda fam: sum(r['kva_aparente_eq'] for r in rows if r['familia'] == fam and r['ano'] == 2025 and r['gate_liberacao_experimental'])
    return dict(soma_reguladores_2025=g('reguladores'), soma_trafo_dist_2025=g('trafo_dist_565'), soma_trafo_forca_2025=g('trafo_forca_570'), quantis_kva_2025=q)


def summarize(rows):
    plaus = plausibility(rows)
    out = []
    for fam, (grandeza, unit, campo) in SEMANTICA.items():
        rr = [r for r in rows if r['familia'] == fam]
        n = sum(r['registros_auditados'] for r in rr)
        withpow = sum(r['registros_auditados'] - r['sem_campo_potencia'] for r in rr)
        valid = sum(r['cod_potencia_valido'] for r in rr)
        gate = [r for r in rr if r['gate_liberacao_experimental']]
        by_d = defaultdict(list)
        for r in gate:
            by_d[r['DIST']].append(r['ano'])
        series = {d: ys for d, ys in by_d.items() if len(ys) >= 2}
        if grandeza == 'nao_aplicavel' or (n and withpow == 0):
            status, why = 'nao_aplicavel', SEMANTICA[fam][2]
        elif not n:
            status, why = 'sem_registros', 'nenhum registro da familia nas publicacoes auditadas'
        elif fam == 'reguladores' and plaus and plaus['soma_reguladores_2025'] > plaus['soma_trafo_dist_2025']:
            status = 'bloqueado_semantica_nao_homogenea'
            why = (f"codigos validos ({valid}/{withpow}), mas os valores misturam potencia propria e passante (p10/p50/p90 = {plaus['quantis_kva_2025']} kVA) e a soma "
                   f"nacional 2025 ({plaus['soma_reguladores_2025']:.0f} kVA) supera toda a transformacao de distribuicao ({plaus['soma_trafo_dist_2025']:.0f} kVA): "
                   "nao e estoque aditivo. Teste para liberar: classificar cada registro por POT_NOM contra raiz(3) x tensao do circuito x COR_NOM (TCOR) "
                   "e liberar so DIST com convencao unica comprovada")
        elif series:
            status = 'liberacao_experimental_proposta' if fam != 'trafo_dist_565' else 'experimental_em_uso (nivel A)'
            why = f'{len(series)} DIST com >= 2 competencias que passam o gate (todo registro com codigo de potencia valido e quantidade igual a do contrato)'
        else:
            status, why = 'bloqueado', 'nenhuma DIST com >= 2 competencias que passem o gate de potencia valida'
        out.append(dict(familia=fam, grandeza=grandeza, unidade=unit, campos_e_dominio=campo, conversao='nenhuma (kVA, kW e kVAr nao sao convertidos)',
                        dist_ano_auditados=len(rr), registros=n, registros_com_campo_potencia=withpow, cobertura_codigo_valido=valid / withpow if withpow else None,
                        dist_ano_no_gate=len(gate), dist_com_2_ou_mais_competencias_no_gate=len(series),
                        dist_ano_quantidade_confere_contrato=sum(1 for r in rr if r['quantidade_confere_contrato']),
                        kva_eq_2025=sum(r['kva_aparente_eq'] for r in gate if r['ano'] == 2025) if grandeza == 'aparente' else None,
                        kva_instalacao_2025=sum(r['kva_aparente_instalacao'] for r in gate if r['ano'] == 2025) if grandeza == 'aparente' else None,
                        status=status, motivo=why))
    out += [dict(familia='bancos_capacitores', grandeza='reativa', unidade='kVAr', campos_e_dominio='UNCRBT/UNCRMT/UNCRAT.POT_NOM -> TPOTRTV',
                 conversao='nenhuma', status='fora_do_escopo_desta_auditoria', motivo='potencia reativa registrada no DDA; nao convertida para kVA/kW; sem extracao nesta etapa'),
            dict(familia='geradores', grandeza='ativa', unidade='kW', campos_e_dominio='UGBT/UGMT/UGAT.POT_INST (kW)', conversao='nenhuma',
                 status='fora_do_escopo_desta_auditoria', motivo='potencia ativa instalada de geracao; nao somavel a kVA de transformacao')]
    return out


if __name__ == '__main__':
    import sys
    if '--resumo' in sys.argv:      # recompute the matrix from the saved per-DIST audit (no re-reading of the Parquets)
        rr = [dict(r, **{k: (int(r[k]) if k in ('DIST', 'ano', 'registros_auditados', 'sem_campo_potencia', 'cod_potencia_valido') else float(r[k]) if k.startswith('kva_') else r[k] == 'True' if k in ('gate_liberacao_experimental', 'quantidade_confere_contrato') else r[k]) for k in r})
              for r in csv.DictReader(open(OUT / 'POTENCIA_POR_DIST_ANO.csv', encoding='utf-8'))]
        m = summarize(rr); write_csv(OUT / 'MATRIZ_POTENCIAS.csv', m)
    else:
        m = run()
    print(json.dumps([{k: x.get(k) for k in ('familia', 'grandeza', 'status', 'dist_com_2_ou_mais_competencias_no_gate', 'cobertura_codigo_valido')} for x in m], ensure_ascii=False, indent=1, default=str))
