"""Lo stato del conto dello studio si ricava da ciò che Stripe riferisce (fase 9, ADR-037)."""

import pytest

from apps.payments.gateway import AccountInfo
from apps.payments.models import StudioPaymentAccount
from apps.payments.services import state_from_account

S = StudioPaymentAccount.State


@pytest.mark.parametrize(
    ("capability", "open_requirements", "closed", "expected"),
    [
        ("active", 0, False, S.ACTIVE),
        ("active", 3, False, S.ACTIVE),  # attivo vale anche con requisiti futuri aperti
        ("restricted", 19, False, S.INFORMATION_NEEDED),  # un conto appena creato
        ("restricted", 2, False, S.INFORMATION_NEEDED),
        ("restricted", 0, False, S.RESTRICTED),  # bloccato da Stripe, nulla da fornire
        ("pending", 0, False, S.IN_PROGRESS),  # in revisione
        ("pending", 4, False, S.IN_PROGRESS),
        ("", 0, False, S.IN_PROGRESS),  # Stripe non riporta nulla: mai "attivo" per ottimismo
        ("", 5, False, S.INFORMATION_NEEDED),
        ("active", 0, True, S.DISCONNECTED),  # chiuso vince su tutto
        ("restricted", 9, True, S.DISCONNECTED),
    ],
)
def test_state_table(capability, open_requirements, closed, expected):
    info = AccountInfo(
        id="acct_1", card_payments=capability, open_requirements=open_requirements, closed=closed
    )

    assert state_from_account(info) == expected


def test_only_an_active_capability_ever_means_can_accept_online():
    for capability in ["restricted", "pending", "", "inactive", "unsupported"]:
        info = AccountInfo(id="a", card_payments=capability)
        assert state_from_account(info) != S.ACTIVE
