"""Configurable, tested feature coverage and imputation policy. Statistics are fitted on TRAINING rows only.

strict    (default, previous behaviour): a feature is usable only if every training and evaluation row has it.
coverage: a feature is usable if its coverage among TRAINING rows reaches `min_train_coverage`; missing values in
          training and evaluation rows are filled with the training median/mean (optionally with a missing indicator).

Targets are never imputed. A value that exists but fails the release/revision/reference gate is NOT a gap: it makes
the feature ineligible (imputing it would hide a leakage risk). Imputation never uses zero as an implicit default."""
from dataclasses import dataclass, asdict
import numpy as np

STRATEGIES = ('strict', 'coverage')
IMPUTATIONS = ('none', 'median', 'mean')
MIN_TRAIN_VALUES = 5


@dataclass(frozen=True)
class FeaturePolicy:
    strategy: str = 'strict'
    min_train_coverage: float = 1.0
    imputation: str = 'none'
    missing_indicator: bool = False

    def __post_init__(self):
        if self.strategy not in STRATEGIES: raise ValueError('unknown feature strategy')
        if self.imputation not in IMPUTATIONS: raise ValueError('unknown imputation')
        if not 0 < self.min_train_coverage <= 1: raise ValueError('min_train_coverage must be in (0, 1]')
        if self.strategy == 'strict' and (self.imputation != 'none' or self.min_train_coverage != 1 or self.missing_indicator):
            raise ValueError('strict policy forbids imputation and partial coverage')
        if self.strategy == 'coverage' and self.imputation == 'none':
            raise ValueError('coverage policy needs an imputation; dropping evaluation rows would break the common test set')

    @classmethod
    def from_cfg(cls, cfg):
        return cls(**(cfg or {}))

    def as_dict(self):
        return asdict(self)


def _has(r, i):
    return i < len(r['x']) and r['x'][i] is not None


def feature_status(i, train, evaluation, mode, policy, gate):
    """-> dict(eligible, reason, train_coverage, eval_coverage). `gate(row, i, mode)` is the release/reference gate."""
    if i == 0:
        return dict(eligible=True, reason='stock', train_coverage=1., eval_coverage=1.)
    rows = train + evaluation
    if not train or not rows:
        return dict(eligible=False, reason='no_rows', train_coverage=None, eval_coverage=None)
    with_value = [r for r in rows if _has(r, i)]
    tc = sum(_has(r, i) for r in train) / len(train)
    ec = sum(_has(r, i) for r in evaluation) / len(evaluation) if evaluation else None
    if any(not gate(r, i, mode) for r in with_value):
        return dict(eligible=False, reason='release_or_reference_gate', train_coverage=tc, eval_coverage=ec)
    if policy.strategy == 'strict':
        ok = len(with_value) == len(rows)
        return dict(eligible=ok, reason='complete' if ok else 'missing_values_strict', train_coverage=tc, eval_coverage=ec)
    n = sum(_has(r, i) for r in train)
    if tc < policy.min_train_coverage or n < MIN_TRAIN_VALUES:
        return dict(eligible=False, reason='train_coverage_below_minimum', train_coverage=tc, eval_coverage=ec)
    return dict(eligible=True, reason='complete' if len(with_value) == len(rows) else 'imputed_with_train_statistic', train_coverage=tc, eval_coverage=ec)


def fit_imputer(train, features, policy):
    """Statistic per feature from TRAINING values only."""
    stats = {}
    for i in features:
        if i == 0 or policy.imputation == 'none': continue
        v = np.array([r['x'][i] for r in train if _has(r, i)], dtype=float)
        if len(v) < MIN_TRAIN_VALUES: raise ValueError('too few training values to fit the imputer')
        stats[i] = float(np.median(v) if policy.imputation == 'median' else np.mean(v))
    return stats


def design(rows, features, stats, policy):
    """Matrix for `rows`; a missing value without a fitted statistic is an error (never an implicit zero)."""
    out = []
    for r in rows:
        line, flags = [], []
        for i in features:
            if _has(r, i):
                line.append(float(r['x'][i])); flags.append(0.)
            elif i in stats:
                line.append(stats[i]); flags.append(1.)
            else:
                raise ValueError('missing feature; no imputation authorized')
        out.append(line + (flags if policy.missing_indicator else []))
    return np.array(out, dtype=float)
