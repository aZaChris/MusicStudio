"""Consent, export and erasure (constitution X, ADR-032)."""

from collections.abc import Iterable

from django.conf import settings

from apps.audit import services as audit
from apps.students.models import ParentAccount, Student

from .models import ConsentRecord


def give_consent(parent: ParentAccount, students: Iterable[Student]) -> ConsentRecord:
    students = list(students)
    record = ConsentRecord.objects.create(
        parent=parent, notice_version=settings.PRIVACY_NOTICE_VERSION
    )
    record.students.set(students)
    for studio_id in {s.studio_id for s in students}:
        audit.record(
            audit.Action.CONSENT_GIVE,
            actor=parent.user,
            target=record,
            studio_id=studio_id,
            metadata={"notice_version": settings.PRIVACY_NOTICE_VERSION},
        )
    return record
