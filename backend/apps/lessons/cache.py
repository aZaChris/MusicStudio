"""Dashboard cache with per-studio version keys (ADR-017).

The dashboard of a studio is cached under a key that contains the studio's *version*.
Any write to the studio's lessons, packages, payments or students bumps the version
(`apps/common/signals.py`), so every old key becomes unreachable at once — no need to know
which keys exist. Old entries simply expire (TTL).

If the cache is down, the dashboard is computed normally: a cache must never be a single
point of failure.
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
    return f"dashboard:studio-version:{studio_id}"


def studio_version(studio_id: int) -> int:
    key = _version_key(studio_id)
    cache.add(key, 1, timeout=None)  # no-op if it already exists
    version: int = cache.get(key) or 1
    return version


def bump_studio_version(studio_id: int) -> None:
    try:
        cache.incr(_version_key(studio_id))
    except ValueError:  # key missing (evicted or never set): any new value invalidates
        cache.set(_version_key(studio_id), 2, timeout=None)
    except Exception:
        logger.exception("Could not invalidate dashboard cache for studio %s", studio_id)


def cached_dashboard(ctx: TenantContext, compute: Callable[[], Any]) -> Any:
    """Return the dashboard for `ctx`, from the cache when the studio has not changed."""
    if ctx.studio_id is None or ctx.is_parent:
        return compute()  # parents span studios and rarely open the dashboard
    try:
        key = ":".join(
            str(part)
            for part in (
                "dashboard:v1",
                ctx.studio_id,
                studio_version(ctx.studio_id),
                ctx.role,
                ctx.teacher_id,
                timezone.localdate(),  # "this week" changes at midnight
            )
        )
        hit = cache.get(key)
    except Exception:
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
