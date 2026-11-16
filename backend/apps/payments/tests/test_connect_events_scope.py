"""Un evento del conto di uno studio non tocca mai un altro studio (US3, fase 9, FR-031, SC-006)."""

import pytest

from apps.common.factories import (
    PackageFactory,
    StudentFactory,
    StudioPaymentAccountFactory,
)
from apps.common.tests.helpers import client_for, make_studio_owner
from apps.payments.models import Payment, PaymentDispute

from .connect_helpers import dispute_obj, paid_online, refund_obj, send_event

pytestmark = pytest.mark.django_db


def _studio_with_account(intent: str, capture):
    owner = make_studio_owner()
    StudioPaymentAccountFactory(studio=owner.studio)
    package = PackageFactory(student=StudentFactory(teacher=owner), price="100.00")
    payment, checkout = paid_online(capture, package=package, intent=intent)
    return owner, payment, checkout


def test_a_refund_on_studio_as_account_never_touches_studio_bs_payment(
    fake_stripe, django_capture_on_commit_callbacks
):
    _, a_payment, a_checkout = _studio_with_account("pi_a", django_capture_on_commit_callbacks)
    _, b_payment, _ = _studio_with_account("pi_b", django_capture_on_commit_callbacks)

    # Un evento del conto di A che nomina il pagamento Stripe di B (id esistente, altro conto).
    send_event(
        "evt_x", "refund.updated", refund_obj("re_x", "pi_b", 10000),
        a_checkout.stripe_account_id, django_capture_on_commit_callbacks,
    )  # fmt: skip

    assert not Payment.objects.filter(reversal_of=b_payment).exists()
    assert not Payment.objects.filter(reversal_of=a_payment).exists()
    assert not PaymentDispute.objects.exists()


def test_a_dispute_on_one_account_with_another_accounts_intent_is_unmatched(
    fake_stripe, django_capture_on_commit_callbacks
):
    _, _, a_checkout = _studio_with_account("pi_a", django_capture_on_commit_callbacks)
    _, b_payment, _ = _studio_with_account("pi_b", django_capture_on_commit_callbacks)

    send_event(
        "evt_d", "charge.dispute.created", dispute_obj("dp_x", "pi_b", 10000),
        a_checkout.stripe_account_id, django_capture_on_commit_callbacks,
    )  # fmt: skip

    assert not PaymentDispute.objects.exists()
    assert not b_payment.disputes.exists()


def test_the_attention_list_of_one_studio_shows_none_of_anothers(
    fake_stripe, django_capture_on_commit_callbacks
):
    owner_a, _, a_checkout = _studio_with_account("pi_a", django_capture_on_commit_callbacks)
    owner_b, _, _ = _studio_with_account("pi_b", django_capture_on_commit_callbacks)
    send_event(
        "evt_a", "refund.updated", refund_obj("re_a", "pi_nobody", 1234),
        a_checkout.stripe_account_id, django_capture_on_commit_callbacks,
    )  # fmt: skip

    seen_a = client_for(owner_a.user).get("/api/v1/payment-account/").data["needs_attention"]
    seen_b = client_for(owner_b.user).get("/api/v1/payment-account/").data["needs_attention"]

    assert [i["kind"] for i in seen_a] == ["refund_unmatched"] and seen_a[0]["amount"] == "12.34"
    assert seen_b == []


def test_an_event_of_an_unconnected_account_is_ignored_even_with_a_known_payment_intent(
    fake_stripe, django_capture_on_commit_callbacks
):
    _, payment, _ = _studio_with_account("pi_a", django_capture_on_commit_callbacks)

    send_event(
        "evt_u", "refund.updated", refund_obj("re_u", "pi_a", 10000),
        "acct_not_connected_to_anyone", django_capture_on_commit_callbacks,
    )  # fmt: skip

    assert not Payment.objects.filter(reversal_of=payment).exists()
