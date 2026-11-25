"""Ogni modello nell'admin ha una regola scritta: sola lettura o modificabile, mai campi cifrati.

ADR-041, specs/010 US2 (FR-007, FR-010). Registrare un modello nuovo senza deciderne la regola
fa fallire il primo test.
"""

import pytest
from django.contrib import admin
from django.test import RequestFactory

from apps.accounts.models import User
from apps.common.fields import EncryptedTextField

pytestmark = pytest.mark.django_db

# Record definitivi per scelta (constitution X, fase 8): mai creati, modificati o cancellati a mano.
FINAL = {
    "payments.payment",
    "payments.receipt",
    "payments.paymentdispute",
    "payments.webhookevent",
    "payments.checkoutsession",
    "privacy.consentrecord",
    "audit.auditentry",
}
# Dati che si cambiano solo dai service (sovrapposizioni, saldo, limiti): dall'admin si guardano.
SERVICE_ONLY = {
    "lessons.lesson",
    "packages.package",
    "students.student",
    "students.parentaccount",
    "students.parentstudentlink",
    "studios.studio",
    "studios.teacher",
    "notifications.reminderdelivery",
}
# Le uniche modifiche ammesse, tutte registrate nel registro (AuditedAdmin).
EDITABLE = {"accounts.user"}


@pytest.fixture
def request_():
    request = RequestFactory().get("/")
    request.user = User(is_staff=True, is_superuser=True, is_active=True)
    return request


def registry():
    return {model._meta.label_lower: (model, ma) for model, ma in admin.site._registry.items()}


def test_every_registered_model_has_a_rule():
    assert set(registry()) == FINAL | SERVICE_ONLY | EDITABLE


@pytest.mark.parametrize("label", sorted(FINAL | SERVICE_ONLY))
def test_read_only_models_cannot_be_written_from_the_admin(label, request_):
    _, ma = registry()[label]
    assert not ma.has_add_permission(request_)
    assert not ma.has_change_permission(request_)
    assert not ma.has_delete_permission(request_)
    assert "delete_selected" not in ma.get_actions(request_)
    assert ma.has_view_permission(request_)


@pytest.mark.parametrize("label", sorted(FINAL | SERVICE_ONLY | EDITABLE))
def test_no_screen_shows_an_encrypted_field(label, request_):
    model, ma = registry()[label]
    encrypted = {f.name for f in model._meta.fields if isinstance(f, EncryptedTextField)}
    shown = {
        *ma.get_fields(request_),
        *ma.get_list_display(request_),
        *ma.get_search_fields(request_),
        *[f for f in ma.get_list_filter(request_) if isinstance(f, str)],
    }
    assert not encrypted & shown, f"{label} shows {encrypted & shown}"


def test_mfa_secrets_and_recovery_codes_are_not_in_the_admin():
    assert not {"accounts.mfadevice", "accounts.recoverycode"} & set(registry())
