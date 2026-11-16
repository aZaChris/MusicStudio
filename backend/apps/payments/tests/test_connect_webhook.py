"""Endpoint dei webhook dei conti collegati (fase 9, ADR-039)."""

import pytest
from rest_framework.test import APIClient

from apps.common.factories import StudioPaymentAccountFactory
from apps.payments.models import WebhookEvent

from .fakes import CONNECT_WEBHOOK_SECRET, WEBHOOK_SECRET, signed_event

pytestmark = pytest.mark.django_db
URL = "/api/v1/webhooks/stripe-connect/"
PLATFORM_URL = "/api/v1/webhooks/stripe/"
STRIPE_IP = "3.18.12.63"


def _post(body: bytes, sig: str | None, capture, url: str = URL, **extra):
    headers = {"HTTP_STRIPE_SIGNATURE": sig} if sig else {}
    with capture(execute=True):
        return APIClient().post(url, data=body, content_type="application/json", **headers, **extra)


def _event(event_id="evt_c1", account="acct_test_1", **kw):
    return signed_event(
        event_id,
        "customer.created",
        {"id": "cus_1"},
        secret=kw.pop("secret", CONNECT_WEBHOOK_SECRET),
        account=account,
        **kw,
    )


def test_a_valid_event_of_a_known_account_is_stored_and_processed(
    fake_stripe, django_capture_on_commit_callbacks
):
    StudioPaymentAccountFactory(stripe_account_id="acct_test_1")
    body, sig = _event()

    res = _post(body, sig, django_capture_on_commit_callbacks)

    assert res.status_code == 200
    stored = WebhookEvent.objects.get()
    assert stored.stripe_account_id == "acct_test_1"
    assert stored.processed_at is not None
    assert stored.outcome == WebhookEvent.Outcome.IGNORED  # nessun gestore per questo tipo


def test_a_bad_or_missing_signature_is_refused_and_nothing_is_stored(
    fake_stripe, django_capture_on_commit_callbacks
):
    body, _ = _event()

    assert _post(body, "t=1,v1=bad", django_capture_on_commit_callbacks).status_code == 400
    assert _post(body, None, django_capture_on_commit_callbacks).status_code == 400
    assert not WebhookEvent.objects.exists()


def test_the_two_endpoints_do_not_accept_each_others_secret(
    fake_stripe, django_capture_on_commit_callbacks
):
    platform_body, platform_sig = signed_event("evt_p", "customer.created", {"id": "c"})
    connect_body, connect_sig = _event("evt_k", secret=CONNECT_WEBHOOK_SECRET)

    assert (
        _post(platform_body, platform_sig, django_capture_on_commit_callbacks, URL).status_code
        == 400
    )
    assert (
        _post(
            connect_body, connect_sig, django_capture_on_commit_callbacks, PLATFORM_URL
        ).status_code
        == 400
    )
    # ...e ognuno accetta il proprio.
    assert (
        _post(
            platform_body, platform_sig, django_capture_on_commit_callbacks, PLATFORM_URL
        ).status_code
        == 200
    )
    assert WEBHOOK_SECRET != CONNECT_WEBHOOK_SECRET


def test_without_a_configured_secret_the_endpoint_answers_400(
    fake_stripe, settings, django_capture_on_commit_callbacks
):
    settings.STRIPE_CONNECT_WEBHOOK_SECRET = ""
    body, sig = _event()

    assert _post(body, sig, django_capture_on_commit_callbacks).status_code == 400


def test_a_duplicate_delivery_is_processed_once(fake_stripe, django_capture_on_commit_callbacks):
    StudioPaymentAccountFactory(stripe_account_id="acct_test_1")
    body, sig = _event("evt_dup")

    statuses = [_post(body, sig, django_capture_on_commit_callbacks).status_code for _ in range(3)]

    assert statuses == [200, 200, 200]
    stored = WebhookEvent.objects.get()
    assert stored.attempts == 1


def test_an_event_of_an_unknown_account_is_kept_and_ignored(
    fake_stripe, django_capture_on_commit_callbacks
):
    body, sig = _event(account="acct_nobody")

    assert _post(body, sig, django_capture_on_commit_callbacks).status_code == 200

    stored = WebhookEvent.objects.get()
    assert stored.outcome == WebhookEvent.Outcome.IGNORED and stored.processed_at is not None


def test_a_live_mode_event_is_kept_and_ignored(fake_stripe, django_capture_on_commit_callbacks):
    StudioPaymentAccountFactory(stripe_account_id="acct_test_1")
    body, sig = _event("evt_live", livemode=True)

    assert _post(body, sig, django_capture_on_commit_callbacks).status_code == 200

    stored = WebhookEvent.objects.get()
    assert stored.livemode is True and stored.outcome == WebhookEvent.Outcome.IGNORED


def test_the_source_address_allowlist_applies_to_this_endpoint_too(
    fake_stripe, settings, django_capture_on_commit_callbacks
):
    settings.TRUSTED_PROXY_COUNT = 1
    settings.STRIPE_WEBHOOK_ALLOWED_IPS = [STRIPE_IP]
    body, sig = _event()

    refused = _post(body, sig, django_capture_on_commit_callbacks, HTTP_X_FORWARDED_FOR="6.6.6.6")
    allowed = _post(body, sig, django_capture_on_commit_callbacks, HTTP_X_FORWARDED_FOR=STRIPE_IP)

    assert (refused.status_code, allowed.status_code) == (403, 200)
