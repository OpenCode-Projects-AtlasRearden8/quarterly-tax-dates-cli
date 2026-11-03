# STATUS.md -- quarterly-tax-dates

Date: 2026-11-03

## What was built

`quarterly-tax-dates` -- a pure-stdlib, fully offline Python CLI that
computes US quarterly estimated-tax (Form 1040-ES) due dates for any tax
year and quietly guards them:

- **Date math** (`quarterly_tax_dates/dates.py`): April/June/September
  installments inside the tax year, plus "Q4" landing on January 15 of the
  *next* year. Weekend and federal/DC holiday shifts move a date to the
  next business day, including the gotchas the tool was built for:
  - MLK Day on January 15 (2024, 2029) slipping the prior year's Q4 to
    January 16;
  - DC Emancipation Day (April 16) pushing Q1 to April 17/18 (2023, 2028);
  - June 17, 2024 / September 16, 2024 style weekend slides;
  - New Year's Day observed back onto a Friday Dec 31 (fed observance
    rules) so followed-up years remain weekday-safe.
- **Bundled data file** (`quarterly_tax_dates/data/due_dates.json`): the
  documented shift rules, source note, official dates, and the "what to
  gather" checklist. Coverage: tax years 2023-2031. Years outside the
  window still compute offline from the rules, with a printed note.
  Regenerable via `python3 tools/generate_data.py`; tests cross-check the
  bundle against the rule engine so the two can never drift silently.
- **`__main__.py` entrypoint** so `python3 -m quarterly_tax_dates`
  works without installing, and **console script**
  `quarterly-tax-dates` after `pip install .` (validated in a clean venv,
  including the packaged data file).
- **Countdown checklist**: every installment prints its due date, a
  "days from now / past due" countdown, shift explanation when the date
  moved, and the same gather-list every time (pay stubs/1099s, payment
  receipts, prior-year return for safe-harbor check, bank info for Direct
  Pay/EFTPS). Plain ASCII output, disclaimer to end.
- **ICS export** (`--ics PATH`, `quarterly_tax_dates/ics.py`): RFC 5545
  VCALENDAR with four all-day VEVENTs, deterministic UIDs
  (`est-tax-qN-YEAR@asdale-dynamics.tax-dates`), CRLF line endings,
  75-octet folding, comma/semicolon escaping.
- **JSON output** (`--json`): tool version, tax year, per-installment
  base/due dates, shift reason, days remaining, coverage flag.
- **UX niceties**: `--next` (only the next upcoming installment),
  `--version`, argparse help, exit codes 0/1/2 (operational errors print
  `error: ...` on stderr, never a traceback).

## How to run it

```bash
python3 -m quarterly_tax_dates           # current tax year, full checklist
python3 -m quarterly_tax_dates 2023      # a past year
python3 -m quarterly_tax_dates --next    # next upcoming installment only
python3 -m quarterly_tax_dates 2026 --ics my-dates.ics
python3 -m quarterly_tax_dates 2026 --json

# installed command (after `pip install .`):
quarterly-tax-dates --help
```

## Verification results

- `python3 -m pytest`: **77 tests pass, 1 skip** (`0.07s`). The skip is the
  bundle-vs-computation cross-test for 2032, which is intentionally one
  year past the bundle window (verified by the sister tests).
- Date-math suite pins every officially published IRS date for tax years
  2023-2028 (Apr 18 2023; Jun 17 + Sep 16 2024; Jan 16 2024 for TY2023;
  Apr 18 2028 -- the Emancipation Day double-shift; Jan 18 2028 for TY2027,
  Sat lands + Mon MLK), plus property tests that no due date 2020-2050 ever
  lands on a weekend or holiday.
- ICS tests cover structure, all-day `VALUE=DATE` events, deterministic
  UIDs, folding <=75 octets after unfolding, escaping, and CRLF endings.
- CLI tests cover exit codes (0/1/2), JSON shape, `--next`, checklist
  content, un-covered-year note, unwritable ICS target, missing data file
  (friendly `error:` on stderr, no traceback), and an on-disk countdown
  for 2023 given the current system date.
- `pyflakes` clean (no unused imports/variables).
- Manual runs verified: `python3 -m quarterly_tax_dates 2023` (shift
  notes on Q1/Q4), `--next` (shows Q4 2026 due Jan 15, 2027 for Nov 3,
  2026), `--json` parse, `--ics` file content (4 events, correct
  DTSTARTs, CRLF), venv install with packaged data file, and missing-dir
  ICS error path.
- License: MIT with the exact line `Copyright (c) 2026 Asdale Dynamics,
  LLC`; README credits Asdale Dynamics, LLC.

## Known gaps

- **Rule-based years.** Tax years outside 2023-2031 are computed from the
  documented weekday/DC-holiday rules, not a curated official list. IRS
  has altered deadlines in disasters (hurricane extensions etc.) -- those
  one-off relief orders are NOT modeled, by design. Always confirm on
  IRS.gov before paying.
- **Empirical shells only.** The federal holiday table covers standard
  modern holidays (2020s-2050s). If Congress renames/creates holidays,
  `holidays.py` must be updated (tests will catch the weekend-landing
  invariant smell but not a *name* change).
- **No state estimated-tax support.** Federal-only. States have different
  quarter-alignment (some use 60/30-day conventions).
- **Checklist is general.** One shared gather-list for all four
  installments; no quarterly-specific items (e.g. Q4 reminders about
  retirement contributions are not differentiated).
- **ICS `DTSTAMP`** uses current UTC time, so the file's bytes differ
  between runs (UIDs stay stable).
- **Timezone**: "days remaining" is computed from local calendar dates
  (`date.today()`), not an explicit user timezone choice.
- **No `--quiet/--color/--ics-auto-open`** niceties; kept the CLI small on
  purpose (plain text, no emoji, no ANSI).

## Repo layout

```
quarterly-tax-dates-cli/
  LICENSE                     MIT (c) 2026 Asdale Dynamics, LLC
  README.md                   warm, plain-English usage guide
  STATUS.md                   this file
  pyproject.toml              packaging + pytest config
  .gitignore
  tools/generate_data.py      offline data-file generator
  quarterly_tax_dates/
    __init__.py
    __main__.py               `python -m quarterly_tax_dates`
    cli.py                    argparse, report, JSON, exit codes
    dates.py                  base dates + shift engine + bundle loader
    holidays.py               federal + DC Emancipation Day table
    ics.py                    RFC 5545 export
    data/due_dates.json       the bundled source of truth (2023-2031)
  tests/
    test_dates.py             IRS-pinned schedule + invariants
    test_holidays.py          observed-rule correctness
    test_bundle.py            data-file integrity
    test_cli.py               exit codes, JSON, checklist, failure modes
    test_ics.py               RFC 5545 shape
```
