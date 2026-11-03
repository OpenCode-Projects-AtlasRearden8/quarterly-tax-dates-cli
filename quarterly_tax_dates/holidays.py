"""US federal holidays (with DC Emancipation Day) used for deadline shifting.

Pure stdlib, offline. No network, no API.

The IRS moves tax deadlines that fall on a weekend or legal holiday to the
next business day. For federal tax purposes "legal holiday" includes
holidays observed in the District of Columbia -- most importantly DC
Emancipation Day (April 16), which is why some April dates slide an extra
day (the April 18, 2023 tax deadline is the famous example).
"""

from __future__ import annotations

import datetime as _dt
from functools import lru_cache

def _nth_weekday(year: int, month: int, weekday: int, n: int) -> _dt.date:
    """n-th weekday of a month (n=1 is first; n=-1 is last)."""
    if n > 0:
        first = _dt.date(year, month, 1)
        delta = (weekday - first.weekday()) % 7
        return first + _dt.timedelta(days=delta + 7 * (n - 1))
    nxt = _dt.date(year + 1, 1, 1) if month == 12 else _dt.date(year, month + 1, 1)
    last = nxt - _dt.timedelta(days=1)
    delta = (last.weekday() - weekday) % 7
    return last - _dt.timedelta(days=delta)


def _observed(year: int, month: int, day: int) -> _dt.date:
    """Federal observing rule: Sunday -> next Monday; Saturday -> prior Friday."""
    d = _dt.date(year, month, day)
    if d.weekday() == 6:  # Sunday
        return d + _dt.timedelta(days=1)
    if d.weekday() == 5:  # Saturday
        return d - _dt.timedelta(days=1)
    return d


@lru_cache(maxsize=None)
def holidays_for_year(year: int) -> dict[_dt.date, str]:
    """Holiday date -> name for one calendar year (no cross-year observances)."""
    holidays: dict[_dt.date, str] = {}

    def add(d: _dt.date, name: str) -> None:
        # Keep the earliest observance if two rules ever collide on one date.
        existing = holidays.get(d)
        if existing is None or existing.endswith("(observed)"):
            holidays[d] = name

    # New Year's Day: Sunday -> observed Monday Jan 2. If Jan 1 falls on a
    # Saturday, the observance is Friday Dec 31 of the *previous* calendar
    # year (that entry is added by that year's own table), so no raw
    # Saturday entry is added here.
    jan1 = _dt.date(year, 1, 1)
    if jan1.weekday() == 6:
        add(jan1 + _dt.timedelta(days=1), "New Year's Day (observed)")
    elif jan1.weekday() != 5:
        add(jan1, "New Year's Day")
    add(_nth_weekday(year, 1, 0, 3), "Birthday of Martin Luther King, Jr.")
    add(_nth_weekday(year, 2, 0, 3), "Washington's Birthday")
    add(_nth_weekday(year, 5, 0, -1), "Memorial Day")
    add(_observed(year, 6, 19), "Juneteenth National Independence Day")
    add(_observed(year, 7, 4), "Independence Day")
    add(_nth_weekday(year, 9, 0, 1), "Labor Day")
    add(_nth_weekday(year, 10, 0, 2), "Columbus Day")
    add(_observed(year, 11, 11), "Veterans Day")
    add(_nth_weekday(year, 11, 3, 4), "Thanksgiving Day")
    add(_observed(year, 12, 25), "Christmas Day")

    # DC Emancipation Day, April 16. If it falls on a weekend, DC observes it
    # on the adjacent weekday (Sunday -> Monday, Saturday -> Friday), and
    # federal tax deadlines follow the observed date.
    emancipation = _dt.date(year, 4, 16)
    if emancipation.weekday() == 6:  # Sunday -> observed Monday
        add(emancipation + _dt.timedelta(days=1), "DC Emancipation Day (observed)")
    elif emancipation.weekday() == 5:  # Saturday -> observed Friday
        add(emancipation - _dt.timedelta(days=1), "DC Emancipation Day (observed)")
    else:
        add(emancipation, "DC Emancipation Day")

    # New Year's Day observed on Friday Dec 31 when Jan 1 lands on a Saturday.
    jan1_next = _dt.date(year + 1, 1, 1)
    if jan1_next.weekday() == 5:
        add(_dt.date(year, 12, 31), "New Year's Day (observed)")

    return holidays
