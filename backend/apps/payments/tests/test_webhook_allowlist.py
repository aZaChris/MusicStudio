"""Webhook source allowlist behind the proxy (US6, ADR-021)."""

import pytest
from rest_framework.test import APIClient

from apps.payments.models import WebhookEvent
from apps.payments.webhooks import is_allowed_source

from .fakes import signed_event

pytestmark = pytest.mark.django_db
URL = "/api/v1/webhooks/stripe/"
STRIPE_IP = "3.18.12.63"


@pytest.fixture
def behind_proxy(settings, fake_stripe):
    settings.TRUSTED_PROXY_COUNT = 1
    settings.STRIPE_WEBHOOK_ALLOWED_IPS = [STRIPE_IP, "54.187.216.72"]


def _post(xff: str, signature: bool = True):
    body, sig = signed_event("evt_allow", "customer.created", {"id": "cus_1"})
    headers = {"HTTP_X_FORWARDED_FOR": xff}
    if signature:
        headers["HTTP_STRIPE_SIGNATURE"] = sig
    return APIClient().post(URL, data=body, content_type="application/json", **headers)


def test_allowed_address_is_processed(behind_proxy):
    assert _post(STRIPE_IP).status_code == 200
    assert WebhookEvent.objects.count() == 1


def test_other_address_is_refused_and_nothing_stored(behind_proxy, caplog):
    res = _post("6.6.6.6")

    assert res.status_code == 403
    assert not WebhookEvent.objects.exists()
    assert "6.6.6.6" in caplog.text


def test_forged_left_most_forwarded_for_is_refused(behind_proxy):
    # Attacker sends "X-Forwarded-For: <stripe ip>"; Traefik appends the real address.
    assert _post(f"{STRIPE_IP}, 6.6.6.6").status_code == 403
    assert not WebhookEvent.objects.exists()


def test_allowed_address_still_needs_a_valid_signature(behind_proxy):
    assert _post(STRIPE_IP, signature=False).status_code == 400


def test_empty_allowlist_disables_the_check_not_the_signature(settings, fake_stripe):
    settings.STRIPE_WEBHOOK_ALLOWED_IPS = []
    assert _post("6.6.6.6").status_code == 200
    assert _post("6.6.6.6", signature=False).status_code == 400


def test_cidr_ranges_and_garbage(settings):
    settings.STRIPE_WEBHOOK_ALLOWED_IPS = ["10.1.0.0/16"]
    assert is_allowed_source("10.1.2.3")
    assert not is_allowed_source("10.2.0.1")
    assert not is_allowed_source("not-an-ip")
    assert not is_allowed_source("")
