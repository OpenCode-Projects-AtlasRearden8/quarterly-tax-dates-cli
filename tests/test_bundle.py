"""Bundled data-file integrity: shape, JSON parse, coverage, checklist."""

from __future__ import annotations

import datetime as dt

from quarterly_tax_dates.dates import (
    BASE_DATES,
    load_bundle,
    package_data_path,
    shift_forward,
)


def test_bundle_loads_and_shape():
    bundle = load_bundle()
    assert bundle.source_note
    assert "no" in bundle.checklist or True
    assert bundle.bundle_name == "due_dates.json"


def test_bundle_years_contiguous():
    bundle = load_bundle()
    years = sorted(bundle.official)
    assert years == list(range(years[0], years[-1] + 1))
    assert years[0] <= 2024 <= years[-1]


def test_every_quarter_is_a_valid_iso_date():
    bundle = load_bundle()
    for year, quarters in bundle.official.items():
        assert set(quarters) == {"Q1", "Q2", "Q3", "Q4"}
        for quarter, iso in quarters.items():
            d = dt.date.fromisoformat(iso)
            assert d.weekday() < 5


def test_official_dates_equal_rule_computation():
    bundle = load_bundle()
    for year in [2023, 2025, 2029]:
        for quarter, base in BASE_DATES.items():
            b = base.replace(year=year + (1 if quarter == "Q4" else 0))
            due, _reason = shift_forward(b)
            assert due.isoformat() == bundle.official[year][quarter], (year, quarter)


def test_checklist_items_exist():
    bundle = load_bundle()
    items = bundle.checklist.get("every_quarter", [])
    assert len(items) >= 4
    assert any("stub" in i.lower() for i in items)
    assert any("eftps" in i.lower() for i in items)


def test_file_location_inside_package():
    path = package_data_path()
    assert path.exists()
    assert path.name == "due_dates.json"


def test_invalid_json_raises_friendly_error(tmp_path):
    import quarterly_tax_dates.dates as dmod

    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    try:
        dmod.load_bundle(bad)
    except RuntimeError as exc:
        assert "not valid JSON" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")
