"""Gli eventi si salvano ripuliti dei dati personali (fase 9, ADR-039, constitution X)."""

import json

import pytest

from apps.common.factories import PackageFactory
from apps.payments import services
from apps.payments.models import CheckoutSession, Payment, WebhookEvent

pytestmark = pytest.mark.django_db

PERSONAL = [
    "Maria Rossi",
    "maria.rossi@example.com",
    "Via Roma 1",
    "00100",
    "4242",
    "visa",
    "+390000000000",
    "secret-note",
]


def _noisy_session(session_id: str = "cs_test_1") -> dict:
    # Una Checkout Session reale porta il pagante dentro: nome, email, indirizzo, carta.
    return {
        "id": session_id,
        "object": "checkout.session",
        "status": "complete",
        "payment_status": "paid",
        "amount_total": 12000,
        "currency": "eur",
        "url": "https://checkout.stripe.com/c/pay/cs_test_1#fidXXXX",
        "customer_email": "maria.rossi@example.com",
        "customer_details": {
            "name": "Maria Rossi",
            "email": "maria.rossi@example.com",
            "phone": "+390000000000",
            "address": {"line1": "Via Roma 1", "postal_code": "00100", "city": "Roma"},
        },
        "shipping_details": {"name": "Maria Rossi", "address": {"line1": "Via Roma 1"}},
        "payment_method_details": {"card": {"brand": "visa", "last4": "4242"}},
        "payment_intent": {"id": "pi_1", "receipt_email": "maria.rossi@example.com"},
        "metadata": {"checkout_id": "abc", "studio_id": "7", "note": "secret-note"},
        "client_reference_id": "abc",
        "expires_at": 1790000000,
    }


def _event(obj: dict, event_type="checkout.session.completed", **top) -> dict:
    return {
        "id": "evt_1",
        "object": "event",
        "type": event_type,
        "livemode": False,
        "created": 1789999999,
        "account": "acct_x",
        "request": {"id": "req_1", "idempotency_key": "k"},
        "api_version": "2026-10-28",
        "data": {"object": obj},
        **top,
    }


def test_no_personal_data_survives_in_the_stored_payload():
    stored, _ = services.record_webhook_event(_event(_noisy_session()))

    text = json.dumps(WebhookEvent.objects.get(pk=stored.pk).payload)
    for value in PERSONAL:
        assert value not in text, f"{value!r} was stored"
    assert "checkout.stripe.com" not in text  # nemmeno l'indirizzo della pagina di pagamento


def test_what_the_handlers_need_is_kept():
    stored, _ = services.record_webhook_event(_event(_noisy_session()))

    payload = WebhookEvent.objects.get(pk=stored.pk).payload
    obj = payload["data"]["object"]
    assert (payload["id"], payload["type"], payload["account"]) == (
        "evt_1",
        "checkout.session.completed",
        "acct_x",
    )
    assert (obj["id"], obj["status"], obj["payment_status"], obj["amount_total"]) == (
        "cs_test_1",
        "complete",
        "paid",
        12000,
    )
    assert obj["payment_intent"] == "pi_1"  # espanso -> solo l'id
    assert obj["metadata"] == {"checkout_id": "abc", "studio_id": "7"}  # solo le chiavi nostre


def test_an_event_of_another_shape_is_scrubbed_too():
    refund = {
        "id": "re_1",
        "object": "refund",
        "amount": 3000,
        "currency": "eur",
        "status": "succeeded",
        "payment_intent": "pi_1",
        "charge": {"id": "ch_1", "billing_details": {"name": "Maria Rossi"}},
        "receipt_number": "1234-5678",
        "destination_details": {"card": {"reference": "abc"}},
    }

    scrubbed = services.scrub_event(_event(refund, "refund.updated"))

    obj = scrubbed["data"]["object"]
    assert obj["charge"] == "ch_1" and obj["amount"] == 3000 and obj["status"] == "succeeded"
    assert "Maria Rossi" not in json.dumps(scrubbed) and "receipt_number" not in obj
    assert "request" not in scrubbed and "api_version" not in scrubbed


def test_an_event_without_data_does_not_crash():
    assert services.scrub_event({"id": "evt_2", "type": "ping"}) == {
        "id": "evt_2",
        "type": "ping",
        "data": {"object": {"metadata": {}}},
    }


def test_the_scrubbed_event_still_completes_a_checkout(django_capture_on_commit_callbacks):
    # La prova che la ripulitura non toglie nulla che serva al flusso di pagamento.
    package = PackageFactory(price="120.00")
    checkout = CheckoutSession.objects.create(
        package=package, amount="120.00", currency="eur", stripe_session_id="cs_test_1"
    )
    with django_capture_on_commit_callbacks(execute=True):
        stored, _ = services.record_webhook_event(_event(_noisy_session(), account=None))

    stored.refresh_from_db()
    checkout.refresh_from_db()
    assert stored.outcome == WebhookEvent.Outcome.APPLIED
    assert checkout.status == CheckoutSession.Status.COMPLETED
    assert Payment.objects.get().amount == 120
