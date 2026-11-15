"""The database itself guarantees the shape of a reversal (FR-004, FR-009)."""

import pytest
from django.db import IntegrityError, transaction

from apps.common.factories import PaymentFactory
from apps.payments.models import Payment

pytestmark = pytest.mark.django_db


def _reversal_of(original: Payment, **overrides) -> Payment:
    fields = {
        "student": original.student,
        "amount": original.amount,
        "date": original.date,
        "method": original.method,
        "status": Payment.Status.REVERSAL,
        "reversal_of": original,
    }
    return Payment(**{**fields, **overrides})


def test_a_well_formed_reversal_is_accepted():
    original = PaymentFactory()
    reversal = _reversal_of(original, reason="wrong student")
    reversal.save()
    original.refresh_from_db()
    assert original.reversal == reversal
    assert Payment.objects.get(pk=reversal.pk).reason == "wrong student"


def test_a_reversal_without_a_link_is_refused():
    original = PaymentFactory()
    with pytest.raises(IntegrityError), transaction.atomic():
        _reversal_of(original, reversal_of=None).save()


def test_a_link_on_a_normal_entry_is_refused():
    original = PaymentFactory()
    with pytest.raises(IntegrityError), transaction.atomic():
        _reversal_of(original, status=Payment.Status.PAID).save()


def test_an_original_cannot_have_two_reversals():
    original = PaymentFactory()
    _reversal_of(original).save()
    with pytest.raises(IntegrityError), transaction.atomic():
        _reversal_of(original).save()


def test_a_reversal_amount_must_be_positive():
    original = PaymentFactory()
    with pytest.raises(IntegrityError), transaction.atomic():
        _reversal_of(original, amount="-40.00").save()


def test_old_style_entries_still_save_and_reason_is_stored_encrypted():
    entry = PaymentFactory(status=Payment.Status.PENDING)
    assert entry.reason == "" and entry.recorded_by is None and entry.reversal_of is None
    original = PaymentFactory()
    reversal = _reversal_of(original, reason="secret reason")
    reversal.save()
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("select reason from payments_payment where id = %s", [reversal.pk])
        assert "secret reason" not in cursor.fetchone()[0]
