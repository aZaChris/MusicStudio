"""Shared Django settings.

Every value that differs between environments comes from an environment variable
(documented in the repository's `.env.example`). Environment-specific modules
(`dev`, `test`, `prod`) only override what they must.
"""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
# A local `backend/.env` is a dev convenience; containers get real env vars instead.
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY: str = env("DJANGO_SECRET_KEY")
DEBUG: bool = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS: list[str] = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS: list[str] = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])
ADMIN_URL: str = env("DJANGO_ADMIN_URL", default="admin/")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    # Before staticfiles so runserver serves static files the same way as production.
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django.contrib.postgres",  # ExclusionConstraint, range types (ADR-009)
    # third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",  # refresh-token revocation (ADR-018)
    "drf_spectacular",
    "corsheaders",
    "django_filters",
    # local apps (one per business domain — see docs/learning/adr/ADR-002)
    "apps.accounts",
    "apps.studios",
    "apps.students",
    "apps.packages",
    "apps.lessons",
    "apps.payments",
    "apps.notifications",
    "apps.common",
]

MIDDLEWARE = [
    # First: the request id must exist before anything logs (ADR-019).
    "apps.common.logging.RequestIdMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": env.db(
        "DATABASE_URL", default="postgres://musicstudio:musicstudio@localhost:5432/musicstudio"
    ),
}
# Reuse connections for a minute instead of opening one per request.
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

REDIS_URL: str = env("REDIS_URL", default="redis://localhost:6379/0")

# The cache backs DRF throttling, so every web worker must share it (Redis, not locmem).
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("CACHE_URL", default=REDIS_URL),
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# MusicStudio serves EN/IT; clients own UI translation, this covers admin/emails.
LANGUAGE_CODE = "en-us"
LANGUAGES = [("en", "English"), ("it", "Italiano")]
TIME_ZONE: str = env("DJANGO_TIME_ZONE", default="Europe/Rome")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_SCHEMA_CLASS": "apps.common.schema.MusicStudioAutoSchema",
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    # Converts django.core.exceptions.ValidationError raised by services into a 400.
    "EXCEPTION_HANDLER": "apps.common.exceptions.exception_handler",
    # OWASP API4: bound how fast one client can hit the API. The `login` scope is applied
    # only to the token endpoint (see apps/accounts/views.py).
    "DEFAULT_THROTTLE_CLASSES": (
        "apps.common.throttling.AnonRateThrottle",
        "apps.common.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("THROTTLE_ANON", default="100/hour"),
        "user": env("THROTTLE_USER", default="1000/hour"),
        "login": env("THROTTLE_LOGIN", default="5/min"),
    },
}

SIMPLE_JWT = {
    # Access tokens are never checked against the blacklist (no query per request), so
    # their lifetime is the window in which a logged-out token still works (ADR-018).
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("JWT_ACCESS_MINUTES", default=15)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_DAYS", default=14)),
    "ROTATE_REFRESH_TOKENS": True,
    # A rotated refresh token is dead: replaying it (e.g. a stolen copy) is refused.
    "BLACKLIST_AFTER_ROTATION": True,
    "SIGNING_KEY": env("JWT_SIGNING_KEY", default=SECRET_KEY),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "MusicStudio API",
    "DESCRIPTION": "REST API for the MusicStudio teacher/parent platform.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    # Separate request/response components: read-only fields are not required in requests.
    "COMPONENT_SPLIT_REQUEST": True,
    "TAGS": [
        {"name": "accounts", "description": "Login (JWT) and the current user."},
        {"name": "studios", "description": "The studio (tenant) and its teachers."},
        {"name": "students", "description": "Students, their history and reassignment."},
        {"name": "packages", "description": "Prepaid lesson packages."},
        {"name": "lessons", "description": "Agenda, completion, cancellation, dashboard."},
        {"name": "payments", "description": "Manually recorded payments."},
    ],
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
        "apps.common.schema.add_error_responses",
    ],
}

