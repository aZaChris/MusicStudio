"""The committed OpenAPI contract must describe what endpoints really return."""

import pytest
import yaml
from django.conf import settings

from apps.common.factories import StudentFactory
from apps.common.tests.helpers import client_for


def test_student_lessons_is_documented_as_a_list_of_lessons():
    contract = yaml.safe_load((settings.BASE_DIR / "openapi.yaml").read_text())
    schema = contract["paths"]["/api/v1/students/{id}/lessons/"]["get"]["responses"]["200"]
    body = schema["content"]["application/json"]["schema"]

    assert body == {"type": "array", "items": {"$ref": "#/components/schemas/Lesson"}}


def test_active_package_is_documented_as_nullable():
    contract = yaml.safe_load((settings.BASE_DIR / "openapi.yaml").read_text())
    field = contract["components"]["schemas"]["Student"]["properties"]["active_package"]

    assert field.get("nullable") is True


@pytest.mark.django_db
def test_student_without_package_returns_null_active_package():
    student = StudentFactory()

    res = client_for(student.teacher.user).get(f"/api/v1/students/{student.id}/")

    assert res.status_code == 200
    assert res.json()["active_package"] is None
