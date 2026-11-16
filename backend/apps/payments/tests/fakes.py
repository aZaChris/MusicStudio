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
CONNECT_WEBHOOK_SECRET = "whsec_test_connect"


@dataclass
class FakeStripe:
    """Records calls; behaves like Stripe for what our code uses."""

    created: list[dict[str, Any]] = field(default_factory=list)
    sessions: dict[str, gateway.SessionInfo] = field(default_factory=dict)
    fail_create: bool = False
    # Fase 9: conti collegati. `session_accounts` ricorda su quale conto è nata ogni sessione.
    accounts: dict[str, gateway.AccountInfo] = field(default_factory=dict)
    account_keys: dict[str, str] = field(default_factory=dict)  # chiave di idempotenza -> conto
    account_params: list[dict[str, Any]] = field(default_factory=list)
    links: list[dict[str, Any]] = field(default_factory=list)
    session_accounts: dict[str, str | None] = field(default_factory=dict)
    retrieved: list[tuple[str, str | None]] = field(default_factory=list)
    fail_account: bool = False

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
        self.session_accounts[session_id] = kwargs.get("stripe_account")
        return info

    def retrieve_checkout_session(
        self, session_id: str, stripe_account: str | None = None
    ) -> gateway.SessionInfo:
        self.retrieved.append((session_id, stripe_account))
        return self.sessions[session_id]

    # --- Conti collegati (fase 9) ---------------------------------------------------------

    def create_account(self, *, studio_id: int, idempotency_key: str) -> gateway.AccountInfo:
        if self.fail_account:
            raise gateway.PaymentsUnavailable("The payment provider is not reachable.")
        self.account_params.append({"studio_id": studio_id, "idempotency_key": idempotency_key})
        # Come Stripe: la stessa chiave di idempotenza restituisce lo stesso conto.
        if idempotency_key in self.account_keys:
            return self.accounts[self.account_keys[idempotency_key]]
        account_id = f"acct_test_{len(self.accounts) + 1}"
        info = gateway.AccountInfo(id=account_id, card_payments="restricted", open_requirements=19)
        self.accounts[account_id] = info
        self.account_keys[idempotency_key] = account_id
        return info

    def create_account_link(
        self, *, account_id: str, return_url: str, refresh_url: str
    ) -> gateway.AccountLink:
        if self.fail_account:
            raise gateway.PaymentsUnavailable("The payment provider is not reachable.")
        self.links.append(
            {"account_id": account_id, "return_url": return_url, "refresh_url": refresh_url}
        )
        return gateway.AccountLink(
            url=f"https://connect.stripe.com/setup/s/{account_id}/{len(self.links)}",
            expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=5),
        )

    def retrieve_account(self, account_id: str) -> gateway.AccountInfo:
        if self.fail_account:
            raise gateway.PaymentsUnavailable("The payment provider is not reachable.")
        return self.accounts[account_id]

    def set_account(
        self,
        account_id: str,
        *,
        card_payments: str,
        open_requirements: int = 0,
        closed: bool = False,
    ) -> None:
        # Simula ciò che Stripe riferisce dopo che il titolare ha lavorato sulla sua pagina.
        self.accounts[account_id] = gateway.AccountInfo(
            id=account_id,
            card_payments=card_payments,
            open_requirements=open_requirements,
            closed=closed,
        )


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


def signed_event(
    event_id: str,
    event_type: str,
    session: dict[str, Any],
    *,
    secret: str = WEBHOOK_SECRET,
    account: str | None = None,
    livemode: bool = False,
) -> tuple[bytes, str]:
    """Body + Stripe-Signature header, built with Stripe's documented scheme
    (HMAC-SHA256 over "<timestamp>.<raw body>"), so the real SDK verifies it.

    `account` e `livemode` riproducono i campi di un evento di un conto collegato (fase 9)."""
    event: dict[str, Any] = {
        "id": event_id,
        "object": "event",
        "type": event_type,
        "livemode": livemode,
        "data": {"object": session},
    }
    if account:
        event["account"] = account
    body = json.dumps(event).encode()
    timestamp = int(time.time())
    digest = hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()
    return body, f"t={timestamp},v1={digest}"
