"""Cache invalidation on writes (ADR-017).

Signals are used on purpose here: they fire on every ORM write path — services, the
Django admin, DRF `destroy`, management commands — which explicit calls in services would
miss. Limitation to remember: `QuerySet.update()` and `bulk_create()` do not send signals.
"""

from typing import Any

from django.db import transaction
from django.db.models.signals import post_delete, post_save

from apps.lessons.cache import bump_studio_version
from apps.lessons.models import Lesson
from apps.packages.models import Package
from apps.payments.models import Payment
from apps.students.models import Student


def _studio_of(instance: Any) -> int | None:
    if isinstance(instance, Student):
        studio_id: int | None = instance.studio_id
        return studio_id
    student_id = getattr(instance, "student_id", None)
    if student_id is None:
        return None
    return Student.objects.filter(pk=student_id).values_list("studio_id", flat=True).first()


def invalidate_dashboard(sender: Any, instance: Any, **kwargs: Any) -> None:
    studio_id = _studio_of(instance)
    if studio_id is not None:
        # After commit: a rolled-back write must not invalidate, and a reader must not
        # rebuild the cache from data that is not committed yet.
        transaction.on_commit(lambda: bump_studio_version(studio_id))


def connect() -> None:
    for model in (Lesson, Package, Payment, Student):
        post_save.connect(invalidate_dashboard, sender=model, dispatch_uid=f"dash-save-{model}")
        post_delete.connect(invalidate_dashboard, sender=model, dispatch_uid=f"dash-del-{model}")
