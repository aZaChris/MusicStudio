import pytest

from apps.payments import gateway

from .fakes import WEBHOOK_SECRET, FakeStripe


@pytest.fixture
def fake_stripe(monkeypatch, settings) -> FakeStripe:
    settings.STRIPE_API_KEY = "rk_test_fake"
    settings.STRIPE_WEBHOOK_SECRET = WEBHOOK_SECRET
    fake = FakeStripe()
    monkeypatch.setattr(gateway, "create_checkout_session", fake.create_checkout_session)
    monkeypatch.setattr(gateway, "retrieve_checkout_session", fake.retrieve_checkout_session)
    return fake
