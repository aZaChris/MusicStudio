"""Invalidazione della cache a ogni scrittura (ADR-017).

Qui i segnali sono una scelta voluta: scattano su ogni percorso di scrittura dell'ORM (service,
admin di Django, `destroy` di DRF, comandi di gestione), che chiamate esplicite nei service
perderebbero. Limite da ricordare: `QuerySet.update()` e `bulk_create()` non inviano segnali.
Spiegazione: docs/learning/concetti/caching.md.
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
    # Lo studio si ricava dallo studente (o è lo studente stesso): lezioni, pacchetti e pagamenti
    # non hanno una colonna studio propria.
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
        # Dopo il commit: una scrittura annullata non deve invalidare, e un lettore non deve
        # ricostruire la cache con dati non ancora confermati.
        transaction.on_commit(lambda: bump_studio_version(studio_id))


def connect() -> None:
    # `dispatch_uid` rende il collegamento idempotente: chiamarlo due volte non duplica i segnali.
    for model in (Lesson, Package, Payment, Student):
        post_save.connect(invalidate_dashboard, sender=model, dispatch_uid=f"dash-save-{model}")
        post_delete.connect(invalidate_dashboard, sender=model, dispatch_uid=f"dash-del-{model}")
