"""Feature registry: statistical population, unit, dependencies, coverage, temporal availability, origin and
eligibility per asset/metric. The declaration is static; coverage and availability are measured from the panel."""
import csv
from dataclasses import dataclass, asdict
from pathlib import Path
from .features import FEATURES
from .runner import atomic, fingerprint

# future_policy: how a 2026-2030 value may legitimately be produced (see future.py). Nothing here invents a projection.
#   engine_estimate   -> the engine itself derives it (e.g. recursive stock path), labelled as such
#   scenario_required -> only from an explicit scenario assumption supplied in configuration
#   official_required -> only from an ingested official projection; absent => unavailable
#   static_context    -> census-based constant; carrying it forward is an explicit, labelled engine choice
@dataclass(frozen=True)
class FeatureSpec:
    name: str
    population: str
    unit: str
    dependencies: tuple
    origin: str
    source: str
    availability: str
    unit_kind: tuple              # territorial units for which the feature is defined
    assets: tuple                 # 'asset_metric' ids, '*' for all
    future_policy: str
    status: str = 'implemented'   # implemented | source_not_obtained
    source_variable: str = ''     # variable in ORIGINAL units from which the model feature is derived
    original_unit: str = ''       # unit of the source variable (futures are projected here, then transformed)
    transform: str = 'identity'   # identity | log1p, applied AFTER any projection
    nonnegative: bool = True


SPECS = (
    FeatureSpec('log_stock', 'territorial unit x year, stock at t-1 of the same publication series', 'ln(1 + stock in the asset unit)',
                ('target series', 'publication availability'), 'internal', 'BDGD aggregate of the asset (checkpointed Parquet)',
                'revision availability of the t-1 publication', ('municipality', 'conjunto'), ('*',), 'engine_estimate', source_variable='stock', original_unit='asset unit (customers, items, kVA or km)', transform='log1p'),
    FeatureSpec('urban_share', 'municipality x year, UCBT customers with known TARE area', 'fraction UB/(UB+NU), known customers only',
                ('UCBT.ARE_LOC', 'TARE domain DDA M10 v1.1', 'min known coverage 0.99'), 'internal', 'UCBT aggregate',
                'revision availability of the t-1 publication', ('municipality', 'conjunto'), ('ucbt_quantidade', 'trafo_dist_quantidade', 'trafo_dist_potencia_kva', 'rede_mt_extensao_km'), 'engine_estimate', source_variable='urban_share', original_unit='fraction', transform='identity'),
    FeatureSpec('log_energy_per_client', 'municipality x year, UCBT customers with complete 12-month energy', 'ln(1 + kWh per client per year)',
                ('UCBT.ENE_01..12', 'UC-v3 identity COD_ID+PN_CON'), 'internal', 'UCBT aggregate',
                'revision availability of the t-1 publication', ('municipality', 'conjunto'), ('ucbt_quantidade', 'trafo_dist_quantidade', 'trafo_dist_potencia_kva', 'rede_mt_extensao_km'), 'engine_estimate', source_variable='energy_per_client', original_unit='kWh per client per year', transform='log1p'),
    FeatureSpec('log_population', 'municipality x year', 'ln(1 + persons)', ('IBGE Census 2022 / annual estimates', 'MUN code'), 'external',
                'IBGE SIDRA 4709 and 6579', 'release date per vintage; downloads are not backdated', ('municipality',),
                ('ucbt_quantidade', 'trafo_dist_quantidade', 'trafo_dist_potencia_kva'), 'official_required', source_variable='population', original_unit='persons', transform='log1p'),
    FeatureSpec('population_growth_census', 'municipality (static between censuses)', 'fraction per year, compound 2010-2022',
                ('population_census_2010', 'population 2022'), 'external', 'IBGE SIDRA 1378 + 4709', 'Census 2022 release 2023-08-31',
                ('municipality',), ('ucbt_quantidade', 'trafo_dist_quantidade', 'trafo_dist_potencia_kva'), 'static_context', source_variable='population_growth_census', original_unit='fraction per year', transform='identity', nonnegative=False),
    FeatureSpec('log_gdp', 'municipality x year', 'ln(1 + thousand BRL, current prices)', ('IBGE municipal GDP',), 'external', 'IBGE SIDRA 5938',
                'releases 2023-12-15 (2021) and 2025-12-19 (2022-2023)', ('municipality',),
                ('ucbt_quantidade', 'trafo_dist_quantidade', 'trafo_dist_potencia_kva'), 'scenario_required', source_variable='gdp', original_unit='thousand BRL current', transform='log1p'),
    FeatureSpec('dec', 'conjunto x year (consumer set), ANEEL continuity', 'hours per consumer', ('ANEEL DEC by conjunto', 'CONJ link'),
                'external', 'ANEEL open data (not obtained)', 'not available', ('conjunto',), ('rede_mt_extensao_km',), 'official_required',
                'source_not_obtained', source_variable='dec', original_unit='hours per consumer', transform='identity'),
    FeatureSpec('fec', 'conjunto x year (consumer set), ANEEL continuity', 'interruptions per consumer', ('ANEEL FEC by conjunto', 'CONJ link'),
                'external', 'ANEEL open data (not obtained)', 'not available', ('conjunto',), ('rede_mt_extensao_km',), 'official_required',
                'source_not_obtained', source_variable='fec', original_unit='interruptions per consumer', transform='identity'),
    # Cross-family features (values at t-1 from another asset family at the same territorial unit; see shared.py)
    FeatureSpec('log_ucbt_clients', 'unit x year, active UCBT customers (UC-v3) at t-1', 'ln(1 + customers)', ('UCBT.COD_ID+PN_CON', 'UCBT.MUN or UCBT.CONJ'),
                'internal', 'UCBT aggregate (cross-family)', 'availability of the UCBT publication at t-1', ('municipality', 'conjunto'),
                ('trafo_dist_quantidade', 'trafo_dist_potencia_kva', 'rede_mt_extensao_km'), 'engine_estimate',
                source_variable='ucbt_clients', original_unit='customers', transform='log1p'),
    FeatureSpec('log_trafo_count', 'unit x year, TUC 565 transformers linked EQ->UN at t-1', 'ln(1 + items)', ('EQTRMT/EQTRAT.TUC', 'UNTRMT/UNTRAT.MUN or CONJ'),
                'internal', 'transformer aggregate (cross-family)', 'availability of the transformer publication at t-1', ('municipality', 'conjunto'),
                ('trafo_dist_potencia_kva', 'rede_mt_extensao_km'), 'engine_estimate',
                source_variable='trafo_count', original_unit='items', transform='log1p'),
    FeatureSpec('log_trafo_kva', 'unit x year, nominal kVA of TUC 565 transformers at t-1', 'ln(1 + kVA)', ('UNTRMT.POT_NOM kVA', 'UNTRAT.POT_NOM MVA x 1000'),
                'internal', 'transformer aggregate (cross-family; experimental power)', 'availability of the transformer publication at t-1',
                ('municipality', 'conjunto'), ('trafo_dist_quantidade', 'rede_mt_extensao_km'), 'engine_estimate',
                source_variable='trafo_kva', original_unit='kVA', transform='log1p'),
    FeatureSpec('log_clients_per_trafo', 'unit x year, declared ratio customers / TUC 565 transformers at t-1', 'ln(1 + customers per transformer)',
                ('ucbt_clients', 'trafo_count'), 'internal', 'ratio of two aggregates', 'later of the two publication availabilities',
                ('municipality', 'conjunto'), ('trafo_dist_quantidade', 'trafo_dist_potencia_kva', 'rede_mt_extensao_km'), 'engine_estimate',
                source_variable='clients_per_trafo', original_unit='customers per transformer', transform='log1p'),
    FeatureSpec('log_kva_per_client', 'unit x year, declared ratio nominal kVA / customers at t-1', 'ln(1 + kVA per customer)',
                ('trafo_kva', 'ucbt_clients'), 'internal', 'ratio of two aggregates (experimental power)', 'later of the two publication availabilities',
                ('municipality', 'conjunto'), ('trafo_dist_quantidade', 'trafo_dist_potencia_kva', 'rede_mt_extensao_km'), 'engine_estimate',
                source_variable='kva_per_client', original_unit='kVA per customer', transform='log1p'),
    # Within-snapshot activity: read from the t-1 publication itself (no later snapshot), so it is available exactly when the stock is.
    FeatureSpec('recent_connection_share', 'municipality x year, active UCBT customers (UC-v3) at t-1', 'fraction of active UCs connected in the 12 months up to the data-base',
                ('UCBT.DAT_CON (dd/mm/yyyy)', 'UCBT.SIT_ATIV', 'UC-v3 identity COD_ID+PN_CON'), 'internal', 'UCBT aggregate of the t-1 snapshot',
                'revision availability of the t-1 publication', ('municipality',), ('ucbt_quantidade',), 'scenario_required',
                source_variable='connections_12m / active customers', original_unit='fraction', transform='identity'))
