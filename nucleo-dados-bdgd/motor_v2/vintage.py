"""Vintage-aware availability for point-in-time forecasting (standard library only, read-only on the data it receives).

Four different things are kept apart and never inferred from one another:

* competence  - the reference year of a data release (the BDGD data-base, e.g. 2023-12-31 -> 2023);
* publication - the date a release (one vintage of one competence) became available to a user;
* origin date - the date the forecast is issued (explicit ISO date, not "the end of the competence year");
* target year - the year being forecast.

A forecast issued on an origin date may only read the vintage of each competence that had already been published by that date: the latest
one published on or before the origin date. Revisions published later are rejected, whatever their competence. A competence whose
publication is the target year's own data (or later than the origin date) is never an input; a target that was already published at the
origin date is not a forecast at all (leak). Real dates are never altered. A backtest is only called vintage-proven when every release it
read carries a publication record; a generation stamp or an inferred date is a candidate, not proof."""
from dataclasses import dataclass
from datetime import date

PUBLICATION_RECORD = 'publication_record'   # official publication/availability date recorded by the source
GENERATION_STAMP = 'generation_stamp'        # build timestamp of the file: candidate evidence only
INFERRED = 'inferred'                        # date reconstructed or assumed

VINTAGE_PROVEN = 'vintage_proven'
VINTAGE_UNPROVEN = 'vintage_unproven'


class VintageError(ValueError):
    pass


def iso(value, what='date'):
    """Strict YYYY-MM-DD; ISO dates of that shape order lexicographically and chronologically alike."""
    if not isinstance(value, str) or len(value) != 10:
        raise VintageError(f'{what} must be an ISO date YYYY-MM-DD, got {value!r}')
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise VintageError(f'{what} must be an ISO date YYYY-MM-DD, got {value!r}') from error
    return value


@dataclass(frozen=True)
class Release:
    """One vintage of one competence. `revision` orders vintages published on the same day."""
    competence: int
    published: str
    revision: int = 0
    evidence: str = PUBLICATION_RECORD
    label: str = ''

    def __post_init__(self):
        iso(self.published, 'published')
        if not isinstance(self.competence, int):
            raise VintageError('competence must be a year')
        if self.evidence not in (PUBLICATION_RECORD, GENERATION_STAMP, INFERRED):
            raise VintageError(f'unknown evidence kind {self.evidence!r}')
        if self.published[:4] < str(self.competence):
            raise VintageError(f'release of competence {self.competence} published before that year ({self.published}): impossible vintage')


def _order(release):
    return (release.published, release.revision)


def available(releases, origin_date):
    """Releases published on or before the origin date (the day of publication counts as available)."""
    cutoff = iso(origin_date, 'origin_date')
    return [r for r in releases if r.published <= cutoff]


def rejected_later(releases, origin_date):
    """Releases published after the origin date: first-publications and revisions that a forecast issued then could not have seen."""
    cutoff = iso(origin_date, 'origin_date')
    return [r for r in releases if r.published > cutoff]


def select(releases, competence, origin_date):
    """The vintage of `competence` a forecast issued on `origin_date` may read: the latest one already published; None if none was."""
    seen = [r for r in available(releases, origin_date) if r.competence == competence]
    return max(seen, key=_order) if seen else None


def view(releases, origin_date, target_year):
    """Point-in-time input view for a forecast of `target_year` issued on `origin_date`.

    Returns the selected vintage per competence strictly before the target year, the rejected later releases and the effective lag.
    Raises when the target's own competence was already published at the origin date (the target is known: not a forecast)."""
    cutoff = iso(origin_date, 'origin_date')
    known_target = select(releases, target_year, cutoff)
    if known_target is not None:
        raise VintageError(f'leak: target competence {target_year} already published on {known_target.published}, on or before the origin date {cutoff}')
    if cutoff[:4] > str(target_year):
        raise VintageError(f'origin date {cutoff} is after the target year {target_year}')
    chosen = {}
    for competence in sorted({r.competence for r in releases if r.competence < target_year}):
        picked = select(releases, competence, cutoff)
        if picked is not None:
            chosen[competence] = picked
    latest = max(chosen) if chosen else None
    return dict(origin_date=cutoff, target_year=target_year, selected=chosen,
                rejected_later=sorted(rejected_later(releases, cutoff), key=lambda r: (r.competence, _order(r))),
                last_competence=latest, effective_horizon=None if latest is None else target_year - latest)


def claim(selected_releases, mode='point_in_time'):
    """What a backtest that read these releases is allowed to say about its vintages. Never 'validated': validation also needs the
    independent origins required elsewhere; this only states whether the availability dates are proven."""
    if mode != 'point_in_time':
        return dict(status=VINTAGE_UNPROVEN, reason='reconciled retrospective experiments never acquire point-in-time credentials')
    releases = list(selected_releases)
    if not releases:
        return dict(status=VINTAGE_UNPROVEN, reason='no release was read')
    weak = [r for r in releases if r.evidence != PUBLICATION_RECORD]
    if weak:
        kinds = sorted({r.evidence for r in weak})
        return dict(status=VINTAGE_UNPROVEN, reason=f'{len(weak)} of {len(releases)} releases rest on {"/".join(kinds)} instead of a publication record')
    return dict(status=VINTAGE_PROVEN, reason='every release read has a publication record on or before the origin date')
