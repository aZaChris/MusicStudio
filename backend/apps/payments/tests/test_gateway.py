"""Il gateway parla con Stripe come previsto da ADR-037 (fase 9): conto dello studio, nessuna fee.

Il client dell'SDK è sostituito da un registratore: nessuna rete. Si controlla cosa MusicStudio
manda davvero: l'intestazione del conto collegato, i parametri v2 e l'assenza di commissioni.
"""

import datetime
import json
from types import SimpleNamespace
from typing import Any

import pytest
import stripe

from apps.payments import gateway

SESSION = {"id": "cs_test_1", "status": "open", "payment_status": "unpaid", "url": "https://x"}
ACCOUNT = {
    "id": "acct_1",
    "closed": False,
    "configuration": {"merchant": {"capabilities": {"card_payments": {"status": "active"}}}},
    "requirements": {"entries": []},
}


class Recorder:
    """Un finto StripeClient: registra ogni chiamata e risponde con dati preparati."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
        self.error: Exception | None = None

    def _call(self, name: str, response: dict[str, Any]):
        def call(*args: Any, **kwargs: Any) -> Any:
            self.calls.append((name, args, kwargs))
            if self.error:
                raise self.error
            return json.dumps(response)  # `_as_dict` accetta anche una stringa JSON via str()

        return call

    def client(self) -> SimpleNamespace:
        sessions = SimpleNamespace(
            create=self._call("session.create", SESSION),
            retrieve=self._call("session.retrieve", SESSION),
        )
        return SimpleNamespace(
            v1=SimpleNamespace(checkout=SimpleNamespace(sessions=sessions)),
            v2=SimpleNamespace(
                core=SimpleNamespace(
                    accounts=SimpleNamespace(
                        create=self._call("account.create", ACCOUNT),
                        retrieve=self._call("account.retrieve", ACCOUNT),
                    ),
                    account_links=SimpleNamespace(
                        create=self._call(
                            "link.create",
                            {
                                "url": "https://connect.stripe.com/setup/s/x",
                                "expires_at": "2026-11-16T14:00:00.000Z",
                            },
                        )
                    ),
                )
            ),
        )


@pytest.fixture
def rec(monkeypatch) -> Recorder:
    recorder = Recorder()
    monkeypatch.setattr(gateway, "_client", recorder.client)
    # `_as_dict` fa json.loads(str(obj)): le risposte del registratore sono già stringhe JSON.
    return recorder


def _create(**overrides: Any) -> dict[str, Any]:
    args = {
        "checkout_id": "c1",
        "amount_cents": 12000,
        "currency": "eur",
        "description": "10 lessons",
        "expires_at": datetime.datetime(2026, 11, 20, tzinfo=datetime.UTC),
        "idempotency_key": "checkout-c1",
    }
    return {**args, **overrides}


def test_checkout_on_the_studio_account_sends_the_account_and_no_fee(rec):
    gateway.create_checkout_session(**_create(stripe_account="acct_1"))

    _, _, kwargs = rec.calls[0]
    assert kwargs["options"] == {"idempotency_key": "checkout-c1", "stripe_account": "acct_1"}
    params = kwargs["params"]
    assert "payment_intent_data" not in params  # niente application_fee_amount
    assert "on_behalf_of" not in json.dumps(params) and "application_fee" not in json.dumps(params)
    assert "payment_method_types" not in params


def test_checkout_without_an_account_keeps_the_phase_3_options(rec):
    gateway.create_checkout_session(**_create())

    assert rec.calls[0][2]["options"] == {"idempotency_key": "checkout-c1"}


def test_a_session_is_read_back_with_its_account(rec):
    gateway.retrieve_checkout_session("cs_test_1", "acct_1")
    gateway.retrieve_checkout_session("cs_test_1")

    assert rec.calls[0][2]["options"] == {"stripe_account": "acct_1"}
    assert rec.calls[1][2]["options"] == {}


def test_the_account_is_created_with_the_full_dashboard_and_no_personal_data(rec):
    info = gateway.create_account(studio_id=7, idempotency_key="account-studio-7")

    _, _, kwargs = rec.calls[0]
    params = kwargs["params"]
    assert params["dashboard"] == "full"
    assert params["defaults"]["responsibilities"] == {
        "fees_collector": "stripe",
        "losses_collector": "stripe",
    }
    assert params["configuration"]["merchant"]["capabilities"]["card_payments"] == {
        "requested": True
    }
    assert params["metadata"] == {"studio_id": "7"}  # solo l'id dello studio
    text = json.dumps(params)
    assert "email" not in text and "name" not in text and "phone" not in text
    assert kwargs["options"] == {"idempotency_key": "account-studio-7"}
    assert (info.id, info.card_payments, info.open_requirements) == ("acct_1", "active", 0)


def test_the_onboarding_link_sends_only_the_two_return_addresses(rec):
    link = gateway.create_account_link(
        account_id="acct_1", return_url="https://app/return", refresh_url="https://app/refresh"
    )

    params = rec.calls[0][2]["params"]
    assert params["account"] == "acct_1"
    assert params["use_case"] == {
        "type": "account_onboarding",
        "account_onboarding": {
            "return_url": "https://app/return",
            "refresh_url": "https://app/refresh",
        },
    }
    assert link.url.startswith("https://connect.stripe.com/")
    assert link.expires_at == datetime.datetime(2026, 11, 16, 14, 0, tzinfo=datetime.UTC)


def test_the_account_is_read_with_its_requirements_and_merchant_configuration(rec):
    gateway.retrieve_account("acct_1")

    assert rec.calls[0][1] == ("acct_1",)
    assert rec.calls[0][2]["params"] == {"include": ["requirements", "configuration.merchant"]}


def test_account_info_counts_open_requirements_and_reads_the_capability():
    info = gateway.AccountInfo.from_dict(
        {
            "id": "acct_9",
            "closed": True,
            "configuration": {
                "merchant": {"capabilities": {"card_payments": {"status": "restricted"}}}
            },
            "requirements": {"entries": [{"description": "a"}, {"description": "b"}]},
        }
    )

    assert (info.card_payments, info.open_requirements, info.closed) == ("restricted", 2, True)
    assert gateway.AccountInfo.from_dict({"id": "acct_8"}).card_payments == ""


@pytest.mark.parametrize(
    "call",
    [
        lambda: gateway.create_checkout_session(**_create(stripe_account="acct_1")),
        lambda: gateway.retrieve_checkout_session("cs_test_1", "acct_1"),
        lambda: gateway.create_account(studio_id=1, idempotency_key="k"),
        lambda: gateway.create_account_link(account_id="a", return_url="u", refresh_url="r"),
        lambda: gateway.retrieve_account("acct_1"),
    ],
)
def test_a_stripe_error_becomes_payments_unavailable(rec, call):
    rec.error = stripe.APIConnectionError("boom")

    with pytest.raises(gateway.PaymentsUnavailable):
        call()


def test_each_endpoint_verifies_with_its_own_secret(settings):
    settings.STRIPE_WEBHOOK_SECRET = "whsec_platform"
    settings.STRIPE_CONNECT_WEBHOOK_SECRET = ""

    with pytest.raises(gateway.InvalidWebhook):
        gateway.verify_event(b"{}", "t=1,v1=x", settings.STRIPE_CONNECT_WEBHOOK_SECRET)
    with pytest.raises(gateway.InvalidWebhook):
        gateway.verify_event(b"{}", None)  # senza firma
