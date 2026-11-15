"""Limiti di frequenza che sopravvivono a un guasto della cache (ADR-017).

I throttle di DRF tengono i contatori nella cache (Redis). Se Redis è giù, le classi standard
sollevano un'eccezione e *ogni* richiesta diventa un 500: un problema di cache butta giù
tutta l'API. Queste sottoclassi falliscono aperte: la richiesta passa e l'errore si registra.

Il compromesso, detto chiaro: durante un guasto di Redis non c'è limite di frequenza, nemmeno
sul login. Preferiamo la disponibilità; il guasto si vede nei log e in /health/ready/.
Spiegazione: docs/learning/concetti/caching.md (e CLAUDE.md, "Gotchas").
"""

import logging
from typing import Any

from rest_framework import throttling
from rest_framework.request import Request

logger = logging.getLogger(__name__)


class FailOpenMixin:
    # Va messo *prima* della classe DRF nell'ordine di ereditarietà, per intercettarne gli errori.
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
