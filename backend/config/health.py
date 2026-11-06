"""Liveness and readiness probes (ADR-006).

- `/health/live/`: the process answers. No I/O, so a database outage never makes Docker
  restart otherwise healthy web containers.
- `/health/ready/`: the process can serve traffic — PostgreSQL and Redis both reachable.
  Returns 503 when any check fails, so the proxy/orchestrator stops routing to it.

Both are plain Django views: unauthenticated, not throttled, no DRF machinery.
"""

import logging
from collections.abc import Callable

import redis
from django.conf import settings
from django.db import connection
from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


def check_database() -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")


def check_redis() -> None:
    client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=1)
    client.ping()


CHECKS: dict[str, Callable[[], None]] = {"database": check_database, "redis": check_redis}


@require_GET
def live(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})


@require_GET
def ready(request: HttpRequest) -> JsonResponse:
    results: dict[str, str] = {}
    for name, check in CHECKS.items():
        try:
            check()
            results[name] = "ok"
        except Exception:
            logger.exception("Readiness check %s failed", name)
            results[name] = "error"
    healthy = all(value == "ok" for value in results.values())
    return JsonResponse(
        {"status": "ok" if healthy else "error", "checks": results},
        status=200 if healthy else 503,
    )
