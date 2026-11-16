"""Pagamento online sul conto dello studio: una volta sola, anomalie segnalate (US2, fase 9)."""

import datetime
import json
import threading

import pytest
from django.db import connection
from django.utils import timezone
from rest_framework.test import APIClient

from apps.common.factories import StudioPaymentAccountFactory, connected_package
from apps.common.tests.helpers import client_for
from apps.packages.models import Package
from apps.payments import selectors, services
from apps.payments.gateway import SessionInfo
from apps.payments.models import CheckoutSession, Payment, WebhookEvent
from apps.payments.tasks import reconcile_open_checkouts

from .fakes import CONNECT_WEBHOOK_SECRET, session_payload, signed_event

pytestmark = pytest.mark.django_db
CONNECT_URL = "/api/v1/webhooks/stripe-connect/"


def _open(package: Package) -> CheckoutSession:
    return services.start_checkout(package, user=package.student.teacher.user)


def _send(checkout: CheckoutSession, event_id: str, kind: str, capture, *, account=None, **session):
    payload = session_payload(checkout.stripe_session_id, **session)
    body, sig = signed_event(
        event_id,
        kind,
        payload,
        secret=CONNECT_WEBHOOK_SECRET,
        account=account or checkout.stripe_account_id,
    )
    with capture(execute=True):
        return APIClient().post(
            CONNECT_URL, data=body, content_type="application/json", HTTP_STRIPE_SIGNATURE=sig
        )


def test_the_session_is_created_on_the_studios_account_with_no_fee(fake_stripe):
    package = connected_package(price="120.00")

    checkout = _open(package)

    call = fake_stripe.created[0]
    assert call["stripe_account"] == checkout.stripe_account_id
    assert call["stripe_account"] == package.student.studio.payment_account.stripe_account_id
    assert not {"application_fee_amount", "on_behalf_of", "transfer_data"} & set(call)
    assert call["amount_cents"] == 12000 and call["currency"] == "eur"


def test_a_confirmed_payment_is_recorded_once_with_its_payment_intent(
    fake_stripe, django_capture_on_commit_callbacks
):
    package = connected_package(price="120.00")
    checkout = _open(package)

    res = _send(checkout, "evt_1", "checkout.session.completed", django_capture_on_commit_callbacks)

    assert res.status_code == 200
    payment = Payment.objects.get()
    assert (payment.method, payment.status, payment.amount, payment.checkout_id) == (
        "card",
        "paid",
        120,
        checkout.id,
    )
    checkout.refresh_from_db()
    assert checkout.stripe_payment_intent_id == "pi_test_1"
    assert WebhookEvent.objects.get().outcome == WebhookEvent.Outcome.APPLIED
    assert services.package_is_paid(package)


def test_the_same_confirmation_replayed_three_times_records_one_payment(
    fake_stripe, django_capture_on_commit_callbacks
):
    checkout = _open(connected_package())

    for _ in range(3):
        _send(checkout, "evt_dup", "checkout.session.completed", django_capture_on_commit_callbacks)

    assert Payment.objects.count() == 1 and WebhookEvent.objects.count() == 1


def test_two_different_events_for_the_same_session_still_make_one_payment(
    fake_stripe, django_capture_on_commit_callbacks
):
    checkout = _open(connected_package())

    for event_id, kind in [("evt_a", "completed"), ("evt_b", "async_payment_succeeded")]:
        _send(checkout, event_id, f"checkout.session.{kind}", django_capture_on_commit_callbacks)

    assert Payment.objects.count() == 1


@pytest.mark.parametrize(
    ("kind", "session", "expected"),
    [
        ("checkout.session.async_payment_failed", {"payment_status": "unpaid"}, "failed"),
        (
            "checkout.session.expired",
            {"status": "expired", "payment_status": "unpaid"},
            "expired",
        ),
    ],
)
def test_a_failed_or_expired_attempt_leaves_the_package_open_and_payable_again(
    fake_stripe, django_capture_on_commit_callbacks, kind, session, expected
):
    package = connected_package()
    checkout = _open(package)

    _send(checkout, "evt_x", kind, django_capture_on_commit_callbacks, **session)

    checkout.refresh_from_db()
    assert checkout.status == expected and not Payment.objects.exists()
    assert not services.package_is_paid(package)
    assert _open(package).pk != checkout.pk  # un nuovo tentativo si può aprire


def test_a_different_amount_is_recorded_as_paid_and_flagged_for_the_studio(
    fake_stripe, django_capture_on_commit_callbacks
):
    package = connected_package(price="120.00")
    checkout = _open(package)

    _send(
        checkout,
        "evt_amt",
        "checkout.session.completed",
        django_capture_on_commit_callbacks,
        amount=9900,
    )

    assert str(Payment.objects.get().amount) == "99.00"
    event = WebhookEvent.objects.get()
    assert (event.outcome, event.attention_kind) == (
        WebhookEvent.Outcome.NEEDS_ATTENTION,
        "amount_differs",
    )
    items = selectors.attention_items(package.student.studio.payment_account)
    assert items[0]["kind"] == "amount_differs" and str(items[0]["amount"]) == "99.00"


