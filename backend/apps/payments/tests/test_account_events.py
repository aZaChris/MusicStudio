"""Lo stato del conto resta aggiornato anche senza eventi v2 (fase 9, research "Spike results")."""

import logging

import pytest
from rest_framework.test import APIClient

from apps.audit.models import AuditEntry
from apps.common.factories import StudioPaymentAccountFactory
from apps.common.tests.helpers import client_for, make_studio_owner
from apps.payments import services, tasks
from apps.payments.models import StudioPaymentAccount, WebhookEvent

from .fakes import CONNECT_WEBHOOK_SECRET, signed_event

pytestmark = pytest.mark.django_db
URL = "/api/v1/webhooks/stripe-connect/"


def _deauthorize(account_id: str, event_id: str = "evt_d1"):
    return signed_event(
        event_id,
        "account.application.deauthorized",
        {"id": "ca_1", "object": "application"},
        secret=CONNECT_WEBHOOK_SECRET,
        account=account_id,
    )


def _post(body: bytes, sig: str, capture) -> int:
    with capture(execute=True):
        return (
            APIClient()
            .post(URL, data=body, content_type="application/json", HTTP_STRIPE_SIGNATURE=sig)
            .status_code
        )


def test_a_deauthorized_event_disconnects_the_account_and_stops_online_payments(
    fake_stripe, django_capture_on_commit_callbacks
):
    account = StudioPaymentAccountFactory(state="active")
    body, sig = _deauthorize(account.stripe_account_id)

    assert _post(body, sig, django_capture_on_commit_callbacks) == 200

    account.refresh_from_db()
    assert account.state == "disconnected" and not account.can_accept_online
    assert WebhookEvent.objects.get().outcome == WebhookEvent.Outcome.APPLIED
    entry = AuditEntry.objects.get(action="payment_account.state")
    assert entry.actor_id is None and entry.metadata == {"from": "active", "to": "disconnected"}


def test_a_replayed_deauthorized_event_changes_nothing(
    fake_stripe, django_capture_on_commit_callbacks
):
    account = StudioPaymentAccountFactory(state="active")
    body, sig = _deauthorize(account.stripe_account_id)

    for _ in range(3):
        _post(body, sig, django_capture_on_commit_callbacks)

    assert AuditEntry.objects.filter(action="payment_account.state").count() == 1


def test_an_event_for_one_studio_never_touches_another(
    fake_stripe, django_capture_on_commit_callbacks
):
    mine = StudioPaymentAccountFactory(state="active")
    other = StudioPaymentAccountFactory(state="active")
    body, sig = _deauthorize(mine.stripe_account_id)

    _post(body, sig, django_capture_on_commit_callbacks)

    other.refresh_from_db()
    assert other.state == "active"


def test_the_hourly_refresh_updates_changed_accounts_and_skips_disconnected_ones(fake_stripe):
    changed = StudioPaymentAccountFactory(state="information_needed")
    same = StudioPaymentAccountFactory(state="active")
    dead = StudioPaymentAccountFactory(state="disconnected")
    for account in (changed, same, dead):
        fake_stripe.accounts[account.stripe_account_id] = services.gateway.AccountInfo(
            id=account.stripe_account_id, card_payments="active"
        )

    assert tasks.refresh_payment_accounts() == 1

    changed.refresh_from_db(), same.refresh_from_db(), dead.refresh_from_db()
    assert (changed.state, same.state, dead.state) == ("active", "active", "disconnected")


def test_an_active_account_that_stripe_restricts_stops_being_payable(fake_stripe):
    account = StudioPaymentAccountFactory(state="active")
    fake_stripe.set_account(account.stripe_account_id, card_payments="restricted")

    tasks.refresh_payment_accounts()

    account.refresh_from_db()
    assert account.state == "restricted" and not account.can_accept_online


def test_one_unreachable_account_does_not_stop_the_others(fake_stripe, monkeypatch):
    broken = StudioPaymentAccountFactory(state="information_needed")
    fine = StudioPaymentAccountFactory(state="information_needed")
    fake_stripe.set_account(fine.stripe_account_id, card_payments="active")
    real = fake_stripe.retrieve_account

    def retrieve(account_id: str):
        if account_id == broken.stripe_account_id:
            raise services.gateway.PaymentsUnavailable("down")
        return real(account_id)

    monkeypatch.setattr(services.gateway, "retrieve_account", retrieve)

    assert services.refresh_accounts() == 1

    fine.refresh_from_db(), broken.refresh_from_db()
    assert (fine.state, broken.state) == ("active", "information_needed")


def test_the_hourly_refresh_does_nothing_with_the_switch_off(fake_stripe, settings):
    settings.ONLINE_PAYMENTS_ENABLED = False
    StudioPaymentAccountFactory(state="information_needed")

    assert tasks.refresh_payment_accounts() == 0
    assert fake_stripe.retrieved == []


def test_the_account_flow_logs_no_names_or_emails(fake_stripe, caplog):
    owner = make_studio_owner()
    caplog.set_level(logging.DEBUG)

    client = client_for(owner.user)
    client.post("/api/v1/payment-account/onboarding/")
    fake_stripe.set_account(
        StudioPaymentAccount.objects.get().stripe_account_id, card_payments="active"
    )
    client.post("/api/v1/payment-account/refresh/")
    fake_stripe.fail_account = True
    client.post("/api/v1/payment-account/refresh/")

    assert owner.user.email not in caplog.text
    assert owner.studio.name not in caplog.text
