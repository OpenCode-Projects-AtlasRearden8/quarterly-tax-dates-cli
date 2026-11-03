# quarterly-tax-dates

A small, quiet Python CLI that guards the four quarterly US estimated-tax
deadlines. It computes the due dates for any tax year, shows a dated
countdown with a checklist of what to gather, and can export an `.ics`
calendar file. Pure standard library, fully offline -- no IRS API, no
network, no accounts, no tracked data.

Different from its sibling project **quarterly-taxes-calm-guide**: that one
is the how-to manual that explains estimated taxes like a friend would.
This one is the date math guard rail that keeps you from missing them.

Built and maintained by **Asdale Dynamics, LLC**. Education only -- not tax
advice. Always confirm dates and amounts on [IRS.gov](https://www.irs.gov).

## Why this exists

Every estimated-tax deadline has a story of confusion around it:

- **The Jan/June/Sen off-by-one trap.** "Q2" lands in June, not April. And
  the "Q4" payment for tax year 2026 isn't due in 2026 at all -- it's due
  January 15, 2027 (or the next business day).
- **The weekend slide.** When April 15, June 15, or September 15 falls on a
  Saturday, Sunday, or federal holiday, the IRS moves it to the next
  business day. June 17, 2024 was really "June 15, 2024."
- **The MLK trap.** Martin Luther King, Jr. Day can *be* January 15 (2024
  and 2029), so the previous year's Q4 payment slips to January 16.
- **The Emancipation Day trap.** DC Emancipation Day (April 16) pushed the
  2023 and 2028 tax deadlines to April 18.

This tool knows all of that, so you don't have to keep a scrap of paper
explaining it to yourself every year.

## Install & run

No dependencies, Python 3.9+:

```bash
# Run straight from the repo
python3 -m quarterly_tax_dates 2026

# Or install and get a friendlier command
pip install .
quarterly-tax-dates 2026
```

That prints something like:

```
Quarterly federal estimated-tax due dates (offline, from bundled IRS schedule).

Tax year 2026 estimated-tax payments (safe-harbor installments):

Q1 (tax year 2026) -- pay by Wednesday, April 15, 2026
    112 days from now
      - Last pay stub and any 1099s so far (wages, gig/1099 income, dividends, interest).
      - Receipts and confirmation numbers for any quarterly payments already made.
      - Last year's tax return, to sanity-check the 100%-of-last-tax safe-harbor amount (110% if your prior-year AGI was over $150,000).
      - Bank routing and account numbers if paying by IRS Direct Pay or EFTPS; sign up for EFTPS a week ahead.

Q2 (tax year 2026) -- pay by Monday, June 15, 2026
    ...
```

## Commands

| Command | What it does |
| --- | --- |
| `quarterly-tax-dates [YEAR]` | Full checklist for a tax year (default: current year) |
| `quarterly-tax-dates --next` | Just the next upcoming installment |
| `quarterly-tax-dates 2026 --ics my.ics` | Export an all-day `.ics` event per installment |
| `quarterly-tax-dates 2026 --json` | Machine-readable JSON (for scripts and reminders) |
| `quarterly-tax-dates --version` | Version number |

Exit codes: `0` success, `1` operational error (message on stderr, never a
traceback), `2` usage error.

## How the dates are sourced

The rules and the official covered schedule (2023-2031) live in a bundled
data file, `quarterly_tax_dates/data/due_dates.json`. Nothing is fetched
online. For years outside the bundled window, the same documented
weekday/holiday rules are extended to compute the dates offline; the CLI
prints a note saying the year is outside the bundled schedule.

The shift rule is the IRS one for income-tax deadlines: a due date that
lands on a Saturday, Sunday, or federal/DC holiday moves to the next
business day. DC holidays include Emancipation Day, which is why April
dates occasionally land on the 17th or 18th.

## Tests

```bash
python3 -m pytest
```

The suite (77+ cases) pins the rule engine against every officially
published IRS date in the covered window -- including the famous April 18
2023/2028 clumps, the June 17 and September 16 2024 weekend slides, and the
January 16 2024 MLK trap -- and asserts no generated due date ever lands on
a weekend or holiday, for tax years 2020-2050. It also checks ICS
structure (RFC 5545 folding, escaping, deterministic UIDs), CLI exit codes,
JSON shape, and bundle integrity (JSON parses, coverage is contiguous,
checklist present). To regenerate the bundled schedule after changing the
rules: `python3 tools/generate_data.py`.

## Tips for using the output

- Pay with **IRS Direct Pay** (irs.gov/payments) or **EFTPS**. Sign up for
  EFTPS at least a week before your first deadline so the login arrives in
  time.
- A common anchor is the **safe harbor**: paying 100% of last year's total
  tax (110% if your prior-year AGI was over $150,000), spread across the
  four installments, generally shields you from the underpayment penalty.
- The `.ics` exports are all-day events on each due date, with a note in
  the description. Import once and your calendar asks about it forever.

## Credits

Built with plain English and zero spooky complexity by
**Asdale Dynamics, LLC** -- the small company behind
[dylanasdale.github.io](https://dylanasdale.github.io) and the book
*The Massive AI Manual*, which explain AI like a friend would.

Licensed under the MIT license (see `LICENSE`). Copyright (c) 2026
Asdale Dynamics, LLC.
