"""Two simultaneous reversals of the same entry: exactly one is created (FR-009).

Real concurrency, like the overlap test: threads with their own connections released by a
barrier. The lock on the original row makes the second wait, and the unique link on
`reversal_of` is the safety net behind it.
"""

import threading

import pytest
from django.db import connection

from apps.common.factories import PaymentFactory, StudentFactory
from apps.payments.models import Payment
from apps.payments.services import AlreadyReversed, reverse_payment


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("racers", [2, 6])
def test_concurrent_reversals_create_exactly_one(racers):
    student = StudentFactory()
    payment = PaymentFactory(student=student)
    actor = student.teacher.user
    barrier = threading.Barrier(racers)
    outcomes: list[str] = []
    lock = threading.Lock()

    def reverse() -> None:
        try:
            original = Payment.objects.get(pk=payment.pk)
            barrier.wait(timeout=5)
            reverse_payment(original, reason="race", actor=actor)
            result = "created"
        except AlreadyReversed:
            result = "conflict"
        except Exception as exc:  # a crash must fail the test, not hide in a thread
            result = f"error: {exc!r}"
        finally:
            connection.close()
        with lock:
            outcomes.append(result)

    threads = [threading.Thread(target=reverse) for _ in range(racers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)

    assert sorted(outcomes) == ["conflict"] * (racers - 1) + ["created"]
    assert Payment.objects.filter(reversal_of=payment).count() == 1
