"""Level B (distributor) experimental series of the power metrics released by the audits, with the same selection and scenarios.

    python -m motor_v2.nacional.potencia_b

Concepts (never summed with each other, no kVA <-> kW <-> kVAr conversion):
  trafo_forca_kva           TUC 570 power transformers, apparent power EQTRAT/EQTRMT.POT_NOM -> TPOTAPRT (kVA); forced-ventilation
                            ratings POT_F01/F02 are never added (motor_v2/nacional/potencia.py).
  reguladores_kva_propria   voltage regulators, OWN rating, only DIST whose records follow that convention (reguladores.py).
  reguladores_kva_passante  voltage regulators, THROUGHPUT rating, idem.

A stock (DIST, year) is usable when
  * the potencia.py gate passes: every record carries a valid power code and the record count equals the contract count;
  * the contract cell of the same concept and competence is an eligible stock (elegibilidade.estoque: observed, 31/12, summable);
  * TUC 570: the equipment code and the linked installation agree within TOL_EQ_UN (|EQ - UN| / UN); without the installation
    link the agreement cannot be checked and the stock is not used;
  * the DIST has >= 2 such stocks (release rule of potencia.py), and a regulator DIST keeps one convention in every usable year;
  * regulators: the DIST x year follows the concept's convention (reguladores.convencao) and the value is the kVA of the records
    of that convention (the records outside it, at most 14.5 %, are left out and reported).
A transition is comparable under elegibilidade.transicao on the contract count cells (31/12 consecutive, no rupture, no corporate
succession) and, for TUC 570, when the log change of kVA stays within MAX_GAP of the log change of the unit count (a larger gap
is a change of registration, not growth; for regulators the count is the records in the convention). Features of the ML pools come from the contract (consumers, MV network) as in Level B."""
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

from . import ROOT_OUT, elegibilidade
from . import distribuidora as B
from .relatorio import write_csv

OUT = ROOT_OUT / 'distribuidora_potencia'
POT = ROOT_OUT / 'potencia'
TOL_EQ_UN = 0.05
MAX_GAP = 0.5
CONCEITOS = {
    'trafo_forca_kva': dict(base='trafo_forca', metrica='potencia_kva', unidade='kVA', natureza='continuous_power',
                            grandeza='aparente nominal (sem ventilacao forcada)'),
    'reguladores_kva_propria': dict(base='reguladores', metrica='potencia_propria_kva', unidade='kVA', natureza='continuous_power',
                                    grandeza='aparente propria (placa do regulador)', convencao='PROPRIA'),
    'reguladores_kva_passante': dict(base='reguladores', metrica='potencia_passante_kva', unidade='kVA', natureza='continuous_power',
                                     grandeza='aparente passante (tensao x corrente nominal)', convencao='PASSANTE'),
}


def _f(v):
    return float(v) if v not in ('', None) else None


def estoques_tuc570(audit, contract):
    """{(d, y): (value, usable, reason, units)} for TUC 570 kVA from POTENCIA_POR_DIST_ANO rows (familia trafo_forca_570)."""
    out = {}
    for r in audit:
        d, y = int(r['DIST']), int(r['ano'])
        eq, un, n = _f(r['kva_aparente_eq']), _f(r['kva_aparente_instalacao']), int(r['registros_auditados'])
        ok, why, _ = elegibilidade.estoque(contract.get((d, 'trafo_forca', y)))
        if not ok:
            reason = 'contrato: ' + why
        elif r['gate_liberacao_experimental'] != 'True':
            reason = 'gate de potencia (codigo invalido ou quantidade != contrato)'
        elif not un or un <= 0:
            reason = 'sem vinculo com a instalacao (EQ x UN nao verificavel)'
        elif abs(eq - un) / un > TOL_EQ_UN:
            reason = f'EQ x UN divergem {abs(eq - un) / un:.1%} (> {TOL_EQ_UN:.0%})'
        else:
            reason = None
        out[d, y] = (eq, reason is None, reason, n)
    return out


def estoques_reguladores(linhas, contract, conv):
    out = {}
    for r in linhas:
        d, y = int(r['DIST']), int(r['ano'])
        ok, why, _ = elegibilidade.estoque(contract.get((d, 'reguladores', y)))
        kva = _f(r['kva_' + conv.lower()])
        if not ok:
            reason = 'contrato: ' + why
        elif r['gate_potencia'] not in (True, 'True'):
            reason = 'gate de potencia (codigo invalido ou quantidade != contrato)'
        elif r['convencao'] != conv:
            reason = f"convencao {r['convencao']} != {conv}"
        elif not kva:
            reason = 'sem kVA na convencao'
        else:
            reason = None
        out[d, y] = (kva, reason is None, reason, int(r['propria'] if conv == 'PROPRIA' else r['passante']))
    return out


MIN_COMPETENCIAS = 2


