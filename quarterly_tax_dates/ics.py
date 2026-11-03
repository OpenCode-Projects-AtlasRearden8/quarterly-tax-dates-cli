"""Build an RFC 5545 (.ics) calendar file. Pure stdlib, deterministic UIDs."""

from __future__ import annotations

import datetime as _dt

PRODID = "-//Asdale Dynamics LLC//quarterly-tax-dates//EN"


def _escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _fold(line: str) -> list[str]:
    """RFC 5545 says content lines longer than 75 octets are folded."""
    if len(line.encode("utf-8")) <= 75:
        return [line]
    out = [line[:75]]
    rest = line[75:]
    while rest:
        out.append(" " + rest[:74])
        rest = rest[74:]
    return out


def _event(uid, summary: str, due: _dt.date, description: str, stamp: _dt.datetime) -> list[str]:
    end_day = due + _dt.timedelta(days=1)
    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{stamp.strftime('%Y%m%dT%H%M%SZ')}",
        f"DTSTART;VALUE=DATE:{due.strftime('%Y%m%d')}",
        f"DTEND;VALUE=DATE:{end_day.strftime('%Y%m%d')}",
        f"SUMMARY:{_escape(summary)}",
        f"DESCRIPTION:{_escape(description)}",
        "TRANSP:TRANSPARENT",
        "CATEGORIES:PERSONAL,TAX",
        "END:VEVENT",
    ]
    return lines


def build_ics(payload: dict) -> str:
    stamp = _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODID}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:quarterly-tax-dates",
    ]
    for item in payload["installments"]:
        due = _dt.date.fromisoformat(item["due_date"])
        quarter = item["quarter"]
        year = item["tax_year"]
        summary = f"Estimated tax payment ({quarter}, tax year {year}) due"
        description = (
            f"Federal estimated tax installment {quarter} for tax year {year}. "
            "Pay via IRS Direct Pay (irs.gov/payments) or EFTPS. "
            "Education only, not tax advice."
        )
        lines += _event(
            uid=f"est-tax-{quarter.lower()}-{year}@asdale-dynamics.tax-dates",
            summary=summary,
            due=due,
            description=description,
            stamp=stamp,
        )
    lines.append("END:VCALENDAR")
    folded: list[str] = []
    for line in lines:
        folded.extend(_fold(line))
    return "\r\n".join(folded) + "\r\n"
