"""Cache della dashboard con chiavi a versione per studio (ADR-017).

La dashboard di uno studio è in cache sotto una chiave che contiene la *versione* dello studio.
Ogni scrittura su lezioni, pacchetti, pagamenti o studenti dello studio incrementa la versione
(`apps/common/signals.py`): tutte le vecchie chiavi diventano irraggiungibili in un colpo, senza
bisogno di sapere quali esistono. Le vecchie voci scadono da sole (TTL).

Se la cache è giù, la dashboard si calcola normalmente: una cache non deve mai essere un
punto unico di fallimento. Spiegazione: docs/learning/concetti/caching.md.
"""

import logging
from collections.abc import Callable
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.common.tenancy import TenantContext

logger = logging.getLogger(__name__)


def _version_key(studio_id: int) -> str:
    # Chiave Redis che tiene il numero di versione di uno studio.
    return f"dashboard:studio-version:{studio_id}"


def studio_version(studio_id: int) -> int:
    """Versione attuale della cache di uno studio (parte da 1)."""
    key = _version_key(studio_id)
    cache.add(key, 1, timeout=None)  # non fa nulla se la chiave esiste già
    version: int = cache.get(key) or 1
    return version


def bump_studio_version(studio_id: int) -> None:
    """Invalida tutta la dashboard dello studio alzando la versione."""
    try:
        cache.incr(_version_key(studio_id))
    except ValueError:  # chiave assente (espulsa o mai creata): qualsiasi valore nuovo invalida
        cache.set(_version_key(studio_id), 2, timeout=None)
    except Exception:
        logger.exception("Could not invalidate dashboard cache for studio %s", studio_id)


def cached_dashboard(ctx: TenantContext, compute: Callable[[], Any]) -> Any:
    """Restituisce la dashboard di `ctx`, dalla cache se lo studio non è cambiato."""
    if ctx.studio_id is None or ctx.is_parent:
        return compute()  # i genitori coprono più studi e aprono di rado la dashboard
    try:
        # La chiave contiene tutto ciò che cambia il risultato: studio, versione, ruolo,
        # insegnante e giorno. Utenti con permessi diversi non condividono mai una voce.
        key = ":".join(
            str(part)
            for part in (
                "dashboard:v1",
                ctx.studio_id,
                studio_version(ctx.studio_id),
                ctx.role,
                ctx.teacher_id,
                timezone.localdate(),  # "questa settimana" cambia a mezzanotte
            )
        )
        hit = cache.get(key)
    except Exception:
        # Cache non raggiungibile: si calcola senza, l'API non va giù (CLAUDE.md, "Gotchas").
        logger.exception("Dashboard cache unavailable; computing")
        return compute()
    if hit is not None:
        return hit
    data = compute()
    try:
        cache.set(key, data, timeout=settings.DASHBOARD_CACHE_SECONDS)
    except Exception:
        logger.exception("Could not store dashboard in cache")
    return data