def liberar(stocks):
    """Release rule of a power series: >= MIN_COMPETENCIAS usable stocks in the DIST; regulators also need one convention in every
    usable year (a DIST usable in both conventions is blocked in both). Mutates and returns {concept: {(d, y): stock}}."""
    usable = {c: defaultdict(list) for c in stocks}
    for c, st in stocks.items():
        for (d, y), (v, ok, why, n) in st.items():
            if ok:
                usable[c][d].append(y)
    ambos = set(usable.get('reguladores_kva_propria', {})) & set(usable.get('reguladores_kva_passante', {}))
    for c, st in stocks.items():
        for (d, y), (v, ok, why, n) in list(st.items()):
            if not ok:
                continue
            if c.startswith('reguladores') and d in ambos:
                st[d, y] = (v, False, 'SEM_SEMANTICA_FISICA_HOMOGENEA: convencao muda entre competencias (propria e passante)', n)
            elif len(usable[c][d]) < MIN_COMPETENCIAS:
                st[d, y] = (v, False, f'HISTORICO_INSUFICIENTE: {len(usable[c][d])} competencia(s) utilizavel(is) < {MIN_COMPETENCIAS} exigidas para liberar a metrica', n)
    return stocks


def celulas(estoques, contract, base, gap_check):
    """Level-B cells of one power concept from its stocks; transition rule as in the module docstring."""
    cells = {}
    for (d, y), (v, ok, why, n) in sorted(estoques.items()):
        prev = estoques.get((d, y - 1))
        rup, cav = False, []
        if ok and prev and prev[1]:
            t_ok, t_why, cav = elegibilidade.transicao(contract.get((d, base, y - 1)), contract.get((d, base, y)))
            rup = not t_ok
            if t_ok and gap_check and prev[3] and n and prev[0] > 0 and v > 0:
                gap = abs((math.log(v) - math.log(prev[0])) - (math.log(n) - math.log(prev[3])))
                if gap > MAX_GAP:
                    rup, why = True, f'kVA e unidades variam com diferenca de {gap:.2f} em log (> {MAX_GAP})'
        c = contract.get((d, base, y)) or {}
        cells[d, y] = dict(value=v if ok else None, usable=ok, rupture=rup, estado='observado' if ok else 'nao_utilizavel',
                           status=c.get('status_homologacao'), item=c.get('publicacao_id'), lacuna=None if ok else why,
                           intervalo=c.get('intervalo_base'), nao_somar=c.get('nao_somar_em_agregados') == 'true', motivo=None if ok else why,
                           ressalvas=list(cav) + ([why] if ok and rup and why else []))
    return cells


def fonte(conceitos=None):
    """-> callable for distribuidora.run: the contract cells (features and the 25 concepts) plus the power concepts."""
    def build():
        cells, meta = B.load()
        contract = elegibilidade.cells()
        audit = list(csv.DictReader(open(POT / 'POTENCIA_POR_DIST_ANO.csv', encoding='utf-8')))
        stocks = {'trafo_forca_kva': estoques_tuc570([r for r in audit if r['familia'] == 'trafo_forca_570'], contract)}
        reg = POT / 'REGULADORES_CONVENCAO_POR_DIST_ANO.csv'
        if reg.exists():
            from .reguladores import ler
            lin = ler()
            for c in ('reguladores_kva_propria', 'reguladores_kva_passante'):
                stocks[c] = estoques_reguladores(lin, contract, CONCEITOS[c]['convencao'])
        for c, st in liberar(stocks).items():
            if conceitos and c not in conceitos:
                continue
            spec = CONCEITOS[c]
            for (d, y), cell in celulas(st, contract, spec['base'], True).items():
                cells[d, c, y] = cell
            meta[c] = dict(metrica=spec['metrica'], unidade=spec['unidade'], natureza=spec['natureza'])
        return cells, meta
    return build


def run():
    src = fonte()
    cells, meta = src()
    alvo = {(d, c) for (d, c, y), cell in cells.items() if c in CONCEITOS}
    res = B.run(only=alvo, fonte=lambda: (cells, meta))
    # series with no usable stock are recorded with the reason of every year, so the coverage matrix can classify them
    motivos = []
    for (d, c) in sorted(alvo):
        anos = {y: cells[d, c, y] for y in range(2022, 2026) if (d, c, y) in cells}
        motivos.append(dict(DIST=d, conceito=c, anos_utilizaveis=sum(1 for x in anos.values() if x['usable']),
                            motivos=json.dumps({y: x['motivo'] for y, x in anos.items() if not x['usable']}, ensure_ascii=False),
                            ressalvas=json.dumps({y: x['ressalvas'] for y, x in anos.items() if x['ressalvas']}, ensure_ascii=False)))
    B.write(res, OUT)
    write_csv(OUT / 'ESTOQUES_POTENCIA_B.csv', [dict(DIST=d, conceito=c, ano=y, valor=cell['value'], utilizavel=cell['usable'], ruptura=cell['rupture'],
                                                      motivo=cell['motivo'], ressalvas=json.dumps(cell['ressalvas'], ensure_ascii=False))
                                                 for (d, c, y), cell in sorted(cells.items()) if c in CONCEITOS])
    write_csv(OUT / 'SERIES_POTENCIA_B.csv', motivos)
    return dict(series=len(alvo), geradas=sum(1 for x in res['decisions'] if x['status_projecao'] == 'gerada'),
                bloqueadas=sum(1 for x in res['decisions'] if x['status_projecao'] != 'gerada'), segundos=res['provenance']['segundos'],
                por_conceito={c: sum(1 for x in res['decisions'] if x['conceito'] == c and x['status_projecao'] == 'gerada') for c in CONCEITOS})


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=False, indent=1))
