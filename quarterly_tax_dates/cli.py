"""Command-line interface: countdown checklist, ICS export, JSON output."""

from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path

from . import __version__
from .dates import (
    Bundle,
    DueDate,
    compute_due_year,
    covered_years,
    load_bundle,
)

PROG = "quarterly-tax-dates"
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2

BANNER = "Quarterly federal estimated-tax due dates (offline, from bundled IRS schedule)"


def format_countdown(d: _dt.date, today: _dt.date) -> str:
    days = (d - today).days
    if days == 0:
        return "due TODAY"
    if days < 0:
        n = -days
        return f"{n} day{'s' if n != 1 else ''} past due"
    if days == 1:
        return "1 day from now"
    return f"{days} days from now"


def render_checklist_bundle(due: DueDate, items: list[str]) -> list[str]:
    pretty = due.due_date.strftime(f"%A, %B {due.due_date.day}, %Y")
    lines = [
        f"{due.quarter} (tax year {due.tax_year}) -- pay by {pretty}",
        f"    {format_countdown(due.due_date, _dt.date.today())}",
    ]
    if due.base_date != due.due_date:
        lines.append(f"    shifted from {due.base_date.isoformat()} because: {due.shift_reason}")
    for item in items:
        lines.append(f"      - {item}")
    return lines


def build_report(tax_year: int, bundle: Bundle) -> list[str]:
    dues = compute_due_year(tax_year, bundle)
    general_items = bundle.checklist.get("every_quarter", [])
    lines = [
        BANNER + ".",
        "",
    ]
    if tax_year not in bundle.official:
        lines.append(
            f"Note: tax year {tax_year} is outside the bundled official schedule "
            f"({covered_years(bundle)[0]}-{covered_years(bundle)[-1]}); dates are computed "
            "from the documented IRS weekday/DC-holiday rules, offline."
        )
        lines.append("")
    lines.append(f"Tax year {tax_year} estimated-tax payments (safe-harbor installments):")
    lines.append("")
    for due in dues:
        lines.extend(render_checklist_bundle(due, general_items))
        lines.append("")
    lines.append(
        "Paying: IRS Direct Pay (irs.gov/payments) or EFTPS. Sign up for EFTPS "
        "at least a week ahead so your login works in time."
    )
    lines.append(
        "Education only, not tax advice. Confirm amounts and dates on IRS.gov."
    )
    return lines


def run_cli(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog=PROG,
        description=(BANNER + ". Quietly guard the four deadlines: date math, "
                     "checklist of what to gather, and .ics export. Offline, stdlib only."),
    )
    parser.add_argument(
        "year",
        nargs="?",
        type=int,
        help="tax year to show (default: the current year)",
    )
    parser.add_argument(
        "--ics",
        metavar="PATH",
        help="also write an .ics calendar file with the four due dates as events",
    )
    parser.add_argument(
        "--next",
        action="store_true",
        help="show only the next upcoming installment from today",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--version", action="version", version=f"{PROG} {__version__}")
    args = parser.parse_args(argv)

    bundle = load_bundle()

    if args.year is None:
        tax_year = _dt.date.today().year
    else:
        tax_year = args.year
        if tax_year < 2000 or tax_year > 2099:
            parser.error("year must be between 2000 and 2099")  # exits 2

    dues = compute_due_year(tax_year, bundle)
    today = _dt.date.today()

    shown = dues
    next_only = args.next
    if next_only:
        upcoming = [d for d in dues if d.due_date >= today]
        shown = [upcoming[0]] if upcoming else [dues[-1]]

    if next_only:
        lines = [BANNER + ".", "", f"Next installment (from {today.isoformat()}):", ""]
        for due in shown:
            lines.extend(render_checklist_bundle(due, bundle.checklist.get("every_quarter", [])))
            lines.append("")
        lines.append("Education only, not tax advice. Confirm amounts and dates on IRS.gov.")
    else:
        lines = build_report(tax_year, bundle)

    try:
        payload = build_json_payload(tax_year, bundle, shown, next_only)
    except (OSError, ValueError, KeyError) as exc:  # pragma: no cover - defensive
        print(f"error: could not assemble output: {exc}", file=sys.stderr)
        return EXIT_ERROR

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print("\n".join(lines).rstrip())

    if args.ics:
        try:
            written = write_ics_file(args.ics, payload, bundle)
        except (OSError, ValueError) as exc:
            print(f"error: could not write .ics file: {exc}", file=sys.stderr)
            return EXIT_ERROR
        if not args.json:
            print(f"Calendar file written: {written}")

    return EXIT_OK


def build_json_payload(
    tax_year: int,
    bundle: Bundle,
    shown: list[DueDate],
    next_only: bool,
) -> dict:
    today = _dt.date.today()
    return {
        "tool": "quarterly-tax-dates",
        "version": __version__,
        "tax_year": tax_year,
        "generated_on": today.isoformat(),
        "covered_by_bundle": tax_year in bundle.official,
        "next_only": next_only,
        "installments": [
            {
                "quarter": d.quarter,
                "tax_year": d.tax_year,
                "base_date": d.base_date.isoformat(),
                "due_date": d.due_date.isoformat(),
                "shift_reason": d.shift_reason,
                "days_remaining": (d.due_date - today).days,
            }
            for d in shown
        ],
        "source": bundle.source_note,
        "disclaimer": "Education only, not tax advice. Verify on IRS.gov.",
    }


def write_ics_file(path: str, payload: dict, bundle: Bundle) -> str:
    from .ics import build_ics

    content = build_ics(payload)
    Path(path).write_text(content, encoding="utf-8", newline="")
    return str(path)


def main(argv: list[str] | None = None) -> int:
    try:
        return run_cli(argv)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except BrokenPipeError:  # pragma: no cover
        return EXIT_ERROR
    except KeyboardInterrupt:  # pragma: no cover
        return 130
