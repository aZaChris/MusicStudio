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
    assert list(original.reversals.all()) == [reversal]
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


# --- Fase 9: più storni dal fornitore, id del fornitore unico (ADR-038) -------------------


def _provider_reversal(original: Payment, ref: str | None, amount: str, **overrides) -> Payment:
    return _reversal_of(
        original,
        amount=amount,
        cause=Payment.Cause.REFUND,
        provider_ref=ref,
        **overrides,
    )


def test_an_original_can_have_several_provider_reversals():
    original = PaymentFactory(amount="100.00")
    _provider_reversal(original, "re_1", "30.00").save()
    _provider_reversal(original, "re_2", "20.00").save()

    assert original.reversals.count() == 2


def test_the_same_provider_ref_cannot_be_stored_twice():
    original = PaymentFactory(amount="100.00")
    _provider_reversal(original, "re_1", "30.00").save()
    with pytest.raises(IntegrityError), transaction.atomic():
        _provider_reversal(original, "re_1", "30.00").save()


def test_a_provider_reversal_needs_its_provider_ref():
    original = PaymentFactory()
    with pytest.raises(IntegrityError), transaction.atomic():
        _provider_reversal(original, None, "10.00").save()


def test_a_manual_reversal_cannot_carry_a_provider_ref():
    original = PaymentFactory()
    with pytest.raises(IntegrityError), transaction.atomic():
        _reversal_of(original, provider_ref="re_x").save()


def test_a_manual_reversal_is_still_unique_even_next_to_provider_ones():
    original = PaymentFactory(amount="100.00")
    _provider_reversal(original, "re_1", "30.00").save()
    _reversal_of(original).save()
    with pytest.raises(IntegrityError), transaction.atomic():
        _reversal_of(original).save()


def test_existing_style_rows_default_to_a_manual_cause_without_ref():
    entry = PaymentFactory()
    assert entry.cause == Payment.Cause.MANUAL and entry.provider_ref is None
