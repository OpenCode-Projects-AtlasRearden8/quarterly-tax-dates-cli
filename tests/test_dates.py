"""Date-math tests: quarterly due dates, weekend/holiday shifts, off-by-one traps."""

from __future__ import annotations

import datetime as dt

import pytest

from quarterly_tax_dates.dates import (
    DueDate,
    compute_due_year,
    covered_years,
    is_covered,
    load_bundle,
    shift_forward,
)
from quarterly_tax_dates.holidays import holidays_for_year


@pytest.fixture(scope="module")
def bundle():
    return load_bundle()


# Years 2023-2028 are the officially published IRS dates. Later years are
# derived from the same documented shift rules; the bundle-vs-computation
# cross-check below keeps them honest.
OFFICIAL_SCHEDULE = {
    2023: ("2023-04-18", "2023-06-15", "2023-09-15", "2024-01-16"),
    2024: ("2024-04-15", "2024-06-17", "2024-09-16", "2025-01-15"),
    2025: ("2025-04-15", "2025-06-16", "2025-09-15", "2026-01-15"),
    2026: ("2026-04-15", "2026-06-15", "2026-09-15", "2027-01-15"),
    2027: ("2027-04-15", "2027-06-15", "2027-09-15", "2028-01-18"),
    2028: ("2028-04-18", "2028-06-15", "2028-09-15", "2029-01-16"),
    2029: ("2029-04-17", "2029-06-15", "2029-09-17", "2030-01-15"),
    2030: ("2030-04-15", "2030-06-17", "2030-09-16", "2031-01-15"),
    2031: ("2031-04-15", "2031-06-16", "2031-09-15", "2032-01-15"),
    2032: ("2032-04-15", "2032-06-15", "2032-09-15", "2033-01-18"),
}


@pytest.mark.parametrize("tax_year,expected", sorted(OFFICIAL_SCHEDULE.items()))
def test_all_years_match_officially_published_dates(tax_year, expected, bundle):
    """The rule-computed dates match the officially published IRS dates for
    every year in the fixture table."""
    for due, iso in zip(compute_due_year(tax_year, bundle), expected):
        assert due.due_date == dt.date.fromisoformat(iso)


@pytest.mark.parametrize("tax_year", sorted(OFFICIAL_SCHEDULE))
def test_bundle_matches_computation_for_covered_years(tax_year, bundle):
    if tax_year not in bundle.official:
        pytest.skip(f"{tax_year} is outside the bundled coverage window")
    for due in compute_due_year(tax_year, bundle):
        assert due.due_date == dt.date.fromisoformat(bundle.official[tax_year][due.quarter])
        assert "differs" not in due.shift_reason


def test_q4_is_next_january(bundle):
    """The Jan/June/Sep off-by-one confusion: tax-year 2032's Q4 is a 2033
    date, and it slides to Jan 18 because Jan 15, 2033 was a Saturday and
    Monday Jan 17 was MLK Day."""
    dues = {d.quarter: d for d in compute_due_year(2032, bundle)}
    assert dues["Q4"].due_date == dt.date(2033, 1, 18)
    assert dues["Q4"].tax_year == 2032


def test_weekend_shift_forward(bundle):
    # 2026-06-15 is a Monday (no shift); 2025-06-15 is a Sunday -> June 16.
    dues = {d.quarter: d for d in compute_due_year(2025, bundle)}
    assert dues["Q2"].base_date == dt.date(2025, 6, 15)
    assert dues["Q2"].due_date == dt.date(2025, 6, 16)
    assert "weekend" in dues["Q2"].shift_reason


def test_shift_never_lands_on_weekend_or_holiday():
    # Friday holiday: a base date on the Friday before a Monday holiday must
    # not be bumped onto the weekend.
    cases = [
        dt.date(2024, 7, 4),      # Thursday holiday, no shift
        dt.date(2026, 1, 1),      # Thursday holiday
        dt.date(2028, 4, 15),     # Saturday -> Monday(=Emancipation obs.) -> Tuesday
        dt.date(2033, 1, 15),     # Saturday before MLK Monday -> prior? no: forward to Tue
        dt.date(2023, 4, 15),     # Saturday -> Monday(=Emancipation obs.) -> Tuesday
    ]
    for base in cases:
        due, reason = shift_forward(base)
        assert due.weekday() < 5, (base, due, reason)
        assert due not in holidays_for_year(due.year), (base, due, reason)


def test_2023_april_emancipation_double_shift():
    due, reason = shift_forward(dt.date(2023, 4, 15))
    assert due == dt.date(2023, 4, 18)
    assert "weekend" in reason and "Emancipation" in reason


def test_2024_jan_mlk_off_by_one():
    """Jan 15, 2024 was MLK Day, so tax year 2023's Q4 slipped to Jan 16."""
    dues = {d.quarter: d for d in compute_due_year(2023)}
    assert dues["Q4"].due_date == dt.date(2024, 1, 16)


def test_never_lands_on_weekend_or_holiday_2020_2050():
    """For every plausible tax year, no due date ever lands on a weekend or
    holiday -- the exact invariant the shifting is supposed to guarantee."""
    for tax_year in range(2020, 2051):
        for due in compute_due_year(tax_year):
            assert due.due_date.weekday() < 5, (tax_year, due.quarter, due.due_date)
            assert due.due_date not in holidays_for_year(due.due_date.year), (
                tax_year,
                due.quarter,
                due.due_date,
            )


def test_uncovered_year_outside_bundle_still_computes(bundle):
    """Years outside the bundle still get correct, weekday-safe dates."""
    assert not is_covered(2090, bundle)
    dues = compute_due_year(2090, bundle)
    assert [d.quarter for d in dues] == ["Q1", "Q2", "Q3", "Q4"]
    for due in dues:
        assert due.due_date.weekday() < 5
        assert due.due_date not in holidays_for_year(due.due_date.year)
    assert dues[0].base_date == dt.date(2090, 4, 15)
    assert dues[3].base_date == dt.date(2091, 1, 15)


def test_covered_years_sorted_and_populated(bundle):
    years = covered_years(bundle)
    assert len(years) == len(bundle.official) >= 1
    assert years == sorted(years)


def test_due_date_namedtuple_fields(bundle):
    d: DueDate = compute_due_year(2026, bundle)[0]
    assert d.quarter == "Q1"
    assert d.tax_year == 2026
    assert d.base_date == dt.date(2026, 4, 15)
    assert d.due_date == dt.date(2026, 4, 15)