UNIT_KIND = {'ucbt_quantidade': 'municipality', 'trafo_dist_quantidade': 'municipality', 'trafo_dist_potencia_kva': 'municipality',
             'rede_mt_extensao_km': 'conjunto'}


def check_alignment():
    if tuple(s.name for s in SPECS) != FEATURES:
        raise ValueError('registry and FEATURES are out of sync')


def eligible_for(spec, asset):
    """Static eligibility: asset listed and the asset's territorial unit is one the feature is defined for."""
    if spec.status != 'implemented':
        return False, spec.status
    if UNIT_KIND[asset] not in spec.unit_kind:
        return False, 'unit_mismatch:' + UNIT_KIND[asset]
    if '*' not in spec.assets and asset not in spec.assets:
        return False, 'not_defined_for_asset'
    return True, 'eligible'


def build(rows, asset, mode_gate=None):
    """Registry rows for one asset with coverage measured on `rows` (panel rows with x/feature_meta)."""
    from .externals import feature_allowed
    check_alignment()
    out = []
    for i, spec in enumerate(SPECS):
        ok, why = eligible_for(spec, asset)
        n = len(rows)
        have = [r for r in rows if i < len(r['x']) and r['x'][i] is not None]
        meta = [r.get('feature_meta', {}).get(spec.name) for r in have]
        avail = sorted({m['available'] for m in meta if m and m.get('available')})
        d = asdict(spec)
        d.update(index=i, asset=asset, unit_kind_of_asset=UNIT_KIND[asset], statically_eligible=ok, static_reason=why,
                 rows=n, rows_with_value=len(have), coverage=len(have) / n if n else None,
                 point_in_time_rows=sum(feature_allowed(r, i, 'point_in_time') for r in have),
                 retrospective_rows=sum(feature_allowed(r, i, 'reconciled_retrospective') for r in have),
                 availability_min=avail[0] if avail else None, availability_max=avail[-1] if avail else None)
        d['dependencies'] = ' | '.join(spec.dependencies)
        d['unit_kind'] = ','.join(spec.unit_kind)
        d['assets'] = ','.join(spec.assets)
        out.append(d)
    return out


def write(registry_rows, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / 'FEATURE_REGISTRY.csv').open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, list(registry_rows[0]))
        w.writeheader()
        w.writerows(registry_rows)
    atomic(directory / 'FEATURE_REGISTRY.json', dict(version=fingerprint(registry_rows)[:16], rows=registry_rows))
