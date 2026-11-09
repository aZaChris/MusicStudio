"""The caller's real address behind reverse proxies (ADR-021).

Each proxy *appends* the address it received the connection from to `X-Forwarded-For`.
Everything to the left of what our own proxies appended was written by the client and
can be forged, so we count `TRUSTED_PROXY_COUNT` entries from the right and never read the
left-most value. With 0 trusted proxies (local dev) the socket address is the truth.
"""

from django.conf import settings
from django.http import HttpRequest


def client_ip(request: HttpRequest) -> str:
    trusted: int = settings.TRUSTED_PROXY_COUNT
    remote = str(request.META.get("REMOTE_ADDR", ""))
    if trusted <= 0:
        return remote
    forwarded = [p.strip() for p in request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")]
    forwarded = [p for p in forwarded if p]
    if len(forwarded) < trusted:
        # Fewer entries than proxies: the request did not come through them all.
        return remote
    return forwarded[-trusted]
