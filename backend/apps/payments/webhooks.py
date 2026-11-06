"""Stripe webhook endpoint (ADR-014): verify, store once, acknowledge fast."""

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from . import gateway
from .services import record_webhook_event


class StripeWebhookView(APIView):
    # Stripe authenticates with the signature, not with a user; it must never be throttled
    # (it retries on errors, and a 429 would just generate more deliveries).
    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = ()

    @extend_schema(
        request=None,
        responses={200: OpenApiResponse(description="Event received (or duplicate)")},
        description="Stripe events, verified with the Stripe-Signature header.",
    )
    def post(self, request: Request) -> Response:
        try:
            # request.body = raw bytes; never request.data (re-serialising breaks the HMAC).
            event = gateway.verify_event(request.body, request.headers.get("Stripe-Signature"))
        except gateway.InvalidWebhook:
            return Response({"detail": "Invalid signature."}, status=status.HTTP_400_BAD_REQUEST)
        record_webhook_event(event)
        return Response({"received": True})
