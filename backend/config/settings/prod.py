"""Production (Coolify). Fails fast on missing configuration.

TLS is terminated by Coolify's reverse proxy, which forwards plain HTTP to gunicorn and
sets `X-Forwarded-Proto`. Django must trust that header, otherwise every request looks
insecure and SECURE_SSL_REDIRECT would loop forever.
"""

from .base import *  # noqa: F403
from .base import env

DEBUG = False

# No defaults: a missing value raises ImproperlyConfigured at start-up, not at first use.
SECRET_KEY = env("DJANGO_SECRET_KEY")
JWT_SIGNING_KEY = env("JWT_SIGNING_KEY")
SIMPLE_JWT = {**SIMPLE_JWT, "SIGNING_KEY": JWT_SIGNING_KEY}  # noqa: F405
DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS")

# Container healthchecks call the app on localhost, from inside the container.
ALLOWED_HOSTS = [*ALLOWED_HOSTS, "localhost", "127.0.0.1"]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
# Healthchecks are plain HTTP inside the container network; never redirect them.
SECURE_REDIRECT_EXEMPT = [r"^health/"]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env.int("DJANGO_HSTS_SECONDS", default=60 * 60 * 24 * 30)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True

STORAGES = {
    **STORAGES,  # noqa: F405
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("SMTP_HOST")
EMAIL_PORT = env.int("SMTP_PORT", default=587)
EMAIL_HOST_USER = env("SMTP_USER")
EMAIL_HOST_PASSWORD = env("SMTP_PASSWORD")
EMAIL_USE_TLS = env.bool("SMTP_USE_TLS", default=True)
