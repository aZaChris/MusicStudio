"""Stripe webhooks: verified, stored once, processed idempotently (US2, ADR-014)."""

import datetime

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.common.factories import PackageFactory
from apps.payments import services
from apps.payments.models import CheckoutSession, Payment, WebhookEvent

from .fakes import session_payload, signed_event

pytestmark = pytest.mark.django_db
URL = "/api/v1/webhooks/stripe/"


def _open_checkout(fake_stripe, price="120.00") -> CheckoutSession:
    package = PackageFactory(price=price)
    return services.start_checkout(package, user=package.student.teacher.user)


def _post(body: bytes, signature: str | None, capture) -> object:
    headers = {"HTTP_STRIPE_SIGNATURE": signature} if signature else {}
    with capture(execute=True):
        return APIClient().post(URL, data=body, content_type="application/json", **headers)


def test_completed_paid_session_records_one_card_payment(
    fake_stripe, django_capture_on_commit_callbacks
):
    checkout = _open_checkout(fake_stripe)
    body, sig = signed_event(
        "evt_1", "checkout.session.completed", session_payload(checkout.stripe_session_id)
    )

    res = _post(body, sig, django_capture_on_commit_callbacks)

    assert res.status_code == 200
    payment = Payment.objects.get()
    assert (payment.method, payment.status, payment.checkout_id) == ("card", "paid", checkout.id)
    checkout.refresh_from_db()
    assert checkout.status == CheckoutSession.Status.COMPLETED
    assert WebhookEvent.objects.get().processed_at is not None


def test_duplicate_deliveries_record_a_single_payment(
    fake_stripe, django_capture_on_commit_callbacks
):
    checkout = _open_checkout(fake_stripe)
    body, sig = signed_event(
        "evt_dup", "checkout.session.completed", session_payload(checkout.stripe_session_id)
    )

    statuses = [_post(body, sig, django_capture_on_commit_callbacks).status_code for _ in range(3)]

    assert statuses == [200, 200, 200]
    assert Payment.objects.count() == 1
    assert WebhookEvent.objects.count() == 1


def test_same_session_in_two_different_events_still_one_payment(
    fake_stripe, django_capture_on_commit_callbacks
):
    """completed + async_payment_succeeded for an instantly paid session (or a replay
    with a new event id): the OneToOne checkout → payment keeps it to one."""
    checkout = _open_checkout(fake_stripe)
    session = session_payload(checkout.stripe_session_id)
    for event_id, kind in [("evt_a", "completed"), ("evt_b", "async_payment_succeeded")]:
        body, sig = signed_event(event_id, f"checkout.session.{kind}", session)
        _post(body, sig, django_capture_on_commit_callbacks)

    assert Payment.objects.count() == 1


@pytest.mark.parametrize("signature", [None, "t=1,v1=deadbeef"])
def test_invalid_signature_is_refused_and_not_stored(
    fake_stripe, django_capture_on_commit_callbacks, signature
):
    checkout = _open_checkout(fake_stripe)
    body, _ = signed_event(
        "evt_x", "checkout.session.completed", session_payload(checkout.stripe_session_id)
    )

    res = _post(body, signature, django_capture_on_commit_callbacks)

    assert res.status_code == 400
    assert WebhookEvent.objects.count() == 0
    assert Payment.objects.count() == 0


def test_tampered_body_is_refused(fake_stripe, django_capture_on_commit_callbacks):
    checkout = _open_checkout(fake_stripe)
    body, sig = signed_event(
        "evt_t", "checkout.session.completed", session_payload(checkout.stripe_session_id)
    )

    res = _post(body.replace(b"12000", b"1"), sig, django_capture_on_commit_callbacks)

    assert res.status_code == 400


