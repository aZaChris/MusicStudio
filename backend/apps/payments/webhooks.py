"""Stripe webhook endpoint (ADR-014): check the source, verify, store once, ack fast."""

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
    """True when no allowlist is configured or `ip` is in it (single IPs or CIDR ranges)."""
    allowed = settings.STRIPE_WEBHOOK_ALLOWED_IPS
    if not allowed:
        return True
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(address in ipaddress.ip_network(entry, strict=False) for entry in allowed)


class StripeWebhookView(APIView):
    # Stripe authenticates with the signature, not with a user; it must never be throttled
    # (it retries on errors, and a 429 would just generate more deliveries).
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
            # Before any parsing: an outsider cannot even make us compute the HMAC.
            logger.warning("Stripe webhook refused from non-allowlisted address %s", ip)
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        try:
            # request.body = raw bytes; never request.data (re-serialising breaks the HMAC).
            event = gateway.verify_event(request.body, request.headers.get("Stripe-Signature"))
        except gateway.InvalidWebhook:
            return Response({"detail": "Invalid signature."}, status=status.HTTP_400_BAD_REQUEST)
        record_webhook_event(event)
        return Response({"received": True})
