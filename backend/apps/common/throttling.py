"""Rate limiting that survives a cache outage (ADR-017).

DRF throttles keep their counters in the cache (Redis). If Redis is down, the stock
classes raise and *every* request becomes a 500: a cache problem takes the whole API down.
These subclasses fail open — the request is allowed and the error is logged.

Trade-off, stated plainly: during a Redis outage there is no rate limiting, including on
login. We prefer availability; the outage is visible in logs and in /health/ready/.
"""

import logging
from typing import Any

from rest_framework import throttling
from rest_framework.request import Request

logger = logging.getLogger(__name__)


class FailOpenMixin:
    def allow_request(self, request: Request, view: Any) -> bool:
        try:
            allowed: bool = super().allow_request(request, view)  # type: ignore[misc]
            return allowed
        except Exception:
            logger.exception("Throttle cache unavailable; allowing request")
            return True


class AnonRateThrottle(FailOpenMixin, throttling.AnonRateThrottle):
    pass


class UserRateThrottle(FailOpenMixin, throttling.UserRateThrottle):
    pass


class ScopedRateThrottle(FailOpenMixin, throttling.ScopedRateThrottle):
    pass
