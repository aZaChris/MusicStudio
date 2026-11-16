"""Endpoint dei webhook di Stripe (ADR-014): controlla la provenienza, verifica, salva, risponde.

Il flusso, in ordine: 1) l'IP deve essere quello di Stripe; 2) la firma deve essere valida;
3) l'evento si salva una sola volta; 4) si risponde subito 200 e l'elaborazione vera la fa il
worker Celery. Spiegazione: docs/learning/concetti/webhook-idempotenti.md. Il filtro per IP è
l'ADR-021 (e docs/learning/concetti/ip-reale-dietro-proxy.md spiega come si legge l'IP vero).
"""

import ipaddress
import logging

from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.net import client_ip

from . import gateway
from .services import record_webhook_event

logger = logging.getLogger(__name__)


def is_allowed_source(ip: str) -> bool:
    """Vero se non c'è una lista di IP consentiti oppure `ip` ci sta dentro.

    La lista (STRIPE_WEBHOOK_ALLOWED_IPS) accetta IP singoli o intervalli CIDR.
    """
    allowed = settings.STRIPE_WEBHOOK_ALLOWED_IPS
    if not allowed:
        # Lista vuota = controllo spento (sviluppo e test). In produzione va compilata:
        # vedi docs/operations/runbook.md.
        return True
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(address in ipaddress.ip_network(entry, strict=False) for entry in allowed)


class _BaseStripeWebhookView(APIView):
    # Riceve gli eventi di Stripe. Niente utente: l'autenticazione è la firma.
    # Commento e non docstring: i docstring delle view finiscono in openapi.yaml.
    # Due endpoint, due segreti di firma (ADR-039): questa classe fa tutto il lavoro, le due
    # sottoclassi dicono solo quale impostazione contiene il segreto del proprio endpoint.
    signature_setting = "STRIPE_WEBHOOK_SECRET"

    # Stripe si autentica con la firma, non con un utente; e non va mai limitato (riprova
    # in caso di errore, quindi un 429 creerebbe solo altre consegne).
    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = ()

    @extend_schema(
        request=None,
        responses={
            200: OpenApiResponse(description="Event received (or duplicate)"),
            400: OpenApiResponse(description="Invalid payload or signature"),
            403: OpenApiResponse(description="Caller is not a Stripe webhook address"),
        },
        description="Stripe events, verified with the Stripe-Signature header.",
    )
    def post(self, request: Request) -> Response:
        ip = client_ip(request)
        if not is_allowed_source(ip):
            # Prima di qualsiasi lettura: un estraneo non può nemmeno farci calcolare l'HMAC.
            logger.warning("Stripe webhook refused from non-allowlisted address %s", ip)
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        try:
            # request.body = byte grezzi; mai request.data (ri-serializzare rompe l'HMAC).
            event = gateway.verify_event(
                request.body,
                request.headers.get("Stripe-Signature"),
                getattr(settings, self.signature_setting),
            )
        except gateway.InvalidWebhook:
            return Response({"detail": "Invalid signature."}, status=status.HTTP_400_BAD_REQUEST)
        # Un doppione non fa danni: record_webhook_event lo riconosce e non rimette in coda.
        record_webhook_event(event)
        return Response({"received": True})


class StripeWebhookView(_BaseStripeWebhookView):
    # Eventi del conto della piattaforma (fase 3).
    signature_setting = "STRIPE_WEBHOOK_SECRET"


class StripeConnectWebhookView(_BaseStripeWebhookView):
    # Eventi dei conti collegati degli studi: pagamenti, rimborsi, contestazioni (fase 9).
    # Stripe li consegna solo a un endpoint di tipo "Connected accounts", con un segreto suo.
    signature_setting = "STRIPE_CONNECT_WEBHOOK_SECRET"
