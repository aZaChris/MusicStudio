"""The studio owner's own export and erasure cover the payment instructions (FR-023)."""

import pytest

from apps.audit.models import AuditEntry
from apps.common.factories import (
    ParentAccountFactory,
    StudentFactory,
    TeacherFactory,
)
from apps.common.tests.helpers import client_for, make_studio_owner
from apps.payments.models import PaymentInstructions

pytestmark = pytest.mark.django_db

IBAN = "IT60X0542811101000000123456"
EXPORT = "/api/v1/privacy/export/"
ERASE = "/api/v1/privacy/erase/"


def _owner_with_instructions():
    owner = make_studio_owner()
    PaymentInstructions.objects.create(
        studio=owner.studio,
        account_holder="Studio Armonia SRL",
        iban=IBAN,
        bank_name="Banca Esempio",
        note="Write the student's name",
        links=[{"label": "PayPal", "url": "https://paypal.me/armonia"}],
    )
    return owner


def test_the_owner_export_includes_the_studio_and_decrypted_instructions():
    owner = _owner_with_instructions()

    res = client_for(owner.user).get(EXPORT)

    assert res.status_code == 200
    data = res.json()
    assert data["account"]["email"] == owner.user.email
    assert data["studio"]["name"] == owner.studio.name
    assert data["studio"]["payment_instructions"] == {
        "account_holder": "Studio Armonia SRL",
        "iban": IBAN,
        "bank_name": "Banca Esempio",
        "note": "Write the student's name",
        "links": [{"label": "PayPal", "url": "https://paypal.me/armonia"}],
    }
    # Nothing about the studio's students or payments is added to the owner's own export.
    assert data["children"] == [] and data["consents"] == []
    assert AuditEntry.objects.filter(action="privacy.export", actor=owner.user).exists()


def test_an_owner_without_instructions_exports_a_null_block():
    owner = make_studio_owner()

    data = client_for(owner.user).get(EXPORT).json()

    assert data["studio"] == {
        "name": owner.studio.name,
        "payment_account": None,
        "payment_instructions": None,
    }


def test_the_export_of_a_family_has_no_studio_block_and_teachers_still_cannot_export():
    parent = ParentAccountFactory()
    teacher = TeacherFactory()

    assert "studio" not in client_for(parent.user).get(EXPORT).json()
    assert client_for(teacher.user).get(EXPORT).status_code == 403


def test_erasing_an_owner_deletes_the_instructions():
    owner = _owner_with_instructions()

    res = client_for(owner.user).post(ERASE, {"password": "password123"}, format="json")

    assert res.status_code == 202
    assert not PaymentInstructions.objects.exists()


def test_an_owner_who_cannot_erase_keeps_the_instructions():
    owner = _owner_with_instructions()
    StudentFactory(teacher=owner)  # the studio still has students: erasure is refused

    res = client_for(owner.user).post(ERASE, {"password": "password123"}, format="json")

    assert res.status_code == 409 and res.data["code"] == "studio_not_empty"
    assert PaymentInstructions.objects.filter(studio=owner.studio).exists()


def test_a_wrong_password_deletes_nothing():
    owner = _owner_with_instructions()

    res = client_for(owner.user).post(ERASE, {"password": "wrong"}, format="json")

    assert res.status_code == 400
    assert PaymentInstructions.objects.filter(studio=owner.studio).exists()


def test_the_owner_export_includes_the_payment_account_id_and_state_only():
    from apps.common.factories import StudioPaymentAccountFactory

    owner = make_studio_owner()
    StudioPaymentAccountFactory(studio=owner.studio, stripe_account_id="acct_test_77")

    data = client_for(owner.user).get(EXPORT).json()

    assert data["studio"]["payment_account"] == {
        "stripe_account_id": "acct_test_77",
        "state": "active",
    }


def test_erasing_an_owner_removes_the_link_to_the_stripe_account():
    from apps.common.factories import StudioPaymentAccountFactory
    from apps.payments.models import StudioPaymentAccount

    owner = make_studio_owner()
    StudioPaymentAccountFactory(studio=owner.studio)

    res = client_for(owner.user).post(ERASE, {"password": "password123"}, format="json")

    assert res.status_code == 202
    assert not StudioPaymentAccount.objects.exists()


def test_deleting_a_studio_removes_its_payment_account():
    from apps.common.factories import StudioFactory, StudioPaymentAccountFactory
    from apps.payments.models import StudioPaymentAccount

    studio = StudioFactory()
    StudioPaymentAccountFactory(studio=studio)

    studio.delete()

    assert not StudioPaymentAccount.objects.exists()
