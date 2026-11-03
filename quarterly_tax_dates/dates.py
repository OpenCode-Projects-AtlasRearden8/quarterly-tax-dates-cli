"""Core date math: quarterly estimated-tax due dates, weekend/holiday shifts.

Pure stdlib, offline. No IRS API -- the *rules* and official covered dates
come from the bundled ``data/due_dates.json`` file.

The IRS moves a deadline to the next business day when it lands on a weekend
or legal holiday (including DC holidays). A few known gotchas this module
handles:

* January/June/September off-by-one confusion: Q2 is June 15 (not April),
  Q3 is September 15, and "Q4" for tax year Y is actually due January 15 of
  year Y+1.
* MLK Day can be January 15 (e.g. 2024), pushing Q4 of the previous year to
  January 16.
* DC Emancipation Day (April 16) can push the Q1 date past April 17
  (e.g. April 18 in both 2023 and 2028).
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import NamedTuple

from .holidays import holidays_for_year

# The four safe-harbor "quarterly" installment labels and their base dates.
# Q1/Q2/Q3 land in the tax year itself; Q4 lands on Jan 15 of the NEXT year.
BASE_DATES: dict[str, _dt.date] = {
    "Q1": _dt.date(2000, 4, 15),
    "Q2": _dt.date(2000, 6, 15),
    "Q3": _dt.date(2000, 9, 15),
    "Q4": _dt.date(2000, 1, 15),  # month/day only; year is tax_year + 1
}

QUARTER_ORDER = ("Q1", "Q2", "Q3", "Q4")


class DueDate(NamedTuple):
    quarter: str
    tax_year: int
    base_date: _dt.date
    due_date: _dt.date
    shift_reason: str


class Bundle(NamedTuple):
    official: dict[int, dict[str, str]]  # year -> {Q: ISO date}
    source_note: str
    shift_rules_note: str
    checklist: dict[str, list[str]]
    bundle_name: str


def package_data_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "due_dates.json"


def load_bundle(path: Path | None = None) -> Bundle:
    """Load the bundled data file (offline, no IRS API)."""
    p = path if path is not None else package_data_path()
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Bundled data file missing: {p}. The package install may be "
            "damaged; reinstall quarterly-tax-dates-cli."
        ) from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Bundled data file is not valid JSON ({p}): {exc}"
        ) from exc
    try:
        meta = payload["estimated_tax"]
        official = {int(y): {q: iso for q, iso in qs.items()}
                    for y, qs in meta["official_dates"].items()}
        return Bundle(
            official=official,
            source_note=meta.get("source_note", ""),
            shift_rules_note=meta.get("shift_rules_note", ""),
            checklist=meta.get("checklist", {}),
            bundle_name=p.name,
        )
    except (KeyError, TypeError, AttributeError, ValueError) as exc:
        raise RuntimeError(
            f"Bundled data file {p} has an unexpected shape: {exc!r}"
        ) from exc


def shift_forward(base: _dt.date) -> tuple[_dt.date, str]:
    """Move a date to the next business day if it lands on a weekend or
    federal/DC holiday. Returns (effective_date, human_reason)."""
    reason_parts: list[str] = []
    d = base
    while True:
        if d.weekday() >= 5:
            if not any("weekend" in r for r in reason_parts):
                reason_parts.append(f"base date {base.isoformat()} fell on a weekend")
            d = d + _dt.timedelta(days=7 - d.weekday())
            continue
        name = holidays_for_year(d.year).get(d)
        if name:
            reason_parts.append(
                f"{_human(d)} is {name}"
            )
            d = d + _dt.timedelta(days=1)
            continue
        break
    return d, "; ".join(reason_parts)


def _human(d: _dt.date) -> str:
    return d.strftime(f"%A, %B {d.day}, %Y")


def compute_due_year(tax_year: int, bundle: Bundle | None = None) -> list[DueDate]:
    """Due dates for one tax year: Q1-Q3 inside the year, Q4 next January.

    If the bundled file lists an official date for this year, that is used
    verbatim (belt-and-suspenders with the computed dates, which the test
    suite keeps in sync). For uncovered years the documented shift rules are
    extended to compute the answer offline for any year.
    """
    bundle = bundle or load_bundle()
    results: list[DueDate] = []
    official_for_year = bundle.official.get(tax_year, {})

    for quarter in QUARTER_ORDER:
        base = BASE_DATES[quarter]
        year = tax_year + 1 if quarter == "Q4" else tax_year
        base = _dt.date(year, base.month, base.day)
        if quarter in official_for_year:
            official = _dt.date.fromisoformat(official_for_year[quarter])
            computed, reason = shift_forward(base)
            if official != computed:
                # Never silently disagree with the bundle; the tests pin
                # computed == official, so a mismatch here means someone
                # edited the data file without checking the rules.
                reason = f"bundled official date differs from computed ({computed.isoformat()})"
            reason = reason or "bundled official date per IRS schedule"
            results.append(DueDate(quarter, tax_year, base, official, reason))
        else:
            due, reason = shift_forward(base)
            results.append(DueDate(quarter, tax_year, base, due, reason))
    return results


def covered_years(bundle: Bundle | None = None) -> list[int]:
    bundle = bundle or load_bundle()
    return sorted(bundle.official)


def is_covered(tax_year: int, bundle: Bundle | None = None) -> bool:
    bundle = bundle or load_bundle()
    return tax_year in bundle.official
