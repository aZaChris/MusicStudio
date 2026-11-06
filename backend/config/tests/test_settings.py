"""Production settings must fail fast and trust the proxy's TLS header (audit G9)."""

import importlib
import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]

PROD_ENV = {
    "DJANGO_SETTINGS_MODULE": "config.settings.prod",
    "DJANGO_SECRET_KEY": "x" * 50,
    "JWT_SIGNING_KEY": "y" * 50,
    "DATABASE_URL": "postgres://u:p@db:5432/musicstudio",
    "DJANGO_ALLOWED_HOSTS": "api.example.com",
    "DJANGO_CSRF_TRUSTED_ORIGINS": "https://api.example.com",
    "SMTP_HOST": "smtp.example.com",
    "SMTP_USER": "u",
    "SMTP_PASSWORD": "p",
}


def _load_prod(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Import prod settings in a clean interpreter (settings are module-level state)."""
    code = (
        "from config.settings import prod as s;"
        "print(s.SECURE_PROXY_SSL_HEADER, s.DEBUG, sorted(s.ALLOWED_HOSTS),"
        " s.STORAGES['staticfiles']['BACKEND'])"
    )
    clean_env = {k: v for k, v in os.environ.items() if not k.startswith(("DJANGO_", "JWT_"))}
    return subprocess.run(  # noqa: S603 - fixed interpreter and code, test-only
        [sys.executable, "-c", code],
        cwd=BACKEND_DIR,
        env={**clean_env, **env},
        capture_output=True,
        text=True,
        check=False,
    )


def test_prod_settings_load_with_required_env():
    result = _load_prod(PROD_ENV)

    assert result.returncode == 0, result.stderr
    assert "('HTTP_X_FORWARDED_PROTO', 'https') False" in result.stdout
    assert "api.example.com" in result.stdout and "localhost" in result.stdout
    assert "CompressedManifestStaticFilesStorage" in result.stdout


def test_prod_settings_fail_fast_without_secret():
    env = {k: v for k, v in PROD_ENV.items() if k != "JWT_SIGNING_KEY"}

    result = _load_prod(env)

    assert result.returncode != 0
    assert "JWT_SIGNING_KEY" in result.stderr


def test_dev_settings_are_debug():
    os.environ.setdefault("DJANGO_SECRET_KEY", "test")
    dev = importlib.import_module("config.settings.dev")

    assert dev.DEBUG is True
