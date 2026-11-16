"""Rimborsi e contestazioni sul registro: la somma degli storni non supera mai l'importo.

Fase 9, ADR-038. La regola non è un vincolo del database: la tiene il service sotto il lock di
riga dell'originale, qui provata anche con thread veri.
"""

import datetime
import threading
from decimal import Decimal

import pytest
from django.db import connection
from django.db.models import Sum
from django.utils import timezone

from apps.audit.models import AuditEntry
from apps.common.factories import PaymentFactory, make_reversal
from apps.payments.models import Payment
from apps.payments.services import (
    AlreadyReversed,
    ProviderReversalResult,
    add_provider_reversal,
    reverse_payment,
)

pytestmark = pytest.mark.django_db


def _add(payment: Payment, amount: str, ref: str, cause: str = Payment.Cause.REFUND):
    return add_provider_reversal(
        Payment.objects.get(pk=payment.pk), amount=Decimal(amount), cause=cause, provider_ref=ref
    )


def _reversed_total(payment: Payment) -> Decimal:
    total = Payment.objects.filter(reversal_of=payment).aggregate(total=Sum("amount"))["total"]
    return total or Decimal("0.00")


def test_a_refund_creates_a_dated_linked_row_and_leaves_the_original_alone():
    payment = PaymentFactory(amount="100.00")
    before = Payment.objects.filter(pk=payment.pk).values().get()

    row, outcome = _add(payment, "100.00", "re_1")

    assert outcome == ProviderReversalResult.CREATED and row is not None
    assert (row.status, row.cause, row.provider_ref) == ("reversal", "refund", "re_1")
    assert (row.reversal_of_id, row.amount, row.date) == (
        payment.pk,
        Decimal("100.00"),
        timezone.localdate(),
    )
    assert Payment.objects.filter(pk=payment.pk).values().get() == before


def test_the_row_is_audited_without_an_actor_and_with_ids_only():
    payment = PaymentFactory(amount="50.00")

    row, _ = _add(payment, "20.00", "re_9")

    entry = AuditEntry.objects.get(action="payment.refund")
    assert entry.actor_id is None and entry.studio_id == payment.student.studio_id
    assert entry.target_id == row.pk
    assert entry.metadata == {"cause": "refund", "amount": "20.00", "ref": "re_9"}


def test_a_lost_dispute_is_audited_as_a_dispute():
    payment = PaymentFactory(amount="50.00")

    _add(payment, "50.00", "dp_1", cause=Payment.Cause.DISPUTE)

    assert AuditEntry.objects.filter(action="payment.dispute").count() == 1


def test_partial_refunds_add_up_and_the_surplus_is_refused_without_writing():
    payment = PaymentFactory(amount="100.00")
    assert _add(payment, "60.00", "re_1")[1] == ProviderReversalResult.CREATED
    assert _add(payment, "40.00", "re_2")[1] == ProviderReversalResult.CREATED

    row, outcome = _add(payment, "0.01", "re_3")

    assert (row, outcome) == (None, ProviderReversalResult.EXCEEDS)
    assert _reversed_total(payment) == Decimal("100.00")
    assert not Payment.objects.filter(provider_ref="re_3").exists()


def test_the_same_refund_notified_again_does_nothing():
    payment = PaymentFactory(amount="100.00")
    _add(payment, "30.00", "re_1")

    row, outcome = _add(payment, "30.00", "re_1")

    assert (row, outcome) == (None, ProviderReversalResult.DUPLICATE)
    assert Payment.objects.filter(reversal_of=payment).count() == 1


@pytest.mark.parametrize("status", ["pending", "overdue"])
def test_only_a_paid_entry_can_receive_a_provider_reversal(status):
    payment = PaymentFactory(status=status)

    assert _add(payment, "10.00", "re_1") == (None, ProviderReversalResult.NOT_APPLICABLE)


def test_a_reversal_row_cannot_be_reversed_again_by_the_provider():
    reversal = make_reversal(PaymentFactory(amount="40.00"))

    assert _add(reversal, "10.00", "re_1") == (None, ProviderReversalResult.NOT_APPLICABLE)


def test_a_manual_reversal_is_refused_once_a_refund_exists():
    payment = PaymentFactory(amount="100.00")
    _add(payment, "10.00", "re_1")

    with pytest.raises(AlreadyReversed):
        reverse_payment(payment, reason="mistake", actor=payment.student.teacher.user)


def test_a_provider_refund_is_refused_after_a_full_manual_reversal():
    payment = PaymentFactory(amount="40.00")
    reverse_payment(payment, reason="mistake", actor=payment.student.teacher.user)

    assert _add(payment, "5.00", "re_1") == (None, ProviderReversalResult.EXCEEDS)


@pytest.mark.parametrize(("cause", "amount"), [("manual", "10.00"), ("refund", "0.00")])
def test_invalid_input_is_a_programming_error(cause, amount):
    payment = PaymentFactory()

    with pytest.raises(ValueError):
        add_provider_reversal(payment, amount=Decimal(amount), cause=cause, provider_ref="re_1")


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("racers", [2, 6])
def test_racing_refunds_never_exceed_the_amount(racers):
    payment = PaymentFactory(amount="100.00")
    barrier = threading.Barrier(racers)
    outcomes: list[str] = []
    lock = threading.Lock()

    def refund(n: int) -> None:
        try:
            original = Payment.objects.get(pk=payment.pk)
            barrier.wait(timeout=5)
            _, result = add_provider_reversal(
                original,
                amount=Decimal("40.00"),
                cause=Payment.Cause.REFUND,
                provider_ref=f"re_{n}",
            )
        except Exception as exc:  # un'eccezione deve far fallire il test, non nascondersi
            result = f"error: {exc!r}"
        finally:
            connection.close()
        with lock:
            outcomes.append(result)

    threads = [threading.Thread(target=refund, args=(n,)) for n in range(racers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)

    created = outcomes.count(ProviderReversalResult.CREATED)
    assert created == min(racers, 2), outcomes  # 40 + 40 stanno nei 100, il terzo no
    assert outcomes.count(ProviderReversalResult.EXCEEDS) == racers - created, outcomes
    assert _reversed_total(payment) <= Decimal("100.00")


@pytest.mark.django_db(transaction=True)
def test_the_same_refund_delivered_by_six_threads_creates_one_row():
    payment = PaymentFactory(amount="100.00")
    barrier = threading.Barrier(6)
    outcomes: list[str] = []
    lock = threading.Lock()

    def refund() -> None:
        try:
            original = Payment.objects.get(pk=payment.pk)
            barrier.wait(timeout=5)
            _, result = add_provider_reversal(
                original,
                amount=Decimal("30.00"),
                cause=Payment.Cause.REFUND,
                provider_ref="re_same",
            )
        except Exception as exc:
            result = f"error: {exc!r}"
        finally:
            connection.close()
        with lock:
            outcomes.append(result)

    threads = [threading.Thread(target=refund) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)

    assert (
        sorted(outcomes)
        == [ProviderReversalResult.CREATED] + [ProviderReversalResult.DUPLICATE] * 5
    ), outcomes
    assert Payment.objects.filter(provider_ref="re_same").count() == 1


def test_a_reversal_is_dated_today_not_backdated():
    payment = PaymentFactory(amount="10.00", date=datetime.date(2025, 1, 1))

    row, _ = _add(payment, "10.00", "re_1")

    assert row.date == timezone.localdate() != payment.date
