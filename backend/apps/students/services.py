"""Scritture degli studenti (services, ADR-002)."""

from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.common.tenancy import TenantContext
from apps.studios.models import Teacher

from .models import Student


def create_student(ctx: TenantContext, **fields: Any) -> Student:
    """Uno studente appartiene all'insegnante che lo crea (titolare compreso) e al suo studio.

    Studio e insegnante vengono sempre dal contesto, mai dal client: così non si può creare uno
    studente in uno studio altrui (ADR-010).
    """
    if ctx.teacher_id is None or ctx.studio_id is None:
        raise ValidationError("Only users with a teacher profile can create students.")
    return Student.objects.create(teacher_id=ctx.teacher_id, studio_id=ctx.studio_id, **fields)


@transaction.atomic
def reassign_student(student: Student, teacher: Teacher) -> Student:
    """Passa uno studente a un altro insegnante dello stesso studio.

    Le lezioni esistenti restano all'insegnante di prima: lo storico resta veritiero e l'agenda
    del nuovo insegnante non si rompe per lezioni che non ha fissato lui.
    """
    if teacher.studio_id != student.studio_id:
        raise ValidationError({"teacher": "The teacher must belong to the student's studio."})
    student.teacher = teacher
    student.save(update_fields=["teacher", "updated_at"])
    return student
