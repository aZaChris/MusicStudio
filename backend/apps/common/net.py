"""L'indirizzo reale di chi chiama, dietro i reverse proxy (ADR-021).

Ogni proxy *aggiunge in coda* a `X-Forwarded-For` l'indirizzo da cui ha ricevuto la connessione.
Tutto ciò che sta a sinistra di quanto aggiunto dai nostri proxy l'ha scritto il client e si
può falsificare: quindi si contano `TRUSTED_PROXY_COUNT` voci da destra e non si legge mai il
valore più a sinistra. Con 0 proxy fidati (sviluppo locale) vale l'indirizzo del socket.
Spiegazione: docs/learning/concetti/ip-reale-dietro-proxy.md.
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
        # Meno voci che proxy: la richiesta non è passata da tutti, ci si fida solo del socket.
        return remote
    return forwarded[-trusted]
