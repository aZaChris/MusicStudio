"""Ogni scrittura fatta dall'admin lascia una voce nel registro: chi, cosa, quanti (FR-008)."""

import pytest
from django.conf import settings
from django.contrib import admin
from django.forms import modelform_factory
from django.test import Client, RequestFactory

from apps.accounts.models import User
from apps.audit.models import AuditEntry

pytestmark = pytest.mark.django_db
PW = "Pianoforte-Verde-31"


@pytest.fixture
def operator():
    return User.objects.create_user(
        username="op", email="op@example.com", password=PW, is_staff=True, is_superuser=True
    )


@pytest.fixture
def user_admin():
    return admin.site._registry[User]


def request_for(user):
    request = RequestFactory().post("/")
    request.user = user
    return request


def parent(n: int) -> User:
    return User.objects.create_user(
        username=f"p{n}", email=f"p{n}@example.com", password=PW, role="parent"
    )


def test_a_change_records_the_field_names_but_never_the_values(operator, user_admin):
    target = parent(1)
    form = modelform_factory(User, fields=["first_name", "is_active"])(
        data={"first_name": "Segreto", "is_active": False}, instance=target
    )
    assert form.is_valid()
    user_admin.save_model(request_for(operator), form.save(commit=False), form, True)
    entry = AuditEntry.objects.get(action="admin.change")
    assert (entry.actor_id, entry.target_id) == (operator.pk, target.pk)
    assert entry.metadata["model"] == "accounts.user"
    assert set(entry.metadata["fields"].split(",")) == {"first_name", "is_active"}
    assert "Segreto" not in str(entry.metadata)


def test_a_delete_records_the_object(operator, user_admin):
    target = parent(2)
    target_id = target.pk
    user_admin.delete_model(request_for(operator), target)
    entry = AuditEntry.objects.get(action="admin.delete")
    assert (entry.actor_id, entry.target_id) == (operator.pk, target_id)


def test_a_bulk_delete_is_one_entry_with_the_count(operator, user_admin):
    ids = [parent(n).pk for n in range(3, 6)]
    user_admin.delete_queryset(request_for(operator), User.objects.filter(pk__in=ids))
    entry = AuditEntry.objects.get(action="admin.delete")
    assert entry.metadata == {"model": "accounts.user", "count": 3}


def test_a_custom_action_is_audited_once_with_the_count(operator, settings_):
    targets = [parent(n).pk for n in range(6, 8)]
    client = Client()
    client.force_login(operator)
    res = client.post(
        f"/{settings.ADMIN_URL}accounts/user/",
        {"action": "revoke_sessions", "_selected_action": targets},
    )
    assert res.status_code == 302
    entry = AuditEntry.objects.get(action="admin.change")
    assert entry.metadata == {"model": "accounts.user", "action": "revoke_sessions", "count": 2}


@pytest.fixture
def settings_(settings):
    settings.ADMIN_REQUIRE_TOTP = False
    return settings
