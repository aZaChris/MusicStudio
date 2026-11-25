"""Il promemoria settimanale: diventa rosso a 30 giorni dalla rimozione (research R1b)."""

from datetime import UTC, date, datetime
from io import StringIO

import pytest
from django.core.management import CommandError, call_command

from apps.common import deprecation


def item(sunset: date) -> deprecation.Deprecation:
    return deprecation.Deprecation(
        endpoint="GET /api/v1/things/",
        since=date(2026, 1, 1),
        sunset=sunset,
        successor="/api/v2/things/",
        report="docs/operations/migrations/things.md",
    )


@pytest.fixture
def today(monkeypatch):
    monkeypatch.setattr(deprecation, "_now", lambda: datetime(2027, 1, 1, 9, tzinfo=UTC))


def run() -> str:
    out = StringIO()
    call_command("deprecation_report", stdout=out)
    return out.getvalue()


def test_no_deprecation_is_green(monkeypatch, today):
    monkeypatch.setattr(deprecation, "REGISTRY", [])
    assert "No active deprecations" in run()


def test_far_removal_date_prints_days_left_and_unknown_calls(monkeypatch, today):
    monkeypatch.setattr(deprecation, "REGISTRY", [item(date(2027, 3, 1))])
    out = run()
    assert "GET /api/v1/things/" in out
    assert "59 days left" in out
    assert "calls in the last 30 days: unknown" in out


@pytest.mark.parametrize("sunset", [date(2027, 1, 31), date(2026, 12, 1)])
def test_thirty_days_or_less_or_past_turns_red(monkeypatch, today, sunset):
    monkeypatch.setattr(deprecation, "REGISTRY", [item(sunset)])
    with pytest.raises(CommandError, match="GET /api/v1/things/"):
        run()