CORS_ALLOWED_ORIGINS: list[str] = env.list("CORS_ALLOWED_ORIGINS", default=[])

# Celery
CELERY_BROKER_URL: str = env("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND: str = env("CELERY_RESULT_BACKEND", default=CELERY_BROKER_URL)
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
# Reliability (ADR-016): a task is acknowledged only after it finishes, so a worker that
# dies mid-task gets it redelivered. That means a task can run twice: every task must be
# idempotent. Prefetch 1 keeps long tasks from hoarding messages.
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_SOFT_TIME_LIMIT = env.int("CELERY_TASK_SOFT_TIME_LIMIT", default=60)
CELERY_TASK_TIME_LIMIT = env.int("CELERY_TASK_TIME_LIMIT", default=90)
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
# Keep Django's LOGGING (JSON + request id) in workers instead of Celery's own handlers.
CELERY_WORKER_HIJACK_ROOT_LOGGER = False
# Redis redelivers unacknowledged tasks after this many seconds; must exceed the longest
# task (including retries' countdown) or tasks run twice while still in progress.
CELERY_BROKER_TRANSPORT_OPTIONS = {"visibility_timeout": 3600}

# Stripe — online payments, TEST MODE ONLY (constitution IV, ADR-013).
# A restricted key (rk_test_...) with "Checkout Sessions: write" is recommended over sk_test_.
STRIPE_API_KEY: str = env("STRIPE_API_KEY", default="")
STRIPE_WEBHOOK_SECRET: str = env("STRIPE_WEBHOOK_SECRET", default="")
STRIPE_CURRENCY: str = env("STRIPE_CURRENCY", default="eur")
CHECKOUT_SUCCESS_URL: str = env(
    "CHECKOUT_SUCCESS_URL", default="http://localhost:5173/payments/success"
)
CHECKOUT_CANCEL_URL: str = env(
    "CHECKOUT_CANCEL_URL", default="http://localhost:5173/payments/cancel"
)
CHECKOUT_TTL_MINUTES: int = env.int("CHECKOUT_TTL_MINUTES", default=30)

if STRIPE_API_KEY and not STRIPE_API_KEY.startswith(("sk_test_", "rk_test_")):
    # Fail fast: this project must never move real money (live keys are sk_live_/rk_live_).
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured("STRIPE_API_KEY must be a test-mode key (sk_test_ or rk_test_).")

# Dashboard cache lifetime (ADR-017); data changes invalidate immediately.
DASHBOARD_CACHE_SECONDS: int = env.int("DASHBOARD_CACHE_SECONDS", default=300)

# Email (reminders) — console backend by default, SMTP in prod.py
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL: str = env("DEFAULT_FROM_EMAIL", default="noreply@musicstudio.local")

# Plain text for humans in dev; prod switches the formatter to JSON (ADR-019).
LOG_FORMAT: str = env("LOG_FORMAT", default="plain")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"request_id": {"()": "apps.common.logging.RequestIdFilter"}},
    "formatters": {
        "plain": {"format": "%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s"},
        "json": {"()": "apps.common.logging.JsonFormatter"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": LOG_FORMAT,
            "filters": ["request_id"],
        }
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
    "loggers": {
        # One line per request; set ACCESS_LOG_LEVEL=WARNING to silence it.
        "musicstudio.access": {"level": env("ACCESS_LOG_LEVEL", default="INFO")},
    },
}

# Reverse proxies in front of gunicorn that append to X-Forwarded-For (ADR-021).
TRUSTED_PROXY_COUNT: int = env.int("TRUSTED_PROXY_COUNT", default=0)

# Studio sizing guardrail from the product spec (1-10 teachers per studio)
STUDIO_MAX_TEACHERS = 10

# Package "running low" threshold (spec 001 FR-012)
PACKAGE_LOW_THRESHOLD = 2
