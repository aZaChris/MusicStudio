"""Stripe gateway — the only module that imports `stripe` (ADR-013).

Everything else in the code base talks to these functions and plain data classes, so:
- tests replace this module with a fake (no network, no account needed);
- a provider change, or an SDK upgrade, touches one file.

Rules followed (Stripe best practices): a `StripeClient` instance (never the global key),
Checkout Sessions in `payment` mode, no `payment_method_types` (dynamic payment methods are
configured in the Dashboard), idempotency keys on create, signature-verified webhooks.
"""

import datetime
import json
from dataclasses import dataclass, field
from typing import Any

import stripe
from django.conf import settings

from apps.common.exceptions import ServiceUnavailable

# Tags our sessions in the Stripe Dashboard (fixed label + 8 random letters).
INTEGRATION_IDENTIFIER = "musicstudio_packages_qwhrmtzc"


class PaymentsUnavailable(ServiceUnavailable):
    code = "payments_unavailable"


class InvalidWebhook(Exception):
    """Missing/invalid signature or malformed payload."""


@dataclass(frozen=True)
class SessionInfo:
    """What we need from a Stripe Checkout Session, independent of the SDK."""

    id: str
    status: str  # open | complete | expired
    payment_status: str  # paid | unpaid | no_payment_required
    url: str = ""
    amount_total: int | None = None  # in cents
    expires_at: datetime.datetime | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionInfo":
        expires = data.get("expires_at")
        return cls(
            id=data["id"],
            status=data.get("status") or "",
            payment_status=data.get("payment_status") or "",
            url=data.get("url") or "",
            amount_total=data.get("amount_total"),
            expires_at=datetime.datetime.fromtimestamp(expires, datetime.UTC) if expires else None,
            metadata=dict(data.get("metadata") or {}),
        )


def _client() -> stripe.StripeClient:
    if not settings.STRIPE_API_KEY:
        raise PaymentsUnavailable("Online payments are not configured.")
    return stripe.StripeClient(settings.STRIPE_API_KEY, max_network_retries=2)


def _as_dict(obj: Any) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(str(obj)) if not isinstance(obj, dict) else obj
    return data


def create_checkout_session(
    *,
    checkout_id: str,
    amount_cents: int,
    currency: str,
    description: str,
    expires_at: datetime.datetime,
    idempotency_key: str,
    customer_email: str | None = None,
) -> SessionInfo:
    params: dict[str, Any] = {
        "mode": "payment",
        "line_items": [
            {
                "quantity": 1,
                "price_data": {
                    "currency": currency,
                    "unit_amount": amount_cents,
                    "product_data": {"name": description},
                },
            }
        ],
        "success_url": settings.CHECKOUT_SUCCESS_URL,
        "cancel_url": settings.CHECKOUT_CANCEL_URL,
        "client_reference_id": checkout_id,
        "metadata": {"checkout_id": checkout_id},
        "expires_at": int(expires_at.timestamp()),
        "integration_identifier": INTEGRATION_IDENTIFIER,
    }
    if customer_email:
        params["customer_email"] = customer_email
    try:
        session = _client().v1.checkout.sessions.create(
            params=params,  # type: ignore[arg-type]
            options={"idempotency_key": idempotency_key},
        )
    except stripe.StripeError as exc:
        raise PaymentsUnavailable("The payment provider is not reachable.") from exc
    return SessionInfo.from_dict(_as_dict(session))


def retrieve_checkout_session(session_id: str) -> SessionInfo:
    try:
        session = _client().v1.checkout.sessions.retrieve(session_id)
    except stripe.StripeError as exc:
        raise PaymentsUnavailable("The payment provider is not reachable.") from exc
    return SessionInfo.from_dict(_as_dict(session))


def verify_event(payload: bytes, signature: str | None) -> dict[str, Any]:
    """Check the Stripe-Signature header (HMAC of timestamp + raw body) and parse the event.

    Must receive the raw request body: re-serialised JSON would change the bytes and the
    signature would never match.
    """
    secret = settings.STRIPE_WEBHOOK_SECRET
    if not secret or not signature:
        raise InvalidWebhook("Missing webhook secret or signature.")
    try:
        stripe.Webhook.construct_event(payload, signature, secret)
    except (ValueError, stripe.SignatureVerificationError) as exc:
        raise InvalidWebhook(str(exc)) from exc
    event: dict[str, Any] = json.loads(payload)
    return event
