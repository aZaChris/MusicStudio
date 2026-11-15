"""Tracciamento errori con Sentry, ripulito da credenziali e dati personali (ADR-019).

Si inizializza solo da `config.settings.prod` e solo se SENTRY_DSN è impostato: senza, l'API
funziona uguale e gli errori arrivano comunque nei log.
Spiegazione: docs/learning/concetti/log-strutturati-e-sentry.md.

FUTURO (metriche applicative, ADR-019): oggi Sentry raccoglie solo errori e tracce; contare
eventi di dominio (lezioni create e completate) è rimandato.
"""

import re
from typing import Any

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration

from .logging import request_id_var

FILTERED = "[Filtered]"
_SECRET_HEADERS = {"authorization", "cookie", "stripe-signature", "x-csrftoken"}
# I corpi di queste rotte contengono password, token o eventi di pagamento: non si inviano mai.
_SENSITIVE_PATHS = ("/auth/", "/webhooks/")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def _scrub_text(value: Any) -> Any:
    # Sostituisce gli indirizzi email nei testi liberi (messaggi di errore, query string).
    return _EMAIL.sub(FILTERED, value) if isinstance(value, str) else value


def before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any]:
    # Ultimo filtro prima dell'invio a Sentry: header segreti, cookie, corpi sensibili, email.
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
    event.pop("user", None)  # resta solo il tag user_id impostato da get_tenant

    event.setdefault("tags", {})["request_id"] = request_id_var.get()
    return event


def init_sentry(dsn: str, environment: str, traces_sample_rate: float, release: str | None) -> None:
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        send_default_pii=False,  # niente IP, cookie o email degli utenti
        traces_sample_rate=traces_sample_rate,
        before_send=before_send,  # type: ignore[arg-type]
    )
