"""Request id, log JSON e propagazione verso Celery (ADR-019). Solo libreria standard.

- `RequestIdMiddleware` prende `X-Request-ID` dal proxy se sembra sicuro, altrimenti ne crea uno
  nuovo, lo rimanda nella risposta e scrive una riga di accesso per richiesta.
- `RequestIdFilter` marca ogni riga di log con l'id corrente (una ContextVar, quindi corretta
  per thread e per task asincrono).
- Celery: l'id viaggia negli header del messaggio, così i log di un task avviato da una
  richiesta condividono l'id di quella richiesta.
- `JsonFormatter` scrive un oggetto JSON per riga: ciò che i raccoglitori di log si aspettano.
Spiegazione: docs/learning/concetti/log-strutturati-e-sentry.md.
"""

import json
import logging
import re
import time
import uuid
from collections.abc import Callable
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from typing import Any

from django.http import HttpRequest, HttpResponse

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

HEADER = "X-Request-ID"
_SAFE_ID = re.compile(r"^[A-Za-z0-9-]{1,64}$")  # niente spazi o a capo: niente log injection
access_logger = logging.getLogger("musicstudio.access")


def _incoming_id(request: HttpRequest) -> str:
    # Un id che arriva dal client si accetta solo se è innocuo; altrimenti se ne genera uno.
    candidate = request.headers.get(HEADER, "")
    return candidate if _SAFE_ID.match(candidate) else uuid.uuid4().hex


class RequestIdMiddleware:
    # Middleware: assegna l'id alla richiesta e scrive la riga di accesso a risposta pronta.
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Qui non si azzera: Django scrive i log 4xx/5xx ("django.request") *dopo* che la catena
        # dei middleware è tornata. `clear_request_id` gira su request_finished, dopo quella riga.
        request_id_var.set(_incoming_id(request))
        started = time.monotonic()
        response = self.get_response(request)
        response[HEADER] = request_id_var.get()
        self._log(request, response.status_code, started)
        return response

    @staticmethod
    def _log(request: HttpRequest, status: int, started: float) -> None:
        match = getattr(request, "resolver_match", None)
        tenant = getattr(request, "_tenant_context", None)  # messo in cache da get_tenant, 0 query
        user = getattr(request, "user", None)  # DRF copia l'utente del JWT sull'HttpRequest
        access_logger.info(
            "%s %s %s",
            request.method,
            request.path,
            status,
            extra={
                "method": request.method,
                # Il modello di rotta raggruppa /lessons/12/ e /lessons/13/ nella stessa voce.
                "route": match.route.lstrip("^").rstrip("$") if match else request.path,
                "status": status,
                "duration_ms": round((time.monotonic() - started) * 1000, 1),
                "user_id": getattr(user, "pk", None),
                "studio_id": getattr(tenant, "studio_id", None),
            },
        )


def clear_request_id(**_: Any) -> None:
    """request_finished: la risposta è chiusa; nient'altro appartiene a questa richiesta."""
    request_id_var.set("-")


class RequestIdFilter(logging.Filter):
    # Aggiunge `request_id` a ogni record, così il formatter può stamparlo.
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class TaskArgsFilter(logging.Filter):
    """Il record "task succeeded" di Celery porta gli argomenti del task in `data`. I nostri
    includono token monouso e id utente, quindi non devono mai finire in un log (constitution X)."""

    def filter(self, record: logging.LogRecord) -> bool:
        data = getattr(record, "data", None)
        if isinstance(data, dict):
            record.data = {k: v for k, v in data.items() if k not in ("args", "kwargs")}
        return True


# Campi che ogni LogRecord ha già: tutto il resto (passato con extra={...}) diventa un campo JSON.
_STANDARD = set(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {
    "message",
    "asctime",
    "request_id",
}


class JsonFormatter(logging.Formatter):
    # Una riga = un oggetto JSON, con orario in UTC e request id.
    def format(self, record: logging.LogRecord) -> str:
        data: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", request_id_var.get()),
        }
        # Tutto ciò che si passa con extra={...} diventa un campo di primo livello.
        data.update({k: v for k, v in record.__dict__.items() if k not in _STANDARD})
        if record.exc_info:
            data["exc"] = self.formatException(record.exc_info)
        return json.dumps(data, default=str)


# --- Propagazione verso Celery --------------------------------------------------------
_CTX_RESET_ATTR = "_request_id_token"


def stamp_task_headers(headers: dict[str, Any] | None = None, **_: Any) -> None:
    """before_task_publish: copia l'id corrente negli header del messaggio."""
    current = request_id_var.get()
    if headers is not None and current != "-":
        headers.setdefault("request_id", current)


def bind_task_request_id(task: Any = None, **_: Any) -> None:
    """task_prerun: i log del task portano l'id della richiesta che lo ha messo in coda."""
    incoming = getattr(task.request, "request_id", None) if task is not None else None
    if incoming and _SAFE_ID.match(str(incoming)):
        setattr(task.request, _CTX_RESET_ATTR, request_id_var.set(str(incoming)))


def unbind_task_request_id(task: Any = None, **_: Any) -> None:
    """task_postrun: ripristina l'id precedente (i thread del worker vengono riutilizzati)."""
    token: Token[str] | None = getattr(task.request, _CTX_RESET_ATTR, None) if task else None
    if token is not None:
        request_id_var.reset(token)


def connect_signals() -> None:
    # Chiamata da CommonConfig.ready. `weak=False`: le funzioni sono di modulo e devono restare
    # collegate anche se nessun altro le referenzia.
    from celery.signals import before_task_publish, task_postrun, task_prerun
    from django.core.signals import request_finished

    request_finished.connect(clear_request_id, weak=False)
    before_task_publish.connect(stamp_task_headers, weak=False)
    task_prerun.connect(bind_task_request_id, weak=False)
    task_postrun.connect(unbind_task_request_id, weak=False)
