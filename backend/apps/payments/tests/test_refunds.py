"""Un rimborso fatto su Stripe diventa uno storno nel registro (US3, fase 9, ADR-038)."""

import datetime
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.audit.models import AuditEntry
from apps.common.factories import PaymentFactory
from apps.common.tests.helpers import client_for
from apps.payments import selectors, services
from apps.payments.models import Payment, WebhookEvent

from .connect_helpers import paid_online, refund_obj, send_event

pytestmark = pytest.mark.django_db


def _refund(payment_account, event_id, refund_id, intent, cents, capture, **kw):
    return send_event(
        event_id,
        "refund.updated",
        refund_obj(refund_id, intent, cents, **kw),
        payment_account,
        capture,
    )


def test_a_full_refund_creates_one_linked_reversal_and_reopens_the_package(
    fake_stripe, django_capture_on_commit_callbacks
):
    payment, checkout = paid_online(django_capture_on_commit_callbacks)
    before = Payment.objects.filter(pk=payment.pk).values().get()

    _refund(
        checkout.stripe_account_id,
        "evt_r1",
        "re_1",
        "pi_1",
        10000,
        django_capture_on_commit_callbacks,
    )

    row = Payment.objects.get(reversal_of=payment)
    assert (row.cause, row.provider_ref, row.amount, row.status) == (
        "refund",
        "re_1",
        Decimal("100.00"),
        "reversal",
    )
    assert row.date == timezone.localdate()  # datato oggi, mai a ritroso
    assert (
        Payment.objects.filter(pk=payment.pk).values().get() == before
    )  # l'originale non si tocca
    assert not services.package_is_paid(payment.package)
    assert WebhookEvent.objects.get(stripe_event_id="evt_r1").outcome == "applied"


def test_the_register_net_is_zero_after_a_full_refund(
    fake_stripe, django_capture_on_commit_callbacks
):
    payment, checkout = paid_online(django_capture_on_commit_callbacks)
    _refund(
        checkout.stripe_account_id,
        "evt_r1",
        "re_1",
        "pi_1",
        10000,
        django_capture_on_commit_callbacks,
    )
    owner_ctx = _ctx(payment)

    summary = selectors.register_summary(owner_ctx, payment.date, datetime.date.today())

    assert summary["totals"]["received"] == Decimal("100.00")
    assert summary["totals"]["reversed"] == Decimal("100.00")
    assert summary["totals"]["net"] == Decimal("0.00")


def _ctx(payment):
    from apps.common.tenancy import resolve_tenant

    return resolve_tenant(payment.student.teacher.user)


def test_a_partial_refund_lowers_the_net_but_leaves_the_package_paid(
    fake_stripe, django_capture_on_commit_callbacks
):
    payment, checkout = paid_online(django_capture_on_commit_callbacks)

    _refund(
        checkout.stripe_account_id,
        "evt_r1",
        "re_1",
        "pi_1",
        3000,
        django_capture_on_commit_callbacks,
    )

    assert services.package_is_paid(payment.package)
    summary = selectors.register_summary(_ctx(payment), payment.date, datetime.date.today())
    assert summary["totals"]["net"] == Decimal("70.00")
    annotated = selectors.with_reversals(Payment.objects.filter(pk=payment.pk)).get()
    assert annotated.reversed_amount == Decimal("30.00") and not selectors.is_reversed(annotated)


def test_two_partial_refunds_that_add_up_reverse_the_payment(
    fake_stripe, django_capture_on_commit_callbacks
):
    payment, checkout = paid_online(django_capture_on_commit_callbacks)

    for n, cents in enumerate([3000, 7000], 1):
        _refund(
            checkout.stripe_account_id,
            f"evt_{n}",
            f"re_{n}",
            "pi_1",
            cents,
            django_capture_on_commit_callbacks,
        )

    assert not services.package_is_paid(payment.package)
    assert Payment.objects.filter(reversal_of=payment).count() == 2


def test_the_same_refund_notified_several_times_makes_one_row(
    fake_stripe, django_capture_on_commit_callbacks
):
    payment, checkout = paid_online(django_capture_on_commit_callbacks)
    account = checkout.stripe_account_id

    for event_id in [
        "evt_a",
        "evt_a",
        "evt_b",
        "evt_c",
    ]:  # lo stesso evento, e altri eventi dello stesso rimborso
        _refund(account, event_id, "re_1", "pi_1", 4000, django_capture_on_commit_callbacks)

    assert Payment.objects.filter(reversal_of=payment).count() == 1


