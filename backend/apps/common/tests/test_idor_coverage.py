"""Guard: every route under /api/v1/ is either covered by the IDOR suite or explicitly
declared as holding no tenant data. A new endpoint fails here until someone decides which."""

import re

from django.urls import URLPattern, URLResolver, get_resolver

from apps.common.tests.test_idor import ROUTES

# Routes that expose no tenant objects by id (or are tested elsewhere for their own rules).
NO_TENANT_DATA = {
    "",  # API root
    "auth/token/",
    "auth/token/refresh/",
    "auth/logout/",
    "auth/me/",
    "auth/register/",
    "auth/confirm-email/",
    "auth/confirm-email/resend/",
    "webhooks/stripe/",  # signed by Stripe, no user (apps/payments/tests)
}


def _api_routes() -> set[str]:
    found: set[str] = set()

    def walk(patterns, prefix):  # type: ignore[no-untyped-def]
        for p in patterns:
            text = prefix + str(p.pattern)
            if isinstance(p, URLResolver):
                walk(p.url_patterns, text)
            elif isinstance(p, URLPattern) and text.startswith("api/v1/"):
                route = text.removeprefix("api/v1/").replace("^", "").replace("$", "")
                if "format" in route:
                    continue  # DRF's ".json" suffix variants of the same views
                found.add(re.sub(r"\(\?P<pk>[^)]*\)", "<pk>", route))

    walk(get_resolver().url_patterns, "")
    return found


def test_every_api_route_is_covered_or_declared():
    missing = _api_routes() - ROUTES - NO_TENANT_DATA

    assert not missing, f"Add these routes to the IDOR suite (or NO_TENANT_DATA): {missing}"


def test_declared_routes_still_exist():
    stale = (ROUTES | NO_TENANT_DATA) - _api_routes()

    assert not stale, f"Remove routes that no longer exist: {stale}"
