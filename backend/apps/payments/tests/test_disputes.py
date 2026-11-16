"""Una contestazione (chargeback) sul registro (US3, fase 9, ADR-038)."""

import pytest

from apps.audit.models import AuditEntry
from apps.common.tests.helpers import client_for
from apps.payments import services
from apps.payments.models import Payment, PaymentDispute, WebhookEvent

from .connect_helpers import dispute_obj, paid_online, send_event

pytestmark = pytest.mark.django_db


def _open(account, event_id, dispute_id, intent, cents, capture):
    return send_event(
        event_id, "charge.dispute.created", dispute_obj(dispute_id, intent, cents), account, capture
    )


def _close(account, event_id, dispute_id, intent, cents, status, capture):
    obj = dispute_obj(dispute_id, intent, cents, status=status)
    return send_event(event_id, "charge.dispute.closed", obj, account, capture)


def test_an_open_dispute_marks_the_payment_and_reverses_nothing(
    fake_stripe, django_capture_on_commit_callbacks
):
    payment, checkout = paid_online(django_capture_on_commit_callbacks)

    _open(
        checkout.stripe_account_id,
        "evt_d1",
        "dp_1",
        "pi_1",
        10000,
        django_capture_on_commit_callbacks,
    )

    assert PaymentDispute.objects.get().status == "open"
    assert not Payment.objects.filter(status="reversal").exists()
    assert services.package_is_paid(payment.package)
    rows = client_for(payment.student.teacher.user).get("/api/v1/payments/").data["results"]
    assert next(r for r in rows if r["id"] == payment.pk)["under_dispute"] is True


def test_a_lost_dispute_creates_a_dispute_reversal_and_reopens_the_package(
    fake_stripe, django_capture_on_commit_callbacks
):
    payment, checkout = paid_online(django_capture_on_commit_callbacks)
    account = checkout.stripe_account_id
    _open(account, "evt_d1", "dp_1", "pi_1", 10000, django_capture_on_commit_callbacks)

    _close(account, "evt_d2", "dp_1", "pi_1", 10000, "lost", django_capture_on_commit_callbacks)

    row = Payment.objects.get(reversal_of=payment)
    assert (row.cause, row.provider_ref, str(row.amount)) == ("dispute", "dp_1", "100.00")
    assert PaymentDispute.objects.get().status == "lost"
    assert not services.package_is_paid(payment.package)
    rows = client_for(payment.student.teacher.user).get("/api/v1/payments/").data["results"]
    assert next(r for r in rows if r["id"] == payment.pk)["under_dispute"] is False


def test_a_won_dispute_returns_to_normal_and_reverses_nothing(
    fake_stripe, django_capture_on_commit_callbacks
):
    payment, checkout = paid_online(django_capture_on_commit_callbacks)
    account = checkout.stripe_account_id
    _open(account, "evt_d1", "dp_1", "pi_1", 10000, django_capture_on_commit_callbacks)

    _close(account, "evt_d2", "dp_1", "pi_1", 10000, "won", django_capture_on_commit_callbacks)

    assert PaymentDispute.objects.get().status == "won"
    assert not Payment.objects.filter(status="reversal").exists()
    assert services.package_is_paid(payment.package)


def test_replays_of_the_open_and_close_events_change_nothing(
    fake_stripe, django_capture_on_commit_callbacks
):
    payment, checkout = paid_online(django_capture_on_commit_callbacks)
    account = checkout.stripe_account_id

    for _ in range(3):
        _open(account, "evt_d1", "dp_1", "pi_1", 10000, django_capture_on_commit_callbacks)
    for event_id in ["evt_d2", "evt_d2", "evt_d3"]:  # lo stesso evento e uno con un altro id
        _close(account, event_id, "dp_1", "pi_1", 10000, "lost", django_capture_on_commit_callbacks)

    assert PaymentDispute.objects.count() == 1
    assert Payment.objects.filter(reversal_of=payment).count() == 1
    assert AuditEntry.objects.filter(action="payment.dispute").count() == 3  # aperta, persa, storno


def test_a_close_without_the_open_event_still_works(
    fake_stripe, django_capture_on_commit_callbacks
):
    payment, checkout = paid_online(django_capture_on_commit_callbacks)

    _close(
        checkout.stripe_account_id,
        "evt_d2",
        "dp_9",
        "pi_1",
        10000,
        "lost",
        django_capture_on_commit_callbacks,
    )

    assert PaymentDispute.objects.get().stripe_dispute_id == "dp_9"
    assert Payment.objects.filter(reversal_of=payment, cause="dispute").count() == 1


def test_a_dispute_for_an_unknown_payment_is_flagged_and_changes_nothing(
    fake_stripe, django_capture_on_commit_callbacks
):
    _, checkout = paid_online(django_capture_on_commit_callbacks)

    _open(
        checkout.stripe_account_id,
        "evt_u",
        "dp_u",
        "pi_nobody",
        500,
        django_capture_on_commit_callbacks,
    )
    _close(
        checkout.stripe_account_id,
        "evt_v",
        "dp_u",
        "pi_nobody",
        500,
        "lost",
        django_capture_on_commit_callbacks,
    )

    assert (
        not PaymentDispute.objects.exists()
        and not Payment.objects.filter(status="reversal").exists()
    )
    kinds = set(
        WebhookEvent.objects.filter(outcome="needs_attention").values_list(
            "attention_kind", flat=True
        )
    )
    assert kinds == {"dispute_unmatched"}


def test_a_lost_dispute_after_a_full_refund_is_flagged_not_double_reversed(
    fake_stripe, django_capture_on_commit_callbacks
):
    payment, checkout = paid_online(django_capture_on_commit_callbacks)
    account = checkout.stripe_account_id
    from .connect_helpers import refund_obj

    send_event(
        "evt_r",
        "refund.updated",
        refund_obj("re_1", "pi_1", 10000),
        account,
        django_capture_on_commit_callbacks,
    )

    _close(account, "evt_d", "dp_1", "pi_1", 10000, "lost", django_capture_on_commit_callbacks)

    assert Payment.objects.filter(reversal_of=payment).count() == 1  # solo il rimborso
    event = WebhookEvent.objects.get(stripe_event_id="evt_d")
    assert (event.outcome, event.attention_kind) == ("needs_attention", "dispute_exceeds")
