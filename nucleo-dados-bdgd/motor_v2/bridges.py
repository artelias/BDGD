"""Versioned perimeter bridges. A bridge documents a probable change of territorial perimeter between publications
(succession, absorption, split). Until a human marks it HOMOLOGATED:
  * the affected territorial units are quarantined (excluded from training and testing, never imputed);
  * records of the two companies are never summed, because they may overlap;
  * the engine never converts the perimeter change into expansion or into new connections."""
import json
from pathlib import Path
from .runner import fingerprint

STATUSES = ('PENDING_HOMOLOGATION', 'HOMOLOGATED', 'REJECTED')
KINDS = ('succession', 'absorption', 'split')
REQUIRED = ('id', 'version', 'kind', 'successor_dist', 'predecessor_dist', 'effective_year', 'entering_units', 'overlap_units',
            'status', 'evidence', 'policy')


def validate(bridge):
    missing = [k for k in REQUIRED if k not in bridge]
    if missing:
        raise ValueError('bridge missing fields: ' + ','.join(missing))
    if bridge['status'] not in STATUSES or bridge['kind'] not in KINDS:
        raise ValueError('invalid bridge status or kind')
    if bridge['status'] == 'HOMOLOGATED' and not bridge.get('decision'):
        raise ValueError('a HOMOLOGATED bridge needs a recorded human decision')
    if bridge['status'] != 'HOMOLOGATED' and bridge.get('decision'):
        raise ValueError('decision recorded on a bridge that is not homologated')
    return bridge


def load(directory):
    out = []
    for p in sorted(Path(directory).glob('*.json')):
        b = validate(json.loads(p.read_text(encoding='utf-8-sig')))
        b['_sha256'] = fingerprint({k: v for k, v in b.items() if not k.startswith('_')})
        out.append(b)
    ids = [b['id'] for b in out]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate bridge id')
    return out


def quarantine(bridges, dist, year, unit_kind=None):
    """Units of (dist, year) that must stay out of the model cohort: entering and overlapping units of any bridge that
    is not HOMOLOGATED. Returns {unit: bridge id}. A rejected bridge does not quarantine."""
    out = {}
    for b in bridges:
        if b['status'] == 'REJECTED' or b['successor_dist'] != dist or b['effective_year'] != year:
            continue
        if unit_kind and b.get('unit_kind', 'municipality') != unit_kind:
            continue
        if b['status'] == 'HOMOLOGATED':
            continue                      # homologated bridges are consumed by an explicit comparable-perimeter series, not here
        for u in list(b['entering_units']) + list(b['overlap_units']):
            out[u] = b['id']
    return out


def combine(successor, predecessor, bridge):
    """Sum of predecessor and successor stocks per unit, only for a HOMOLOGATED bridge and only when the unit sets
    are proven disjoint (overlap units must be declared and are then excluded, never double counted)."""
    if bridge['status'] != 'HOMOLOGATED':
        raise ValueError('bridge is not homologated: perimeters must not be combined')
    shared = set(successor) & set(predecessor)
    undeclared = shared - set(bridge['overlap_units'])
    if undeclared:
        raise ValueError(f'overlapping units not declared in the bridge: {sorted(undeclared)[:5]}')
    out = {u: v for u, v in successor.items() if u not in shared}
    out.update({u: v for u, v in predecessor.items() if u not in shared})
    return out
