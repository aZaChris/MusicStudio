"""Strumenti per il contratto OpenAPI (ADR-012).

- `MusicStudioAutoSchema` etichetta ogni operazione con la sua app di dominio (lessons,
  payments...).
- `add_error_responses` documenta in un posto solo le risposte di errore che ogni client deve
  gestire, con schemi condivisi, invece di ripetere `@extend_schema(responses=...)` su ogni
  view (cosa facile da dimenticare). Il testo delle risposte resta in inglese: è il contratto.
Spiegazione: docs/learning/concetti/openapi-e-contratti.md.
"""

from typing import Any

from drf_spectacular.openapi import AutoSchema

ERROR_REF = {"$ref": "#/components/schemas/Error"}
VALIDATION_REF = {"$ref": "#/components/schemas/ValidationError"}

# Scritture che possono urtare i vincoli di sovrapposizione delle lezioni (409).
CONFLICT_PATHS = ("/api/v1/lessons/",)


class MusicStudioAutoSchema(AutoSchema):
    # Classe di schema usata da drf-spectacular (SPECTACULAR_SETTINGS in config/settings).
    def get_tags(self) -> list[str]:
        module = type(self.view).__module__  # es. "apps.lessons.views"
        if module.startswith("rest_framework_simplejwt"):
            return ["accounts"]
        parts = module.split(".")
        if parts[0] == "apps" and len(parts) > 1:
            return [parts[1]]
        tags: list[str] = super().get_tags()
        return tags


def _json(description: str, schema: dict[str, Any]) -> dict[str, Any]:
    return {"description": description, "content": {"application/json": {"schema": schema}}}


def add_error_responses(
    result: dict[str, Any], generator: Any, request: Any, public: bool
) -> dict[str, Any]:
    """Hook di postprocessing: componenti di errore condivisi e risposte per operazione."""
    schemas = result.setdefault("components", {}).setdefault("schemas", {})
    schemas["Error"] = {
        "type": "object",
        "properties": {
            "detail": {"type": "string"},
            "code": {"type": "string", "description": "Machine-readable reason (e.g. 409)."},
        },
        "required": ["detail"],
    }
    schemas["ValidationError"] = {
        "description": "Field name → list of messages, or a list of non-field messages.",
        "oneOf": [
            {"type": "object", "additionalProperties": {"type": "array", "items": {}}},
            {"type": "array", "items": {"type": "string"}},
        ],
    }

    for path, item in result.get("paths", {}).items():
        for method, operation in item.items():
            responses = operation.setdefault("responses", {})
            needs_auth = {} not in operation.get("security", [{}])
            if method in ("post", "put", "patch"):
                responses.setdefault("400", _json("Invalid input.", VALIDATION_REF))
            if "/auth/token/" in path:
                responses.setdefault("401", _json("Invalid credentials or token.", ERROR_REF))
            if needs_auth:
                responses.setdefault("401", _json("Missing or invalid token.", ERROR_REF))
                responses.setdefault("403", _json("Role or object not allowed.", ERROR_REF))
            if "{" in path:
                responses.setdefault("404", _json("Not found or outside your studio.", ERROR_REF))
            can_conflict = path.startswith(CONFLICT_PATHS) and not path.endswith("/cancel/")
            if method in ("post", "put", "patch") and can_conflict:
                responses.setdefault("409", _json("The time slot is already taken.", ERROR_REF))
            responses.setdefault("429", _json("Rate limit exceeded; see Retry-After.", ERROR_REF))
    return result