def test_delayed_method_waits_for_async_success(fake_stripe, django_capture_on_commit_callbacks):
    checkout = _open_checkout(fake_stripe)
    unpaid = session_payload(checkout.stripe_session_id, payment_status="unpaid")
    body, sig = signed_event("evt_c", "checkout.session.completed", unpaid)
    _post(body, sig, django_capture_on_commit_callbacks)
    assert Payment.objects.count() == 0  # SEPA-like: completed but not paid yet

    body, sig = signed_event(
        "evt_s",
        "checkout.session.async_payment_succeeded",
        session_payload(checkout.stripe_session_id),
    )
    _post(body, sig, django_capture_on_commit_callbacks)

    assert Payment.objects.count() == 1


def test_async_failure_marks_attempt_failed(fake_stripe, django_capture_on_commit_callbacks):
    checkout = _open_checkout(fake_stripe)
    session = session_payload(checkout.stripe_session_id, payment_status="unpaid")
    body, sig = signed_event("evt_f", "checkout.session.async_payment_failed", session)

    _post(body, sig, django_capture_on_commit_callbacks)

    checkout.refresh_from_db()
    assert checkout.status == CheckoutSession.Status.FAILED
    assert Payment.objects.count() == 0


def test_expired_session_marks_attempt_expired(fake_stripe, django_capture_on_commit_callbacks):
    checkout = _open_checkout(fake_stripe)
    session = session_payload(checkout.stripe_session_id, status="expired", payment_status="unpaid")
    body, sig = signed_event("evt_e", "checkout.session.expired", session)

    _post(body, sig, django_capture_on_commit_callbacks)

    checkout.refresh_from_db()
    assert checkout.status == CheckoutSession.Status.EXPIRED


def test_unknown_session_and_unhandled_types_are_acknowledged_without_effect(
    fake_stripe, django_capture_on_commit_callbacks
):
    for event_id, kind, session_id in [
        ("evt_u", "checkout.session.completed", "cs_test_other_env"),
        ("evt_h", "customer.created", "cus_1"),
    ]:
        body, sig = signed_event(event_id, kind, session_payload(session_id))
        assert _post(body, sig, django_capture_on_commit_callbacks).status_code == 200

    assert Payment.objects.count() == 0
    assert WebhookEvent.objects.filter(processed_at__isnull=False).count() == 2


def test_recorded_amount_is_what_stripe_charged(fake_stripe, django_capture_on_commit_callbacks):
    checkout = _open_checkout(fake_stripe, price="120.00")
    session = session_payload(checkout.stripe_session_id, amount=9900)
    body, sig = signed_event("evt_amt", "checkout.session.completed", session)

    _post(body, sig, django_capture_on_commit_callbacks)

    assert str(Payment.objects.get().amount) == "99.00"


def test_processing_twice_is_a_no_op(fake_stripe, django_capture_on_commit_callbacks):
    checkout = _open_checkout(fake_stripe)
    body, sig = signed_event(
        "evt_twice", "checkout.session.completed", session_payload(checkout.stripe_session_id)
    )
    _post(body, sig, django_capture_on_commit_callbacks)
    event = WebhookEvent.objects.get()

    assert services.process_webhook_event(event.pk) is False  # e.g. redelivered task
    assert Payment.objects.count() == 1


def test_reconciliation_records_a_payment_whose_webhook_was_lost(fake_stripe):
    from apps.payments.gateway import SessionInfo
    from apps.payments.tasks import reconcile_open_checkouts

    paid = _open_checkout(fake_stripe)
    expired = _open_checkout(fake_stripe)
    CheckoutSession.objects.update(expires_at=timezone.now() - datetime.timedelta(minutes=5))
    fake_stripe.sessions[paid.stripe_session_id] = SessionInfo(
        id=paid.stripe_session_id, status="complete", payment_status="paid", amount_total=12000
    )
    fake_stripe.sessions[expired.stripe_session_id] = SessionInfo(
        id=expired.stripe_session_id, status="expired", payment_status="unpaid"
    )

    assert reconcile_open_checkouts() == 2
    assert reconcile_open_checkouts() == 0  # idempotent

    assert Payment.objects.get().checkout_id == paid.id
    expired.refresh_from_db()
    assert expired.status == CheckoutSession.Status.EXPIRED
