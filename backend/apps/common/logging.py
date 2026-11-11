"""Request id, JSON logs and Celery propagation (ADR-019). Stdlib only.

- `RequestIdMiddleware` takes `X-Request-ID` from the proxy when it looks safe, otherwise
  makes a new one, echoes it in the response and writes one access line per request.
- `RequestIdFilter` stamps every log record with the current id (a ContextVar, so it is
  correct per thread and per async task).
- Celery: the id travels in the task message headers, so the logs of a task started by a
  request share that request's id.
- `JsonFormatter` writes one JSON object per line: what log collectors expect.
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
_SAFE_ID = re.compile(r"^[A-Za-z0-9-]{1,64}$")  # no spaces/newlines: no log injection
access_logger = logging.getLogger("musicstudio.access")


def _incoming_id(request: HttpRequest) -> str:
    candidate = request.headers.get(HEADER, "")
    return candidate if _SAFE_ID.match(candidate) else uuid.uuid4().hex


class RequestIdMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Not reset here: Django logs 4xx/5xx ("django.request") *after* the middleware
        # chain returns. `clear_request_id` runs on request_finished, after that log line.
        request_id_var.set(_incoming_id(request))
        started = time.monotonic()
        response = self.get_response(request)
        response[HEADER] = request_id_var.get()
        self._log(request, response.status_code, started)
        return response

    @staticmethod
    def _log(request: HttpRequest, status: int, started: float) -> None:
        match = getattr(request, "resolver_match", None)
        tenant = getattr(request, "_tenant_context", None)  # cached by get_tenant, no query
        user = getattr(request, "user", None)  # DRF copies the JWT user onto HttpRequest
        access_logger.info(
            "%s %s %s",
            request.method,
            request.path,
            status,
            extra={
                "method": request.method,
                # The route pattern groups /lessons/12/ and /lessons/13/ together.
                "route": match.route.lstrip("^").rstrip("$") if match else request.path,
                "status": status,
                "duration_ms": round((time.monotonic() - started) * 1000, 1),
                "user_id": getattr(user, "pk", None),
                "studio_id": getattr(tenant, "studio_id", None),
            },
        )


def clear_request_id(**_: Any) -> None:
    """request_finished: the response is closed; nothing else belongs to this request."""
    request_id_var.set("-")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class TaskArgsFilter(logging.Filter):
    """Celery's "task succeeded" record carries the task's arguments in `data`. Ours include
    one-time tokens and user ids, so they never reach a log (constitution X)."""

    def filter(self, record: logging.LogRecord) -> bool:
        data = getattr(record, "data", None)
        if isinstance(data, dict):
            record.data = {k: v for k, v in data.items() if k not in ("args", "kwargs")}
        return True


_STANDARD = set(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {
    "message",
    "asctime",
    "request_id",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", request_id_var.get()),
        }
        # Anything passed with extra={...} becomes a top-level field.
        data.update({k: v for k, v in record.__dict__.items() if k not in _STANDARD})
        if record.exc_info:
            data["exc"] = self.formatException(record.exc_info)
        return json.dumps(data, default=str)


# --- Celery propagation ---------------------------------------------------------------
_CTX_RESET_ATTR = "_request_id_token"


def stamp_task_headers(headers: dict[str, Any] | None = None, **_: Any) -> None:
    """before_task_publish: copy the current id into the message headers."""
    current = request_id_var.get()
    if headers is not None and current != "-":
        headers.setdefault("request_id", current)


def bind_task_request_id(task: Any = None, **_: Any) -> None:
    """task_prerun: make the task's logs carry the id of the request that queued it."""
    incoming = getattr(task.request, "request_id", None) if task is not None else None
    if incoming and _SAFE_ID.match(str(incoming)):
        setattr(task.request, _CTX_RESET_ATTR, request_id_var.set(str(incoming)))


def unbind_task_request_id(task: Any = None, **_: Any) -> None:
    """task_postrun: restore the previous id (worker threads are reused)."""
    token: Token[str] | None = getattr(task.request, _CTX_RESET_ATTR, None) if task else None
    if token is not None:
        request_id_var.reset(token)


def connect_signals() -> None:
    from celery.signals import before_task_publish, task_postrun, task_prerun
    from django.core.signals import request_finished

    request_finished.connect(clear_request_id, weak=False)
    before_task_publish.connect(stamp_task_headers, weak=False)
    task_prerun.connect(bind_task_request_id, weak=False)
    task_postrun.connect(unbind_task_request_id, weak=False)
