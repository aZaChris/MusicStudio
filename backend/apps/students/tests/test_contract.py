"""The committed OpenAPI contract must describe what endpoints really return."""

import yaml
from django.conf import settings


def test_student_lessons_is_documented_as_a_list_of_lessons():
    contract = yaml.safe_load((settings.BASE_DIR / "openapi.yaml").read_text())
    schema = contract["paths"]["/api/v1/students/{id}/lessons/"]["get"]["responses"]["200"]
    body = schema["content"]["application/json"]["schema"]

    assert body == {"type": "array", "items": {"$ref": "#/components/schemas/Lesson"}}
