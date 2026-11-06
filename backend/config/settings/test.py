"""Test settings: deterministic, fast, no external services except PostgreSQL."""

import os

# Tests must not depend on a developer's secrets; set a throwaway key before base reads it.
os.environ.setdefault(
    "DJANGO_SECRET_KEY", "test-only-insecure-key-padded-to-a-safe-hmac-length-0123456789"
)

from .base import *  # noqa: F403
from .base import REST_FRAMEWORK

DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost"]

# MD5 is insecure but ~100x faster; only acceptable because test passwords are throwaway.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Throttling needs a cache; locmem keeps tests independent of Redis. Each test clears it.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CELERY_TASK_ALWAYS_EAGER = True

REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {"anon": "1000/min", "user": "1000/min", "login": "5/min"},
}

LOGGING = {"version": 1, "disable_existing_loggers": False}
