"""An empty variable must fall back to the default, as an unset one does (Coolify passes both)."""

import os
import subprocess
import sys

from cryptography.fernet import Fernet
from django.conf import settings


def test_production_settings_load_with_empty_optional_variables():
    env = {
        "PATH": os.environ["PATH"],
        "DJANGO_SETTINGS_MODULE": "config.settings.prod",
        "DJANGO_SECRET_KEY": "test-only",
        "JWT_SIGNING_KEY": "test-only",
        "DATABASE_URL": "postgres://u@localhost/db",
        "DJANGO_ALLOWED_HOSTS": "api.example.test",
        "DJANGO_CSRF_TRUSTED_ORIGINS": "https://api.example.test",
        "SMTP_HOST": "x",
        "SMTP_USER": "x",
        "SMTP_PASSWORD": "x",
        "FIELD_ENCRYPTION_KEYS": Fernet.generate_key().decode(),
        "FRONTEND_URL": "https://app.example.test",
        # Empty, as Coolify sends them to the worker and beat containers.
        "TRUSTED_PROXY_COUNT": "",
        "JWT_ACCESS_MINUTES": "",
        "SMTP_PORT": "",
    }
    code = "import django; django.setup(); from django.conf import settings; "
    code += "print(settings.TRUSTED_PROXY_COUNT)"
    result = subprocess.run(  # noqa: S603 - fixed interpreter and code, test-only
        [sys.executable, "-c", code],
        cwd=settings.BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "1"
