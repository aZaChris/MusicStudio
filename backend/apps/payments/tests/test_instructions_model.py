"""PaymentInstructions: one per studio, bank details encrypted at rest (FR-023)."""

import pytest
from django.db import IntegrityError, connection, transaction

from apps.common.factories import StudioFactory
from apps.payments.models import PaymentInstructions

pytestmark = pytest.mark.django_db


def test_iban_and_holder_are_stored_encrypted_and_read_back_in_clear():
    studio = StudioFactory()
    row = PaymentInstructions.objects.create(
        studio=studio, account_holder="Studio Armonia SRL", iban="IT60X0542811101000000123456"
    )

    with connection.cursor() as cursor:
        cursor.execute(
            "select iban, account_holder from payments_paymentinstructions where id = %s", [row.pk]
        )
        raw_iban, raw_holder = cursor.fetchone()

    assert "IT60" not in raw_iban and "Armonia" not in raw_holder
    row.refresh_from_db()
    assert row.iban == "IT60X0542811101000000123456" and row.account_holder == "Studio Armonia SRL"


def test_a_studio_has_at_most_one_set_of_instructions():
    studio = StudioFactory()
    PaymentInstructions.objects.create(studio=studio)

    with pytest.raises(IntegrityError), transaction.atomic():
        PaymentInstructions.objects.create(studio=studio)


def test_the_text_form_never_shows_bank_details():
    studio = StudioFactory()
    row = PaymentInstructions.objects.create(studio=studio, iban="IT60X0542811101000000123456")

    assert "IT60" not in str(row)


def test_deleting_the_studio_deletes_its_instructions():
    studio = StudioFactory()
    PaymentInstructions.objects.create(studio=studio)

    studio.delete()

    assert not PaymentInstructions.objects.exists()
