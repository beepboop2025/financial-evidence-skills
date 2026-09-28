"""Bounded 2026 NY Fed reference-rate publication calendar.

This is a reviewed calendar, not a perpetual holiday rule or a publication
receipt. It rejects observations outside 2026. January 1-5, 2027 is included
only to calculate the next new observation's release after year-end 2026.

Sources checked September 28, 2026:
https://www.newyorkfed.org/aboutthefed/holiday_schedule
https://www.newyorkfed.org/markets/reference-rates/additional-information-about-reference-rates
https://www.newyorkfed.org/markets/opolicy/operating_policy_260312a
https://www.newyorkfed.org/markets/opolicy/operating_policy_260618a

SOFR has no observation or publication on April 3 or July 3, 2026. EFFR
remains open on both dates. An early market close does not suppress publication.
"""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

CALENDAR_ID = "nyfed-reference-rates-2026.v1"
REVIEWED_OBSERVATION_YEAR = 2026
_HORIZON_END = date(2027, 1, 5)
_NEW_YORK = ZoneInfo("America/New_York")

# Exact New York Fed observances. Its Saturday holidays do not close the
# preceding Friday; Sunday holidays close the following Monday. None of the
# listed 2026 holidays falls on Sunday. July 3 below is a SOFR-specific closure.
_NYFED_CLOSED = frozenset(
    {
        date(2026, 1, 1),
        date(2026, 1, 19),
        date(2026, 2, 16),
        date(2026, 5, 25),
        date(2026, 6, 19),
        date(2026, 7, 4),
        date(2026, 9, 7),
        date(2026, 10, 12),
        date(2026, 11, 11),
        date(2026, 11, 26),
        date(2026, 12, 25),
        date(2027, 1, 1),
    }
)
_SOFR_CLOSED = _NYFED_CLOSED | {date(2026, 4, 3), date(2026, 7, 3)}


def _next_business_day(day: date, closed: frozenset[date]) -> date:
    candidate = day + timedelta(days=1)
    while candidate <= _HORIZON_END:
        if candidate.weekday() < 5 and candidate not in closed:
            return candidate
        candidate += timedelta(days=1)
    raise ValueError("publication falls outside the reviewed calendar horizon")


def next_publication_after_observation(asof: date, mnemonic: str) -> datetime:
    """Return the UTC deadline for the first observation newer than ``asof``.

    The next observation business day is followed by its publication business
    day, at approximately 08:00 New York time for SOFR or 09:00 for EFFR. For
    example, a Friday September 25 print is superseded on Tuesday September 29,
    when Monday's observation is due. This does not return Friday's own Monday
    publication time, nor invent a print when its expected release is missed.

    Only exact ``SOFR`` and ``EFFR`` identifiers and valid 2026 observation
    dates are accepted. Callers must retain independent age and evidence checks.
    """
    if (
        not isinstance(asof, date)
        or isinstance(asof, datetime)
        or asof.year != REVIEWED_OBSERVATION_YEAR
    ):
        raise ValueError("observation date is outside the reviewed 2026 calendar")
    if not isinstance(mnemonic, str) or mnemonic not in {"SOFR", "EFFR"}:
        raise ValueError("unsupported reference-rate mnemonic")
    closed = _SOFR_CLOSED if mnemonic == "SOFR" else _NYFED_CLOSED
    if asof.weekday() >= 5 or asof in closed:
        raise ValueError("observation date is not a reference-rate business day")
    next_observation = _next_business_day(asof, closed)
    publication_day = _next_business_day(next_observation, closed)
    hour = 8 if mnemonic == "SOFR" else 9
    return datetime.combine(
        publication_day, time(hour=hour), tzinfo=_NEW_YORK
    ).astimezone(timezone.utc)