def test_a_second_payment_for_an_already_paid_package_is_kept_but_flagged(
    fake_stripe, django_capture_on_commit_callbacks
):
    package = connected_package()
    checkout = _open(package)
    Payment.objects.create(
        student=package.student, package=package, amount="120.00", date="2026-11-16",
        method="cash", status="paid",
    )  # fmt: skip

    _send(checkout, "evt_dp", "checkout.session.completed", django_capture_on_commit_callbacks)

    # I soldi sono stati presi davvero: la riga c'è, ma mai contata di nascosto (si segnala).
    assert Payment.objects.filter(method="card").count() == 1
    event = WebhookEvent.objects.get()
    assert (event.outcome, event.attention_kind) == (
        WebhookEvent.Outcome.NEEDS_ATTENTION,
        "duplicate_payment",
    )


def test_money_in_another_currency_is_never_recorded_as_euro(
    fake_stripe, django_capture_on_commit_callbacks
):
    checkout = _open(connected_package())

    _send(
        checkout,
        "evt_cur",
        "checkout.session.completed",
        django_capture_on_commit_callbacks,
        currency="usd",
    )

    assert not Payment.objects.exists()
    checkout.refresh_from_db()
    assert checkout.status == CheckoutSession.Status.FAILED
    assert WebhookEvent.objects.get().attention_kind == "currency_differs"


def test_an_event_from_another_studios_account_never_settles_this_attempt(
    fake_stripe, django_capture_on_commit_callbacks
):
    checkout = _open(connected_package())
    other = StudioPaymentAccountFactory()

    _send(
        checkout, "evt_wrong", "checkout.session.completed", django_capture_on_commit_callbacks,
        account=other.stripe_account_id,
    )  # fmt: skip

    assert not Payment.objects.exists()
    checkout.refresh_from_db()
    assert checkout.status == CheckoutSession.Status.OPEN
    assert WebhookEvent.objects.get().outcome == WebhookEvent.Outcome.IGNORED


def test_an_event_without_account_cannot_settle_an_attempt_that_has_one(
    fake_stripe, django_capture_on_commit_callbacks
):
    checkout = _open(connected_package())
    body, sig = signed_event(
        "evt_plat", "checkout.session.completed", session_payload(checkout.stripe_session_id)
    )
    with django_capture_on_commit_callbacks(execute=True):
        APIClient().post(
            "/api/v1/webhooks/stripe/", data=body, content_type="application/json",
            HTTP_STRIPE_SIGNATURE=sig,
        )  # fmt: skip

    assert not Payment.objects.exists()


def test_an_attempt_of_another_account_is_not_reused(fake_stripe):
    package = connected_package()
    first = _open(package)
    # Lo studio ha cambiato conto: un tentativo ancora aperto sul vecchio non si riusa.
    first_account = package.student.studio.payment_account
    first_account.stripe_account_id = "acct_new"
    first_account.save()

    second = _open(package)

    assert second.pk != first.pk and second.stripe_account_id == "acct_new"
    assert len(fake_stripe.created) == 2


@pytest.mark.django_db(transaction=True)
def test_two_simultaneous_starts_open_one_session(fake_stripe):
    package = connected_package()
    user = package.student.teacher.user
    barrier = threading.Barrier(2)
    ids: list[str] = []
    lock = threading.Lock()

    def start() -> None:
        try:
            client = client_for(user)
            barrier.wait(timeout=5)
            res = client.post(f"/api/v1/packages/{package.pk}/checkout/")
            outcome = str(res.data.get("checkout_id", res.status_code))
        except Exception as exc:
            outcome = f"error: {exc!r}"
        finally:
            connection.close()
        with lock:
            ids.append(outcome)

    threads = [threading.Thread(target=start) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)

    assert len(set(ids)) == 1 and not ids[0].startswith("error"), ids
    assert len(fake_stripe.created) == 1


def test_reconciliation_reads_each_attempt_with_its_own_account(fake_stripe):
    package = connected_package()
    checkout = _open(package)
    CheckoutSession.objects.update(expires_at=timezone.now() - datetime.timedelta(minutes=5))
    fake_stripe.sessions[checkout.stripe_session_id] = SessionInfo(
        id=checkout.stripe_session_id, status="complete", payment_status="paid",
        amount_total=12000, currency="eur", payment_intent="pi_9",
    )  # fmt: skip

    assert reconcile_open_checkouts() == 1

    assert fake_stripe.retrieved == [(checkout.stripe_session_id, checkout.stripe_account_id)]
    assert Payment.objects.get().checkout_id == checkout.id
    checkout.refresh_from_db()
    assert checkout.stripe_payment_intent_id == "pi_9"


def test_the_connect_event_payload_is_stored_scrubbed(
    fake_stripe, django_capture_on_commit_callbacks
):
    checkout = _open(connected_package())

    _send(checkout, "evt_s", "checkout.session.completed", django_capture_on_commit_callbacks)

    stored = json.dumps(WebhookEvent.objects.get().payload)
    assert "customer" not in stored and checkout.stripe_session_id in stored
