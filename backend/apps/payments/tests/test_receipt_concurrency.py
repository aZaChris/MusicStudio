"""Twenty simultaneous receipts in one studio: twenty distinct, gapless numbers (SC-007).

Real concurrency: one thread per payment, each with its own connection, released together by a
barrier. The lock on the studio row serialises the numbering; the unique constraint on
(studio, year, sequence) is the safety net behind it.
"""

import threading

import pytest
from django.db import connection

from apps.common.factories import PaymentFactory, StudentFactory
from apps.payments.models import Payment, Receipt
from apps.payments.services import issue_receipt

RACERS = 20


@pytest.mark.django_db(transaction=True)
def test_twenty_simultaneous_receipts_get_twenty_distinct_gapless_numbers():
    student = StudentFactory()
    actor = student.teacher.user
    payment_ids = [PaymentFactory(student=student).pk for _ in range(RACERS)]
    barrier = threading.Barrier(RACERS)
    results: list[str] = []
    lock = threading.Lock()

    def issue(payment_id: int) -> None:
        try:
            payment = Payment.objects.get(pk=payment_id)
            barrier.wait(timeout=10)
            receipt, created = issue_receipt(payment, language="it", actor=actor)
            outcome = f"{receipt.number}:{created}"
        except Exception as exc:  # a crash must fail the test, not hide in a thread
            outcome = f"error: {exc!r}"
        finally:
            connection.close()
        with lock:
            results.append(outcome)

    threads = [threading.Thread(target=issue, args=(pk,)) for pk in payment_ids]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert len(results) == RACERS and not [r for r in results if r.startswith("error")], results
    sequences = sorted(Receipt.objects.values_list("sequence", flat=True))
    assert sequences == list(range(1, RACERS + 1))  # distinct, none skipped, none repeated
    assert len({r.split(":")[0] for r in results}) == RACERS
    assert all(r.endswith(":True") for r in results)


@pytest.mark.django_db(transaction=True)
def test_simultaneous_requests_for_the_same_payment_make_one_receipt():
    student = StudentFactory()
    actor = student.teacher.user
    payment = PaymentFactory(student=student)
    barrier = threading.Barrier(6)
    outcomes: list[tuple[str, bool]] = []
    lock = threading.Lock()

    def issue() -> None:
        try:
            current = Payment.objects.get(pk=payment.pk)
            barrier.wait(timeout=10)
            receipt, created = issue_receipt(current, language="en", actor=actor)
            result = (receipt.number, created)
        finally:
            connection.close()
        with lock:
            outcomes.append(result)

    threads = [threading.Thread(target=issue) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert len(outcomes) == 6 and len({number for number, _ in outcomes}) == 1
    assert sorted(created for _, created in outcomes) == [False] * 5 + [True]
    assert Receipt.objects.count() == 1
