"""Explicit isolation of extraordinary BDGD bases (standard library only).

Ordinary  = the publication the national contract selected for a DIST/competence (2022-2025 annual series). Only ordinary data
            may reach indicators, tables, historical series, totals or any other public product.
Extraordinary = every other local base (another version of the same competence, an item outside the contract, a base of another
            data-base date, an unidentified file). It may feed research: features, change tracking and experimental candidates,
            never a public file, and never as an extra independent observation of a competence that the ordinary series covers.

Every observation carries provenance, competence, data-base, availability date, version and quality status (`Provenance`). An
extraordinary base is only usable at an origin date on or after the day it became available (no retroactive information)."""
import csv
from dataclasses import dataclass
from pathlib import Path

ORDINARY = 'ordinaria'
EXTRAORDINARY = 'extraordinaria'
ROOT = Path(__file__).resolve().parents[1]
# Everything the site or its contracts are built from. Research outputs may never be written under these roots.
PUBLIC_ROOTS = tuple(ROOT / p for p in ('web/public', 'web/src', 'output-historico', 'output-publicavel', 'motor_cenarios/saida', 'motor_cenarios/entrada'))
RESEARCH_ROOT = Path('D:/NUCLEO_BDGD_2025/motor_v2/pesquisa_extraordinaria')

# Roles an extraordinary base may play (never "public").
SENSITIVITY = 'sensibilidade_mesma_competencia'      # replaces/perturbs the ordinary version of the same competence: robustness only
NEW_TEMPORAL = 'observacao_temporal_extraordinaria'  # a competence no ordinary item covers: experimental training, flagged
UNUSABLE = 'inutilizavel'


class IsolationError(ValueError):
    pass


@dataclass(frozen=True)
class Provenance:
    item_id: str
    dist: str
    competencia: int | None
    data_base: str
    disponivel_em: str
    versao: str
    natureza: str
    tipo: str
    qualidade: str
    origem: str


def load(inventory_csv):
    """{item_id: Provenance} from INVENTARIO_PUBLICACOES_LOCAIS.csv (motor_v2.inventory)."""
    out = {}
    with open(inventory_csv, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            out[r['item_id']] = Provenance(item_id=r['item_id'], dist=r['dist'], competencia=int(r['competencia']) if r['competencia'] else None,
                                           data_base=r['data_base'], disponivel_em=r['disponivel_em'], versao=r['versao'],
                                           natureza=r['natureza'], tipo=r['tipo'], qualidade=r['status_inventario'] or 'nao_avaliada', origem=r['origem'])
    return out


def assert_public_safe(item_ids, inventory):
    """Raise unless every item feeding a public product is a known ORDINARY publication. Unknown items are refused too."""
    bad = sorted({i for i in item_ids if i and (i not in inventory or inventory[i].natureza != ORDINARY)})
    if bad:
        raise IsolationError(f'public product would use {len(bad)} non-ordinary or unknown item(s): {bad[:5]}')
    return True


def assert_contract_ordinary(contract_csv, inventory):
    """The national contract (source of the site's series) references ordinary items only."""
    with open(contract_csv, encoding='utf-8') as f:
        ids = {r['publicacao_id'] for r in csv.DictReader(f) if r['publicacao_id']}
    return assert_public_safe(ids, inventory)


def research_path(path):
    """A path where extraordinary-derived outputs may be written: under the research root and outside every public root."""
    p = Path(path).resolve()
    for public in PUBLIC_ROOTS:
        if p == public.resolve() or public.resolve() in p.parents:
            raise IsolationError(f'extraordinary output under a public root: {p}')
    if p != RESEARCH_ROOT.resolve() and RESEARCH_ROOT.resolve() not in p.parents:
        raise IsolationError(f'extraordinary output outside the research root {RESEARCH_ROOT}: {p}')
    return p


def usable_at(prov, origin_date):
    """An extraordinary base may inform an origin only from the day it became available; no date, no use."""
    if not prov.disponivel_em:
        return False
    return prov.disponivel_em[:10] <= origin_date


def training_role(prov, inventory):
    """Role of an extraordinary base in training. A second version of a competence that an ordinary item covers is NOT a new
    temporal observation: it may only be used for sensitivity (swap the version, compare). An unidentified base is unusable."""
    if prov.natureza == ORDINARY:
        raise IsolationError('ordinary publication has no extraordinary role')
    if prov.competencia is None or not prov.dist:
        return UNUSABLE
    covered = any(p.natureza == ORDINARY and p.dist == prov.dist and p.competencia == prov.competencia for p in inventory.values())
    return SENSITIVITY if covered else NEW_TEMPORAL


def plan(inventory):
    """One row per extraordinary base: role, availability and why it can or cannot be used."""
    rows = []
    for p in sorted(inventory.values(), key=lambda p: (p.dist, p.competencia or 0, p.item_id)):
        if p.natureza == ORDINARY:
            continue
        role = training_role(p, inventory)
        rows.append(dict(item_id=p.item_id, dist=p.dist, competencia=p.competencia, data_base=p.data_base, disponivel_em=p.disponivel_em,
                         versao=p.versao, tipo=p.tipo, qualidade=p.qualidade, papel=role, publico=False,
                         nova_observacao_temporal=role == NEW_TEMPORAL,
                         motivo={SENSITIVITY: 'mesma competência já coberta pela série ordinária: só sensibilidade/robustez, nunca observação adicional',
                                 NEW_TEMPORAL: 'competência sem item ordinário: treino experimental sinalizado, nunca produto público',
                                 UNUSABLE: 'DIST/competência não identificados'}[role]))
    return rows
