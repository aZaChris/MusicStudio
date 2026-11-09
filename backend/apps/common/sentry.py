"""Error tracking with Sentry, scrubbed of credentials and personal data (ADR-019).

Initialised only by `config.settings.prod` and only when SENTRY_DSN is set: without it the
API works exactly the same and errors still reach the logs.
"""

import re
from typing import Any

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration

from .logging import request_id_var

FILTERED = "[Filtered]"
_SECRET_HEADERS = {"authorization", "cookie", "stripe-signature", "x-csrftoken"}
# Bodies of these endpoints hold passwords, tokens or payment events: never sent.
_SENSITIVE_PATHS = ("/auth/", "/webhooks/")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def _scrub_text(value: Any) -> Any:
    return _EMAIL.sub(FILTERED, value) if isinstance(value, str) else value


def before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any]:
    request = event.get("request") or {}
    headers = request.get("headers") or {}
    for name in list(headers):
        if name.lower() in _SECRET_HEADERS:
            headers[name] = FILTERED
    request.pop("cookies", None)
    if any(p in str(request.get("url", "")) for p in _SENSITIVE_PATHS):
        request.pop("data", None)
    if "query_string" in request:
        request["query_string"] = _scrub_text(request["query_string"])

    for exc in (event.get("exception") or {}).get("values") or []:
        exc["value"] = _scrub_text(exc.get("value"))
    if isinstance(event.get("logentry"), dict):
        event["logentry"]["message"] = _scrub_text(event["logentry"].get("message"))
    event.pop("user", None)  # keep only the user_id tag set below

    event.setdefault("tags", {})["request_id"] = request_id_var.get()
    return event


def init_sentry(dsn: str, environment: str, traces_sample_rate: float, release: str | None) -> None:
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        send_default_pii=False,  # no IPs, cookies or user emails
        traces_sample_rate=traces_sample_rate,
        before_send=before_send,  # type: ignore[arg-type]
    )
