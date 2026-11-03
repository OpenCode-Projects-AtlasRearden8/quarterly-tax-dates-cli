"""ICS content tests: RFC 5545 shape, deterministic UIDs, line folding."""

from __future__ import annotations

import datetime as dt

from quarterly_tax_dates.ics import build_ics
from quarterly_tax_dates.dates import load_bundle


def _payload(year=2026):
    from quarterly_tax_dates.dates import compute_due_year

    bundle = load_bundle()
    dues = compute_due_year(year, bundle)
    return {
        "tax_year": year,
        "installments": [
            {
                "quarter": d.quarter,
                "tax_year": d.tax_year,
                "due_date": d.due_date.isoformat(),
            }
            for d in dues
        ],
    }


def _unfold(content: str) -> str:
    return content.replace("\r\n ", "")


def test_structure():
    content = build_ics(_payload())
    lines = content.split("\r\n")
    assert lines[0] == "BEGIN:VCALENDAR"
    assert lines[-1] == "" and lines[-2] == "END:VCALENDAR"
    assert "VERSION:2.0" in content
    assert "PRODID:-//Asdale Dynamics LLC//quarterly-tax-dates//EN" in content
    assert content.count("BEGIN:VEVENT") == 4
    assert content.count("END:VEVENT") == 4


def test_all_day_events_use_value_date():
    content = build_ics(_payload(2024))
    assert "DTSTART;VALUE=DATE:20240415" in content
    assert "DTEND;VALUE=DATE:20240416" in content
    assert "DTSTART;VALUE=DATE-TIME" not in content


def test_deterministic_uids():
    assert "est-tax-q1-2026@asdale-dynamics.tax-dates" in build_ics(_payload())


def test_line_folding_75_octets():
    content = build_ics(_payload())
    for raw in content.replace("\r ", "").split("\r\n"):
        assert len(raw.encode("utf-8")) <= 75, raw


def test_escaping_commas_and_semicolons():
    payload = _payload()
    payload["installments"][0]["quarter"] = "Q1,weird;name"
    content = _unfold(build_ics(payload))
    assert "SUMMARY:Estimated tax payment (Q1\\,weird\\;name\\, tax year 2026) due" in content


def test_dates_cross_check_bundle():
    payload = _payload(2023)
    bundle = load_bundle()
    assert payload["installments"][3]["due_date"] == bundle.official[2023]["Q4"]
    assert dt.date.fromisoformat(bundle.official[2023]["Q1"]) == dt.date(2023, 4, 18)
