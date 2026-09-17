from .base import *  # noqa: F403
from .base import env

DEBUG = False

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("SMTP_HOST")
EMAIL_PORT = env.int("SMTP_PORT", default=587)
EMAIL_HOST_USER = env("SMTP_USER")
EMAIL_HOST_PASSWORD = env("SMTP_PASSWORD")
EMAIL_USE_TLS = True
