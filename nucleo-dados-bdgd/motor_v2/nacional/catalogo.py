"""Eligibility matrix of the WHOLE Motor Universal catalog (objective x metric), with what this run actually computed.

For every objective of motor_universal.registry (built from etl/bdgd2025/config/conceitos_2025.json) the matrix records: unit,
nature, entities, MCPSE/TUC filter, territorial route (field of the record itself, or the UN* installation linked to the EQ*
equipment), whether the national contract carries the series, Level B coverage (distributor series 2022-2025 with a comparable
transition / with a projection) and Level A (territorial extraction implemented, DIST extracted / projected). A metric the
contract does not publish and no extractor defines is BLOCKED with its reason; nothing is inferred without a source or link."""
import csv
import glob
import json
import os
from collections import Counter
from pathlib import Path

import duckdb

from . import ROOT_OUT
from .relatorio import write_csv
from ..runner import ROOT, read

LEVEL_A_MAP = {('consumidores', 'quantidade'): ('ucbt_quantidade', 'parcial: so UCBT (UCMT/UCAT fora do extrator territorial); municipio = UCBT.MUN'),
               ('trafo_dist', 'quantidade'): ('trafo_dist_quantidade', 'EQTRMT/EQTRAT TUC 565 -> UNTRMT/UNTRAT.MUN (vinculo bijetivo)'),
               ('trafo_dist', 'potencia_kva'): ('trafo_dist_potencia_kva', 'UNTRMT kVA / UNTRAT MVA x 1000 do vinculo bijetivo; experimental'),
               ('rede_mt', 'extensao_km'): ('rede_mt_extensao_km', 'SSDMT.COMP/1000 por SSDMT.CONJ'),
               ('rede_bt', 'extensao_km'): ('rede_bt_extensao_km', 'SSDBT.COMP/1000 por SSDBT.CONJ')}
# power metrics: decided by the separate power audit (potencia.py, MATRIZ_POTENCIAS.csv); status and reason per objective
BLOCKED = {('trafo_forca', 'potencia_kva'): ('liberacao_experimental_proposta', 'potencia APARENTE (kVA): EQTRAT/EQTRMT.POT_NOM -> TPOTAPRT, conferida com UNTRAT.POT_NOM (MVA x1000); 72 DIST com >= 2 competencias no gate (codigos validos e quantidade = contrato); POT_F01/F02 nao somadas; serie ainda nao projetada nesta execucao'),
           ('trafo_medida', 'potencia_kva'): ('nao_aplicavel', 'transformador de medida (TUC 575, EQTRM) nao tem campo de potencia: relacao e classe de exatidao, nao potencia de transformacao'),
           ('reguladores', 'potencia_kva'): ('bloqueado', 'EQRE.POT_NOM -> TPOTAPRT (kVA aparente) com codigos validos, mas valores misturam potencia propria e passante e a soma nacional supera a transformacao de distribuicao: semantica nao homogenea (MATRIZ_POTENCIAS.csv)')}
TERRITORIAL_FIELDS = ('MUN', 'CONJ', 'CTMT', 'CTAT', 'SUB')
LINKS = {'EQTRMT': 'UNTRMT', 'EQTRAT': 'UNTRAT', 'EQRE': 'UNREMT/UNREAT', 'EQSE': 'UNSEMT/UNSEAT/UNSEBT', 'EQCR': 'UNCRMT/UNCRAT/UNCRBT'}


def entity_fields(dist=26):
    c = duckdb.connect(); out = {}
    for p in sorted(glob.glob(f'D:/NUCLEO_BDGD_2025/staging_parquet/DIST={dist}/DATA_BASE=2025-12-31/entidade=*/part-0.parquet')):
        e = os.path.basename(os.path.dirname(p)).split('=')[1]
        cols = {r[0] for r in c.execute(f"DESCRIBE SELECT * FROM read_parquet('{p}')").fetchall()}
        out[e] = sorted(cols & set(TERRITORIAL_FIELDS))
    c.close()
    return out


