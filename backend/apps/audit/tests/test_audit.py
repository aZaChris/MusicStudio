"""Audit entries: append-only, request id captured, metadata limited to plain facts."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.audit import services
from apps.audit.models import AuditEntry
from apps.common.factories import StudentFactory, UserFactory
from apps.common.logging import request_id_var

pytestmark = pytest.mark.django_db


def test_record_keeps_identifiers_and_request_id():
    user = UserFactory()
    student = StudentFactory()
    token = request_id_var.set("req-123")
    try:
        entry = services.record(
            services.Action.PRIVACY_EXPORT,
            actor=user,
            target=student,
            studio_id=student.studio_id,
            metadata={"role": "parent", "count": 3, "email": None, "nested": {"x": 1}},
        )
    finally:
        request_id_var.reset(token)

    assert entry.actor == user
    assert (entry.target_type, entry.target_id) == ("student", student.pk)
    assert entry.request_id == "req-123"
    assert entry.metadata == {"role": "parent", "count": 3}  # None and dicts dropped


def test_anonymous_actor_and_missing_request_id():
    entry = services.record(services.Action.LOGIN_FAILURE, outcome=services.Outcome.FAILURE)

    assert entry.actor is None and entry.request_id == ""


def test_entries_cannot_be_changed_or_deleted_one_by_one():
    entry = services.record(services.Action.LOGIN_SUCCESS)

    entry.outcome = services.Outcome.FAILURE
    with pytest.raises(PermissionError):
        entry.save()
    with pytest.raises(PermissionError):
        entry.delete()


def test_purge_removes_only_old_entries():
    old = services.record(services.Action.LOGIN_SUCCESS)
    AuditEntry.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=400))
    recent = services.record(services.Action.LOGIN_SUCCESS)

    deleted = services.purge_older_than(timezone.now() - timedelta(days=365))

    assert deleted == 1
    assert list(AuditEntry.objects.values_list("pk", flat=True)) == [recent.pk]
