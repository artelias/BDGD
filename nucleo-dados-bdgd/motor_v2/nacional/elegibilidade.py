"""One eligibility policy for both levels (A territorial, B distributor), read from the national contract WITHOUT changing it.

Two separate properties:

  STOCK (a physical value observed at a data-base) is eligible when
    * estado is `observado` or `zero_verificado` and the value exists;
    * dataBase is 31/12 of the competence (BASE.DAT_FNL, the regulatory competence);
    * the cell may be summed (`nao_somar_em_agregados` false). A cell flagged nao_somar (e.g. Energisa Nova Friburgo 2022,
      incorporated by Energisa MR on 2022-11-30 and already inside its successor) is neither modelled nor projected nor summed.
  `intervalo_base` = INTERVALO_NAO_ANUAL does NOT make a stock ineligible: the class only says BASE.DAT_INC is not 01/01
  (01/12 of the previous year, or 01/12 of the same year) while DAT_FNL is the correct 31/12. DAT_INC bounds the period of
  the flow fields (monthly energy); the physical inventory is the snapshot at DAT_FNL. It is kept as a recorded caveat.

  TRANSITION t-1 -> t (growth, training target, scenario envelope) is eligible when both stocks are eligible, the two
  data-bases are 31/12 of consecutive years (exactly one year apart) and the contract records no rupture at t. A transition
  touching an INTERVALO_NAO_ANUAL cell is eligible WITH the caveat `intervalo_base_nao_anual`. Empirical check (contract,
  2022-2025, all 25 concepts, median +- 5 MAD of the national cross-section with the scenario MAD floor 0.02): 7.7% of the 196
  such transitions are atypical against 8.1% of the 6,132 others; 12 of the 15 atypical ones are Amazonas Energia 2022 -> 2023, a
  level shift of the 2022 publication across concepts (stable from 2023 on) that Equatorial GO 2022, with the same 31-day BASE,
  does not show; without it the share is 1.7% (reconciliacao_ab/AUDITORIA_INTERVALO_NAO_ANUAL.csv).

  A transition is also NOT eligible when the DIST is the destination of a corporate succession (incorporation, official event in
  output-historico/2022-2025/eventos_sucessao.csv) effective between the two data-bases: the contract series stays on the
  original publication perimeter and does not flag it as a rupture, so the step is a perimeter change, not growth (Energisa PB
  2022 -> 2023 absorbs Energisa Borborema, EPB_EBO_2023). Level A already holds those units out through the perimeter bridge.

The policy does not decide the human homologation pending in auditoria/fase4 (public products); it only governs the internal,
experimental Motor V2 layer."""
import csv
from datetime import date
from functools import lru_cache
from pathlib import Path

from . import CONTRACT

VERSAO = 'elegibilidade-v2 (estoque x transicao; INTERVALO_NAO_ANUAL = ressalva, nao exclusao; sucessao societaria = transicao nao comparavel)'
EVENTOS = Path('D:/NUCLEO_BDGD_2025/output-historico/2022-2025/eventos_sucessao.csv')
# Level A asset -> contract concept whose cell governs the same publication (DIST, competence)
CONCEITO_A = {'ucbt_quantidade': 'consumidores', 'trafo_dist_quantidade': 'trafo_dist', 'trafo_dist_potencia_kva': 'trafo_dist',
              'rede_mt_extensao_km': 'rede_mt', 'rede_bt_extensao_km': 'rede_bt'}


def cells(path=CONTRACT):
    """{(dist, concept, year): contract row} of the national contract (read only)."""
    with open(path, encoding='utf-8-sig') as f:
        return {(int(r['dist']), r['conceitoId'], int(r['ano'])): r for r in csv.DictReader(f)}


def estoque(r):
    """-> (eligible, reason or None, caveats) for one contract row (None = no cell)."""
    if r is None:
        return False, 'sem_celula', []
    y = int(r['ano'])
    if r['estado'] not in ('observado', 'zero_verificado') or r['valor'] == '':
        return False, f"estado={r['estado']}" + (f" lacuna={r['tipo_lacuna']}" if r.get('tipo_lacuna') else ''), []
    if r['dataBase'] != f'{y}-12-31':
        return False, f"data-base {r['dataBase']} != {y}-12-31", []
    if r['nao_somar_em_agregados'] == 'true':
        return False, 'nao_somar_em_agregados (sucessao/perimetro ja contido em outra DIST)', []
    cav = []
    if r['intervalo_base'] == 'INTERVALO_NAO_ANUAL':
        cav.append('intervalo_base_nao_anual')
    if r['intervalo_base'] not in ('INTERVALO_ANUAL_COMPATIVEL', 'INTERVALO_NAO_ANUAL', ''):
        cav.append('intervalo_base=' + r['intervalo_base'])
    return True, None, cav


@lru_cache(maxsize=1)
def sucessoes():
    """{(destination DIST, competence year in which the event takes effect): event id}; effective in (31/12/(t-1), 31/12/t] -> t."""
    out = {}
    if EVENTOS.exists():
        with open(EVENTOS, encoding='utf-8') as f:
            for r in csv.DictReader(f):
                if r['dist_destino_2025'] and r['data_efetivacao']:
                    out[int(r['dist_destino_2025']), date.fromisoformat(r['data_efetivacao']).year] = r['evento_id']
    return out


def transicao(prev, cur, sucessao=True):
    """-> (eligible, reason or None, caveats) for the step prev -> cur (contract rows of the same DIST and concept).
    sucessao=False reproduces the rule before the succession check (only to measure the change)."""
    a, why_a, cav_a = estoque(prev)
    b, why_b, cav_b = estoque(cur)
    if not a:
        return False, 'estoque t-1 inelegivel: ' + why_a, []
    if not b:
        return False, 'estoque t inelegivel: ' + why_b, []
    d0, d1 = date.fromisoformat(prev['dataBase']), date.fromisoformat(cur['dataBase'])
    if (d0.month, d0.day, d1.month, d1.day) != (12, 31, 12, 31) or d1.year - d0.year != 1:
        return False, f"datas-base {prev['dataBase']} -> {cur['dataBase']} nao sao 31/12 consecutivos", []
    if cur['ruptura_desde_ano_anterior'] == 'true':
        return False, 'ruptura no contrato: ' + (cur.get('tipo_ruptura') or 'sem tipo'), []
    ev = sucessoes().get((int(cur['dist']), d1.year)) if sucessao and cur.get('dist') else None
    if ev:
        return False, f'sucessao societaria {ev} entre as datas-base (mudanca de perimetro, nao crescimento)', []
    return True, None, sorted(set(cav_a) | set(cav_b))


def legado_b(r):
    """Rule of the first national run (d4982e8) for Level B, kept only to measure what changed."""
    return r is not None and r['estado'] in ('observado', 'zero_verificado') and r['valor'] != '' \
        and r['intervalo_base'] == 'INTERVALO_ANUAL_COMPATIVEL' and r['nao_somar_em_agregados'] != 'true'
