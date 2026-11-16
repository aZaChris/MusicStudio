"""Aiuti per i test dei rimborsi e delle contestazioni: un pagamento online già incassato e gli
eventi di Stripe (forma reale, ripulita) che lo toccano."""

from decimal import Decimal
from typing import Any

from rest_framework.test import APIClient

from apps.common.factories import connected_package
from apps.packages.models import Package
from apps.payments import services
from apps.payments.models import CheckoutSession, Payment

from .fakes import CONNECT_WEBHOOK_SECRET, session_payload, signed_event

CONNECT_URL = "/api/v1/webhooks/stripe-connect/"


def send_event(event_id: str, event_type: str, obj: dict[str, Any], account: str, capture) -> int:
    body, sig = signed_event(
        event_id, event_type, obj, secret=CONNECT_WEBHOOK_SECRET, account=account
    )
    with capture(execute=True):
        res = APIClient().post(
            CONNECT_URL, data=body, content_type="application/json", HTTP_STRIPE_SIGNATURE=sig
        )
    return res.status_code


def paid_online(
    capture, *, package: Package | None = None, price: str = "100.00", intent: str = "pi_1"
) -> tuple[Payment, CheckoutSession]:
    """Un pagamento online incassato per intero, passando dal flusso vero: checkout + evento."""
    package = package or connected_package(price=price)
    checkout = services.start_checkout(package, user=package.student.teacher.user)
    amount = int(Decimal(str(package.price)) * 100)
    send_event(
        f"evt_pay_{intent}",
        "checkout.session.completed",
        session_payload(checkout.stripe_session_id, amount=amount, payment_intent=intent),
        checkout.stripe_account_id,
        capture,
    )
    return Payment.objects.get(checkout=checkout), checkout


def refund_obj(
    refund_id: str, intent: str, cents: int, status: str = "succeeded"
) -> dict[str, Any]:
    return {
        "id": refund_id,
        "object": "refund",
        "amount": cents,
        "currency": "eur",
        "status": status,
        "payment_intent": intent,
        "charge": "ch_1",
    }


def dispute_obj(
    dispute_id: str, intent: str, cents: int, status: str = "needs_response"
) -> dict[str, Any]:
    return {
        "id": dispute_id,
        "object": "dispute",
        "amount": cents,
        "currency": "eur",
        "status": status,
        "payment_intent": intent,
        "charge": "ch_1",
        "reason": "fraudulent",
    }
