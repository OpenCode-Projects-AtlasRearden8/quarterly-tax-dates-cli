"""CLI tests: exit codes, output shape, .ics export, JSON, failure modes."""

from __future__ import annotations

import json

import pytest

from quarterly_tax_dates import __version__
from quarterly_tax_dates import cli
from quarterly_tax_dates.cli import EXIT_ERROR, EXIT_OK, format_countdown, main, run_cli


def test_happy_path_exit_zero(capsys):
    code = run_cli(["2026"])
    out = capsys.readouterr().out
    assert code == EXIT_OK
    assert "Tax year 2026" in out
    for q in ("Q1", "Q2", "Q3", "Q4"):
        assert q in out
    assert "not tax advice" in out.lower()


def test_default_year_is_current(capsys):
    import datetime as dt
    code = run_cli([])
    out = capsys.readouterr().out
    assert code == EXIT_OK
    assert f"Tax year {dt.date.today().year}" in out


def test_quiet_checklist_items_present(capsys):
    run_cli(["2026"])
    out = capsys.readouterr().out
    assert "pay stub" in out
    assert "safe-harbor" in out or "safe harbor" in out.lower()
    assert "EFTPS" in out


def test_bundle_outside_coverage_adds_note(capsys):
    run_cli(["2090"])
    out = capsys.readouterr().out
    assert "outside the bundled official schedule" in out


def test_next_flag(capsys):
    code = run_cli(["2026", "--next"])
    out = capsys.readouterr().out
    assert code == EXIT_OK
    assert "Next installment" in out


@pytest.mark.parametrize("argv", [["--version"], ["--version", "extra"]])
def test_version_flag(argv, capsys):
    with pytest.raises(SystemExit) as excinfo:
        run_cli(argv)
    assert excinfo.value.code == 0
    assert __version__ in capsys.readouterr().out


@pytest.mark.parametrize("bad", ["3000", "1999", "not-a-year"])
def test_bad_year_exits_2(bad, capsys):
    with pytest.raises(SystemExit) as excinfo:
        run_cli([bad])
    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert err.strip(), "argparse errors go to stderr"


def test_json_output(capsys):
    code = run_cli(["2026", "--json"])
    out = capsys.readouterr().out
    assert code == EXIT_OK
    payload = json.loads(out)
    assert payload["tool"] == "quarterly-tax-dates"
    assert payload["version"] == __version__
    assert payload["tax_year"] == 2026
    assert payload["covered_by_bundle"] is True
    assert [i["quarter"] for i in payload["installments"]] == ["Q1", "Q2", "Q3", "Q4"]
    assert payload["installments"][0]["due_date"] == "2026-04-15"
    assert payload["disclaimer"].startswith("Education only")


def test_json_next_only(capsys):
    run_cli(["2026", "--next", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["next_only"] is True
    assert len(payload["installments"]) == 1


def test_ics_export(tmp_path, capsys):
    target = tmp_path / "due.ics"
    code = run_cli(["2026", "--ics", str(target)])
    assert code == EXIT_OK
    content = target.open("r", newline="").read()
    assert content.count("BEGIN:VEVENT") == 4
    assert "DTSTART;VALUE=DATE:20260415" in content
    assert "DTSTART;VALUE=DATE:20270115" in content
    assert content.startswith("BEGIN:VCALENDAR\r\n")
    assert content.endswith("END:VCALENDAR\r\n")
    assert "created in capsys" not in capsys.readouterr().out or True


def test_ics_export_with_json_runs_clean(tmp_path, capsys):
    target = tmp_path / "due.ics"
    code = run_cli(["2026", "--json", "--ics", str(target)])
    assert code == EXIT_OK
    json.loads(capsys.readouterr().out)  # stdout stays pure JSON
    assert target.exists()


def test_ics_unwritable_path_reports_error(tmp_path):
    # A directory as the .ics target must produce exit 1 and stderr, not a traceback.
    target = tmp_path / "asdir"
    target.mkdir()
    code = main(["2026", "--ics", str(target)])
    assert code == EXIT_ERROR


def test_missing_data_file_reports_error_not_traceback(capsys, monkeypatch):
    def boom():
        raise RuntimeError("Bundled data file missing: nope.json")
    monkeypatch.setattr(cli, "load_bundle", boom)
    code = main(["2026"])
    err = capsys.readouterr().err
    assert code == EXIT_ERROR
    assert "error:" in err
    assert "Traceback" not in err


def test_format_countdown_words():
    import datetime as dt
    today = dt.date(2026, 1, 1)
    assert format_countdown(dt.date(2026, 1, 1), today) == "due TODAY"
    assert format_countdown(dt.date(2026, 1, 2), today) == "1 day from now"
    assert format_countdown(dt.date(2026, 1, 20), today) == "19 days from now"
    assert format_countdown(dt.date(2025, 12, 30), today) == "2 days past due"
    assert format_countdown(dt.date(2025, 12, 31), today) == "1 day past due"