def run():
    from motor_universal.registry import registry_from_catalog
    reg = registry_from_catalog(json.loads((ROOT / 'etl/bdgd2025/config/conceitos_2025.json').read_text(encoding='utf-8')))
    fields = entity_fields()
    b = list(csv.DictReader(open(ROOT_OUT / 'distribuidora' / 'DECISOES_B.csv', encoding='utf-8')))
    bres = list(csv.DictReader(open(ROOT_OUT / 'distribuidora' / 'RESULTADOS_CANDIDATOS_B.csv', encoding='utf-8')))
    a = list(csv.DictReader(open(ROOT_OUT / 'projecao' / 'DECISOES_A.csv', encoding='utf-8'))) if (ROOT_OUT / 'projecao' / 'DECISOES_A.csv').exists() else []
    contract = {(r['conceito'], r['metrica']) for r in b}
    rows = []
    for t in reg['objetivos']:
        key = (t['objetivo_id'], t['metrica'])
        ents = t['entidades']
        terr = {e: fields.get(e, []) for e in ents}
        via = {e: LINKS[e] for e in ents if e in LINKS}
        bb = [r for r in b if (r['conceito'], r['metrica']) == key]
        measured = {r['DIST'] for r in bres if (r['conceito'], r['metrica']) == key and r.get('previsoes') not in ('', '0', None)}
        aa_key = LEVEL_A_MAP.get(key)
        aa = [r for r in a if aa_key and r.get('ativo') and f"{r['ativo']}_{r['metrica']}" == aa_key[0]]
        status = 'bloqueado'
        if bb and any(r['status_projecao'] == 'gerada' for r in bb):
            status = 'distribuidora+territorial' if aa else 'distribuidora'
        elif aa:
            status = 'territorial'
        rows.append(dict(objetivo_id=t['objetivo_id'], nome=t['nome'], familia=t['familia'], metrica=t['metrica'], unidade=t['unidade'],
                         natureza='discrete_count' if t['metrica'] == 'quantidade' else 'continuous_capacity' if t['metrica'] == 'potencia_kva' else 'continuous_length',
                         entidades='|'.join(ents), filtro_mcpse=json.dumps(t.get('filtros') or {}, ensure_ascii=False),
                         campos_territoriais=json.dumps(terr), vinculo_instalacao=json.dumps(via), no_contrato_nacional=key in contract,
                         dist_com_serie_no_contrato=len({r['DIST'] for r in bb if r['ano_ancora']}),
                         dist_com_avaliacao_retrospectiva=len(measured),
                         dist_com_projecao_nivel_B=sum(1 for r in bb if r['status_projecao'] == 'gerada'),
                         nivel_A_extrator=aa_key[0] if aa_key else None, nivel_A_regra=aa_key[1] if aa_key else None,
                         dist_com_projecao_nivel_A=sum(1 for r in aa if r.get('status_projecao') == 'gerada'),
                         status=BLOCKED[key][0] if key in BLOCKED and status == 'bloqueado' else status,
                         motivo_bloqueio=BLOCKED[key][1] if key in BLOCKED else (None if status != 'bloqueado' else 'sem serie no contrato e sem extrator definido'),
                         nivel_A_pendente=None if aa_key else ('extracao territorial viavel por ' + ','.join(sorted({f for v in terr.values() for f in v})) +
                                                               ' mas nao implementada nesta execucao' if any(terr.values()) else
                                                               ('territorio so pelo vinculo ' + json.dumps(via) if via else 'entidade sem campo territorial'))))
    write_csv(ROOT_OUT / 'MATRIZ_ELEGIBILIDADE_CATALOGO.csv', rows)
    return rows


if __name__ == '__main__':
    r = run()
    print(json.dumps(Counter(x['status'] for x in r)))
