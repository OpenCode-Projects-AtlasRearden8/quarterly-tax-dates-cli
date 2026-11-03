#!/usr/bin/env python3
"""Regenerate the bundled data file (offline; no IRS API).

The official dates are *derived* by the package's own documented shift rules
and pinned here so production code reads from the data file (the "bundled
data file" requirement) while tests keep the two in sync.

Run from the project root:  python tools/generate_data.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from quarterly_tax_dates.dates import BASE_DATES, QUARTER_ORDER, shift_forward  # noqa: E402

SOURCE_NOTE = (
    "Bundled offline schedule for US federal estimated tax (Form 1040-ES) "
    "installments. Based on the IRS general rule (April/June/September in "
    "year, January of the next year) with weekend/federal-holiday shifts, "
    "including DC Emancipation Day effects. Verify on IRS.gov before paying. "
    "No IRS API is used."
)

SHIFT_RULES_NOTE = (
    "Sheet-shifting rules: a due date that lands on a Saturday, Sunday, or "
    "federal/DC holiday moves to the next business day. Notable cases: "
    "MLK Day can be Jan 15 (e.g. 2024), and DC Emancipation Day (April 16, "
    "observed on the next weekday if it falls on a weekend) can push April "
    "dates to the 17th or 18th (e.g. 2023 and 2028)."
)

CHECKLIST = {
    "every_quarter": [
        "Last pay stub and any 1099s so far (wages, gig/1099 income, dividends, interest).",
        "Receipts and confirmation numbers for any quarterly payments already made.",
        "Last year's tax return, to sanity-check the 100%-of-last-tax safe-harbor amount (110% if your prior-year AGI was over $150,000).",
        "Bank routing and account numbers if paying by IRS Direct Pay or EFTPS; sign up for EFTPS a week ahead.",
    ]
}


def main() -> None:
    start_year, end_year = 2023, 2031
    official: dict[str, dict[str, str]] = {}
    for tax_year in range(start_year, end_year + 1):
        official[str(tax_year)] = {}
        for quarter in QUARTER_ORDER:
            base = BASE_DATES[quarter]
            year = tax_year + 1 if quarter == "Q4" else tax_year
            base = base.replace(year=year)
            due, _reason = shift_forward(base)
            official[str(tax_year)][quarter] = due.isoformat()

    tier1 = {
        "schema_version": 1,
        "estimated_tax": {
            "source_note": SOURCE_NOTE,
            "shift_rules_note": SHIFT_RULES_NOTE,
            "covered_years": [start_year, end_year],
            "base_rules": {
                "dates_md": {q: f"{BASE_DATES[q].month:02d}-{BASE_DATES[q].day:02d}" for q in QUARTER_ORDER},
                "q4_year_offset": 1,
            },
            "official_dates": official,
            "checklist": CHECKLIST,
        },
    }
    out_path = ROOT / "quarterly_tax_dates" / "data" / "due_dates.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(tier1, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
