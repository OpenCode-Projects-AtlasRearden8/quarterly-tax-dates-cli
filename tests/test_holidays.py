"""Holiday-table sanity checks (observed rules, DC Emancipation Day)."""

from __future__ import annotations

import datetime as dt

import pytest

from quarterly_tax_dates.holidays import holidays_for_year


@pytest.mark.parametrize("iso,name_part", [
    ("2023-01-02", "New Year"),
    ("2023-01-16", "Martin Luther King"),
    ("2023-02-20", "Washington"),
    ("2023-05-29", "Memorial"),
    ("2023-06-19", "Juneteenth"),
    ("2023-07-04", "Independence"),
    ("2023-09-04", "Labor"),
    ("2023-10-09", "Columbus"),
    ("2023-11-10", "Veterans"),   # Nov 11, 2023 was Saturday -> observed Friday
    ("2023-11-23", "Thanksgiving"),
    ("2023-12-25", "Christmas"),
    ("2024-01-15", "Martin Luther King"),
    ("2026-11-11", "Veterans"),   # Wednesday, no shift
])
def test_known_holidays(iso, name_part):
    d = dt.date.fromisoformat(iso)
    assert name_part in holidays_for_year(d.year)[d]


def test_dc_emancipation_plain():
    assert dt.date(2026, 4, 16) in holidays_for_year(2026)


def test_dc_emancipation_sunday_pushes_to_monday():
    # April 16, 2023 was a Sunday -> observed Monday April 17.
    table = holidays_for_year(2023)
    assert dt.date(2023, 4, 17) in table
    assert "Emancipation" in table[dt.date(2023, 4, 17)]


def test_new_years_observed_back_dec31():
    # Jan 1, 2028 is a Saturday -> observed Friday, Dec 31, 2027.
    table = holidays_for_year(2027)
    assert dt.date(2027, 12, 31) in table
    assert "New Year" in table[dt.date(2027, 12, 31)]


def test_no_holiday_lands_on_weekend():
    """Observed holidays land on weekdays by construction."""
    for year in range(2020, 2051):
        for d, name in holidays_for_year(year).items():
            assert d.weekday() < 5, (d, name)


def test_american_gf_fridays_excluded():
    """A Friday right after a Thanksgiving Monday-free stretch is a business
    day; only observed rules create Friday holidays."""
    table = holidays_for_year(2026)
    assert dt.date(2026, 11, 27) not in table