def test_a_refund_still_pending_does_nothing_until_it_succeeds(
    fake_stripe, django_capture_on_commit_callbacks
):
    payment, checkout = paid_online(django_capture_on_commit_callbacks)
    account = checkout.stripe_account_id

    _refund(
        account, "evt_p", "re_1", "pi_1", 4000, django_capture_on_commit_callbacks, status="pending"
    )
    assert not Payment.objects.filter(reversal_of=payment).exists()

    _refund(account, "evt_s", "re_1", "pi_1", 4000, django_capture_on_commit_callbacks)
    assert Payment.objects.filter(reversal_of=payment).count() == 1


def test_a_refund_above_what_is_left_is_flagged_and_writes_nothing(
    fake_stripe, django_capture_on_commit_callbacks
):
    payment, checkout = paid_online(django_capture_on_commit_callbacks)
    account = checkout.stripe_account_id
    _refund(account, "evt_1", "re_1", "pi_1", 8000, django_capture_on_commit_callbacks)

    _refund(account, "evt_2", "re_2", "pi_1", 5000, django_capture_on_commit_callbacks)

    assert Payment.objects.filter(reversal_of=payment).count() == 1
    event = WebhookEvent.objects.get(stripe_event_id="evt_2")
    assert (event.outcome, event.attention_kind) == ("needs_attention", "refund_exceeds")


def test_a_refund_matching_no_payment_changes_nothing_and_is_flagged(
    fake_stripe, django_capture_on_commit_callbacks
):
    payment, checkout = paid_online(django_capture_on_commit_callbacks)
    cash = PaymentFactory(student=payment.student, method="cash")

    _refund(
        checkout.stripe_account_id,
        "evt_x",
        "re_x",
        "pi_nobody",
        1000,
        django_capture_on_commit_callbacks,
    )

    assert not Payment.objects.filter(status="reversal").exists()
    event = WebhookEvent.objects.get(stripe_event_id="evt_x")
    assert (event.outcome, event.attention_kind) == ("needs_attention", "refund_unmatched")
    assert cash.reversals.count() == 0


def test_a_failed_refund_is_ignored(fake_stripe, django_capture_on_commit_callbacks):
    payment, checkout = paid_online(django_capture_on_commit_callbacks)

    _refund(
        checkout.stripe_account_id, "evt_f", "re_f", "pi_1", 4000,
        django_capture_on_commit_callbacks, status="failed",
    )  # fmt: skip

    assert not Payment.objects.filter(reversal_of=payment).exists()


def test_a_manual_reversal_is_refused_after_a_refund(
    fake_stripe, django_capture_on_commit_callbacks
):
    payment, checkout = paid_online(django_capture_on_commit_callbacks)
    _refund(
        checkout.stripe_account_id,
        "evt_1",
        "re_1",
        "pi_1",
        1000,
        django_capture_on_commit_callbacks,
    )

    res = client_for(payment.student.teacher.user).post(
        f"/api/v1/payments/{payment.pk}/reverse/", {"reason": "oops"}, format="json"
    )

    assert res.status_code == 409 and res.data["code"] == "already_reversed"


def test_the_payment_api_shows_the_reversed_amount_and_the_cause(
    fake_stripe, django_capture_on_commit_callbacks
):
    payment, checkout = paid_online(django_capture_on_commit_callbacks)
    _refund(
        checkout.stripe_account_id,
        "evt_1",
        "re_1",
        "pi_1",
        3000,
        django_capture_on_commit_callbacks,
    )
    client = client_for(payment.student.teacher.user)

    rows = {r["id"]: r for r in client.get("/api/v1/payments/").data["results"]}

    assert rows[payment.pk]["reversed_amount"] == "30.00" and rows[payment.pk]["reversed"] is False
    reversal = Payment.objects.get(reversal_of=payment)
    assert rows[reversal.pk]["cause"] == "refund" and rows[reversal.pk]["status"] == "reversal"


def test_the_refund_is_audited_without_an_actor(fake_stripe, django_capture_on_commit_callbacks):
    payment, checkout = paid_online(django_capture_on_commit_callbacks)

    _refund(
        checkout.stripe_account_id,
        "evt_1",
        "re_1",
        "pi_1",
        3000,
        django_capture_on_commit_callbacks,
    )

    entry = AuditEntry.objects.get(action="payment.refund")
    assert entry.actor_id is None and entry.studio_id == payment.student.studio_id
    assert entry.metadata == {"cause": "refund", "amount": "30.00", "ref": "re_1"}
