"""Il registro umano delle deprecazioni non può divergere dal codice (ADR-040, research R1b)."""

from datetime import date
from pathlib import Path

from django.conf import settings

from apps.common import deprecation

REPO = Path(settings.BASE_DIR).parent
REGISTER = REPO / "docs/operations/deprecations.md"


def test_every_deprecated_endpoint_has_a_register_row_and_a_migration_report():
    registry = deprecation.load_registry()
    problems = deprecation.register_problems(registry, REGISTER.read_text(), REPO)
    assert problems == []


def test_the_check_names_a_missing_row_and_a_missing_report():
    item = deprecation.Deprecation(
        endpoint="GET /api/v1/things/",
        since=date(2026, 12, 1),
        sunset=date(2027, 3, 31),
        successor=None,
        report="docs/operations/migrations/does-not-exist.md",
    )
    problems = deprecation.register_problems([item], "| nothing here |", REPO)
    assert len(problems) == 2
    assert all("GET /api/v1/things/" in p for p in problems)


def test_a_matching_row_and_report_pass():
    item = deprecation.Deprecation(
        endpoint="GET /api/v1/things/",
        since=date(2026, 12, 1),
        sunset=date(2027, 3, 31),
        successor=None,
        report="docs/operations/migrations/TEMPLATE.md",
    )
    row = "| GET /api/v1/things/ | 2026-12-01 | 2027-03-31 | - | TEMPLATE.md | active |"
    assert deprecation.register_problems([item], row, REPO) == []
