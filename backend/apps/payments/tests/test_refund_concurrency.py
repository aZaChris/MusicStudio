"""Un rimborso di Stripe e uno storno a mano insieme: ne vince uno solo (US3, fase 9)."""

import threading
from decimal import Decimal

import pytest
from django.db import connection

from apps.common.factories import PaymentFactory
from apps.payments.models import Payment
from apps.payments.services import (
    AlreadyReversed,
    ProviderReversalResult,
    add_provider_reversal,
    reverse_payment,
)

pytestmark = pytest.mark.django_db(transaction=True)


def test_a_manual_reversal_racing_a_provider_refund_has_exactly_one_winner():
    payment = PaymentFactory(amount="100.00")
    actor = payment.student.teacher.user
    barrier = threading.Barrier(2)
    outcomes: list[str] = []
    lock = threading.Lock()

    def manual() -> None:
        try:
            original = Payment.objects.get(pk=payment.pk)
            barrier.wait(timeout=5)
            reverse_payment(original, reason="race", actor=actor)
            result = "manual"
        except AlreadyReversed:
            result = "manual-refused"
        except Exception as exc:
            result = f"error: {exc!r}"
        finally:
            connection.close()
        with lock:
            outcomes.append(result)

    def provider() -> None:
        try:
            original = Payment.objects.get(pk=payment.pk)
            barrier.wait(timeout=5)
            _, res = add_provider_reversal(
                original, amount=Decimal("40.00"), cause="refund", provider_ref="re_race"
            )
            result = f"provider-{res}"
        except Exception as exc:
            result = f"error: {exc!r}"
        finally:
            connection.close()
        with lock:
            outcomes.append(result)

    threads = [threading.Thread(target=manual), threading.Thread(target=provider)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)

    assert not [o for o in outcomes if o.startswith("error")], outcomes
    rows = Payment.objects.filter(reversal_of=payment)
    total = sum(row.amount for row in rows)
    # O vince lo storno manuale (100, il rimborso eccede) o il rimborso (40, quello manuale è
    # rifiutato): mai tutti e due, e mai più dell'importo.
    assert total in (Decimal("100.00"), Decimal("40.00")), outcomes
    assert total <= Decimal(str(payment.amount))
    if total == Decimal("100.00"):
        assert f"provider-{ProviderReversalResult.EXCEEDS}" in outcomes
    else:
        assert "manual-refused" in outcomes
