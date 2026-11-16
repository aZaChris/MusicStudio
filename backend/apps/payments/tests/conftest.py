import pytest

from apps.payments import gateway

from .fakes import CONNECT_WEBHOOK_SECRET, WEBHOOK_SECRET, FakeStripe


@pytest.fixture
def fake_stripe(monkeypatch, settings) -> FakeStripe:
    settings.STRIPE_API_KEY = "rk_test_fake"
    settings.STRIPE_WEBHOOK_SECRET = WEBHOOK_SECRET
    settings.STRIPE_CONNECT_WEBHOOK_SECRET = CONNECT_WEBHOOK_SECRET
    fake = FakeStripe()
    monkeypatch.setattr(gateway, "create_checkout_session", fake.create_checkout_session)
    monkeypatch.setattr(gateway, "retrieve_checkout_session", fake.retrieve_checkout_session)
    monkeypatch.setattr(gateway, "create_account", fake.create_account)
    monkeypatch.setattr(gateway, "create_account_link", fake.create_account_link)
    monkeypatch.setattr(gateway, "retrieve_account", fake.retrieve_account)
    return fake
