"""Receipt: one per payment, one number per studio and year, enforced by the database."""

import pytest
from django.db import IntegrityError, transaction

from apps.common.factories import PaymentFactory, StudentFactory
from apps.payments.models import Receipt

pytestmark = pytest.mark.django_db


def _receipt(payment, **overrides):
    fields = {
        "payment": payment,
        "studio": payment.student.studio,
        "year": 2026,
        "sequence": 1,
        "language": "it",
        **overrides,
    }
    return Receipt.objects.create(**fields)


def test_the_number_is_year_dash_four_digits():
    assert _receipt(PaymentFactory(), sequence=7).number == "2026-0007"
    assert _receipt(PaymentFactory(), sequence=12345, year=2027).number == "2027-12345"
    assert str(_receipt(PaymentFactory(), sequence=2)) == "Receipt 2026-0002"


def test_a_payment_has_at_most_one_receipt():
    payment = PaymentFactory()
    _receipt(payment)

    with pytest.raises(IntegrityError), transaction.atomic():
        _receipt(payment, sequence=2)


def test_a_number_is_unique_within_a_studio_and_year_only():
    student = StudentFactory()
    first = PaymentFactory(student=student)
    second = PaymentFactory(student=student)
    _receipt(first)

    with pytest.raises(IntegrityError), transaction.atomic():
        _receipt(second)  # same studio, same year, same sequence

    _receipt(second, year=2027)  # another year: fine
    other_studio = PaymentFactory()
    _receipt(other_studio)  # another studio: fine
