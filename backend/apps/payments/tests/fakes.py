"""Test doubles for the Stripe gateway and real-algorithm webhook signatures."""

import datetime
import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from typing import Any

from apps.payments import gateway

WEBHOOK_SECRET = "whsec_test_musicstudio"


@dataclass
class FakeStripe:
    """Records calls; behaves like Stripe for what our code uses."""

    created: list[dict[str, Any]] = field(default_factory=list)
    sessions: dict[str, gateway.SessionInfo] = field(default_factory=dict)
    fail_create: bool = False

    def create_checkout_session(self, **kwargs: Any) -> gateway.SessionInfo:
        if self.fail_create:
            raise gateway.PaymentsUnavailable("The payment provider is not reachable.")
        self.created.append(kwargs)
        session_id = f"cs_test_{len(self.created)}"
        info = gateway.SessionInfo(
            id=session_id,
            status="open",
            payment_status="unpaid",
            url=f"https://checkout.stripe.com/c/pay/{session_id}",
            amount_total=kwargs["amount_cents"],
            expires_at=kwargs["expires_at"].astimezone(datetime.UTC).replace(microsecond=0),
            metadata={"checkout_id": kwargs["checkout_id"]},
        )
        self.sessions[session_id] = info
        return info

    def retrieve_checkout_session(self, session_id: str) -> gateway.SessionInfo:
        return self.sessions[session_id]


def session_payload(
    session_id: str, *, status: str = "complete", payment_status: str = "paid", amount: int = 12000
) -> dict[str, Any]:
    return {
        "id": session_id,
        "object": "checkout.session",
        "status": status,
        "payment_status": payment_status,
        "amount_total": amount,
        "url": None,
        "expires_at": int(time.time()) + 600,
        "metadata": {},
    }


def signed_event(event_id: str, event_type: str, session: dict[str, Any]) -> tuple[bytes, str]:
    """Body + Stripe-Signature header, built with Stripe's documented scheme
    (HMAC-SHA256 over "<timestamp>.<raw body>"), so the real SDK verifies it."""
    body = json.dumps(
        {"id": event_id, "object": "event", "type": event_type, "data": {"object": session}}
    ).encode()
    timestamp = int(time.time())
    digest = hmac.new(
        WEBHOOK_SECRET.encode(), f"{timestamp}.".encode() + body, hashlib.sha256
    ).hexdigest()
    return body, f"t={timestamp},v1={digest}"
