"""Una famiglia con dati in ogni tabella personale: l'export li contiene tutti, e solo i suoi.

ADR-042, spec 010 US3 (FR-011, FR-013, FR-015).
"""

import datetime
import json
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts import mfa, totp
from apps.accounts.models import Invitation, User
from apps.audit import services as audit
from apps.audit.models import AuditEntry
from apps.common.factories import (
    LessonFactory,
    PackageFactory,
    ParentAccountFactory,
    PaymentFactory,
    StudentFactory,
    TeacherFactory,
    link_parent_to_student,
    make_reversal,
)
from apps.common.tests.helpers import client_for, make_studio_owner
from apps.notifications.models import ReminderDelivery
from apps.payments.models import CheckoutSession, PaymentInstructions, Receipt
from apps.privacy import selectors
from apps.privacy.models import ConsentRecord

pytestmark = pytest.mark.django_db
SECRET_IBAN = "IT60X0542811101000000123456"


def build_family(teacher=None):
    """Un genitore con un figlio e almeno una riga in ogni tabella che lo riguarda."""
    teacher = teacher or TeacherFactory()
    parent = ParentAccountFactory()
    child = StudentFactory(teacher=teacher)
    link_parent_to_student(parent, child)
    package = PackageFactory(student=child)
    lesson = LessonFactory(student=child, teacher=teacher, package=package, notes="note")
    payment = PaymentFactory(student=child, package=package)
    Receipt.objects.create(
        payment=payment,
        studio=child.studio,
        year=2026,
        sequence=Receipt.objects.filter(studio=child.studio).count() + 7,
        language="it",
    )
    make_reversal(payment)
    consent = ConsentRecord.objects.create(parent=parent, notice_version="2026-11")
    consent.students.add(child)
    ReminderDelivery.objects.create(lesson=lesson, parent=parent, status="sent")
    CheckoutSession.objects.create(
        package=package, created_by=parent.user, amount=Decimal("40.00"), currency="eur"
    )
    Invitation.objects.create(
        studio=child.studio,
        email=parent.user.email,
        role="parent",
        token_hash=f"{parent.pk:064d}",
        expires_at=timezone.now() + datetime.timedelta(days=7),
        status="accepted",
        accepted_by=parent.user,
    )
    audit.record(audit.Action.LOGIN_SUCCESS, actor=parent.user)
    return parent.user, child


def build_owner():
    owner = make_studio_owner()
    PaymentInstructions.objects.create(studio=owner.studio, iban=SECRET_IBAN)
    secret, _ = mfa.begin_setup(owner.user)
    mfa.confirm_setup(owner.user, totp.code_at(secret, totp.current_step()))
    return owner


def full_family_exports():
    """Gli export di una famiglia completa e di un titolare: insieme coprono ogni chiave."""
    user, _ = build_family()
    owner = build_owner()
    return [selectors.build_export(user), selectors.build_export(owner.user)]


def test_every_personal_table_of_the_family_is_in_the_export():
    user, child = build_family()
    data = selectors.build_export(user)
    (exported_child,) = data["children"]
    assert exported_child["id"] == child.pk
    assert exported_child["lessons"] and exported_child["packages"]
    payments = exported_child["payments"]
    assert [p["receipt_number"] for p in payments if p["reversal_of"] is None] == ["2026-0007"]
    assert any(p["reversal_of"] for p in payments)
    assert data["account"]["mfa_enabled"] is False
    for key in ("consents", "reminders", "online_checkouts", "invitations", "activity"):
        assert data[key], f"{key} is empty"
    assert {"action": "login.success"}.items() <= data["activity"][0].items()


def test_nothing_of_another_family_or_studio_and_no_secret():
    teacher = TeacherFactory()
    user, _ = build_family(teacher)
    other_same_studio, other_child = build_family(teacher)
    other_studio, _ = build_family()
    owner = build_owner()
    raw = json.dumps(selectors.build_export(user), default=str)
    for stranger in (other_same_studio, other_studio, owner.user):
        assert stranger.email not in raw
    assert other_child.first_name not in raw
    assert SECRET_IBAN not in raw
    owner_raw = json.dumps(selectors.build_export(owner.user), default=str)
    assert SECRET_IBAN in owner_raw  # le istruzioni sono dati del titolare
    assert "secret" not in owner_raw and "code_hash" not in owner_raw
    assert json.loads(owner_raw)["account"]["mfa_enabled"] is True


def test_an_erased_person_exports_what_is_left_and_says_so():
    user, child = build_family()
    name = child.first_name
    # Un checkout aperto blocca la cancellazione (409): qui è già scaduto.
    CheckoutSession.objects.filter(created_by=user).update(status="expired")
    res = client_for(user).post("/api/v1/privacy/erase/", {"password": "password123"})
    assert res.status_code == 202
    user.refresh_from_db()
    data = selectors.build_export(user)  # nessun errore anche su un account anonimizzato
    raw = json.dumps(data, default=str)
    assert name not in raw
    assert all(c["anonymised_at"] for c in data["children"])


def test_each_export_request_is_audited_once_and_costs_a_fixed_number_of_queries(
    django_assert_max_num_queries,
):
    user, child = build_family()
    # Un secondo figlio non deve aggiungere query: una per tabella, non una per figlio.
    second = StudentFactory(teacher=child.teacher)
    link_parent_to_student(user.parent_account, second)
    LessonFactory(student=second, teacher=child.teacher)
    client = client_for(user)
    with django_assert_max_num_queries(15):
        res = client.get("/api/v1/privacy/export/")
    assert res.status_code == 200
    assert AuditEntry.objects.filter(action="privacy.export", actor=user).count() == 1


def test_parents_are_not_mfa_users_but_the_flag_is_still_reported():
    user = User.objects.get(pk=build_family()[0].pk)
    assert selectors.build_export(user)["account"]["mfa_enabled"] is False
