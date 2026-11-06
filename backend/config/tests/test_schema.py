"""The committed OpenAPI contract must match the code (FR-013, ADR-012)."""

from pathlib import Path

import pytest
import yaml
from django.core.management import call_command

BACKEND_DIR = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def generated(tmp_path_factory) -> str:
    target = tmp_path_factory.mktemp("schema") / "openapi.yaml"
    call_command("spectacular", "--fail-on-warn", "--file", str(target))
    return target.read_text()


def test_committed_schema_is_up_to_date(generated):
    committed = (BACKEND_DIR / "openapi.yaml").read_text()

    assert committed == generated, (
        "backend/openapi.yaml is stale. Regenerate it with: "
        "uv run python manage.py spectacular --settings=config.settings.test --file openapi.yaml"
    )


def test_schema_documents_errors_and_tags(generated):
    schema = yaml.safe_load(generated)
    create_lesson = schema["paths"]["/api/v1/lessons/"]["post"]
    cancel = schema["paths"]["/api/v1/lessons/{id}/cancel/"]["post"]
    login = schema["paths"]["/api/v1/auth/token/"]["post"]

    assert create_lesson["tags"] == ["lessons"]
    assert {"400", "401", "403", "409", "429"} <= set(create_lesson["responses"])
    assert "409" not in cancel["responses"]
    assert "401" in login["responses"] and "403" not in login["responses"]
    assert {"Error", "ValidationError"} <= set(schema["components"]["schemas"])
