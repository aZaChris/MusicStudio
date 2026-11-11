import datetime
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import User
from apps.audit import services as audit
from apps.audit.models import AuditEntry
from apps.common.factories import LessonFactory, PackageFactory, StudentFactory, UserFactory
from apps.payments.models import Payment
from apps.privacy import services
from apps.students.models import Student

pytestmark = pytest.mark.django_db
NOW = timezone.now()


def archived(days_ago, **extra):
    student = StudentFactory(is_active=False, first_name="Old", **extra)
    Student.objects.filter(pk=student.pk).update(updated_at=NOW - datetime.timedelta(days=days_ago))
    return student


def pay(student, days_ago):
    return Payment.objects.create(
        student=student,
        package=PackageFactory(student=student),
        amount="10.00",
        date=(NOW - datetime.timedelta(days=days_ago)).date(),
        method=Payment.Method.CASH,
    )


def test_archived_students_are_anonymised_only_after_24_months_without_activity():
    old = archived(800)
    recent = archived(100)
    active = StudentFactory(first_name="Active")
    busy = archived(800)
    LessonFactory(student=busy, start_time=NOW - datetime.timedelta(days=30), notes="n")

    result = services.run_retention(NOW)

    assert result["students_anonymised"] == 1
    old.refresh_from_db()
    assert old.first_name == "Allievo" and old.anonymised_at
    for kept in (recent, active, busy):
        kept.refresh_from_db()
        assert kept.anonymised_at is None


def test_old_payments_audit_entries_and_unconfirmed_signups_are_deleted():
    student = StudentFactory()
    old, young = pay(student, 3700), pay(student, 100)
    entry = audit.record("login.failure")
    AuditEntry.objects.filter(pk=entry.pk).update(created_at=NOW - datetime.timedelta(days=400))
    audit.record("login.failure")
    stale_user = UserFactory(email_verified=False)
    User.objects.filter(pk=stale_user.pk).update(date_joined=NOW - datetime.timedelta(days=8))
    fresh_user = UserFactory(email_verified=False)

    result = services.run_retention(NOW)

    assert (result["payments_deleted"], result["audit_deleted"]) == (1, 1)
    assert result["signups_deleted"] == 1
    assert not Payment.objects.filter(pk=old.pk).exists()
    assert Payment.objects.filter(pk=young.pk).exists()
    assert not User.objects.filter(pk=stale_user.pk).exists()
    assert User.objects.filter(pk=fresh_user.pk).exists()


def test_running_twice_changes_nothing_the_second_time():
    archived(800)
    pay(StudentFactory(), 3700)
    services.run_retention(NOW)
    second = services.run_retention(NOW)
    assert second == {
        "students_anonymised": 0,
        "payments_deleted": 0,
        "audit_deleted": 0,
        "signups_deleted": 0,
    }


def test_command_runs_the_same_rules():
    archived(800)
    out = StringIO()
    call_command("run_retention", stdout=out)
    assert "students_anonymised: 1" in out.getvalue()


def test_the_nightly_job_is_scheduled():
    from config.celery import app

    tasks = {e["task"] for e in app.conf.beat_schedule.values()}
    assert "apps.privacy.tasks.run_retention" in tasks
