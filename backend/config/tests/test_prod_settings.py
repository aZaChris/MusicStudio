"""Production security settings (OWASP API8) and the new phase-7 start-up requirements."""

import json

import pytest

from config.tests.test_settings import PROD_ENV, _load_prod_code

pytestmark = []

NAMES = [
    "SECURE_SSL_REDIRECT",
    "SECURE_HSTS_SECONDS",
    "SECURE_HSTS_INCLUDE_SUBDOMAINS",
    "SESSION_COOKIE_SECURE",
    "CSRF_COOKIE_SECURE",
    "SECURE_CONTENT_TYPE_NOSNIFF",
    "DEBUG",
]


def test_transport_and_cookie_protections_are_on():
    code = "import json; from config.settings import prod as s; print(json.dumps({"
    code += ",".join(f"'{n}': s.{n}" for n in NAMES) + "}))"
    result = _load_prod_code(PROD_ENV, code)

    assert result.returncode == 0, result.stderr
    values = json.loads(result.stdout)
    assert values["SECURE_SSL_REDIRECT"] is True
    assert values["SECURE_HSTS_SECONDS"] > 0 and values["SECURE_HSTS_INCLUDE_SUBDOMAINS"]
    assert values["SESSION_COOKIE_SECURE"] and values["CSRF_COOKIE_SECURE"]
    assert values["SECURE_CONTENT_TYPE_NOSNIFF"] and values["DEBUG"] is False


@pytest.mark.parametrize(
    ("missing", "needle"),
    [
        ("FIELD_ENCRYPTION_KEYS", "FIELD_ENCRYPTION_KEYS"),
        ("FRONTEND_URL", "FRONTEND_URL"),
        ("SMTP_HOST", "SMTP_HOST"),
        ("DJANGO_SECRET_KEY", "DJANGO_SECRET_KEY"),
    ],
)
def test_production_refuses_to_start_without(missing, needle):
    env = {k: v for k, v in PROD_ENV.items() if k != missing}

    result = _load_prod_code(env, "from config.settings import prod")

    assert result.returncode != 0
    assert needle in result.stderr


def test_production_refuses_a_malformed_encryption_key():
    result = _load_prod_code(
        {**PROD_ENV, "FIELD_ENCRYPTION_KEYS": "not-a-fernet-key"},
        "from config.settings import prod",
    )

    assert result.returncode != 0
    assert "FIELD_ENCRYPTION_KEYS" in result.stderr or "Fernet" in result.stderr
