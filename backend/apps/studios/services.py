"""Scritture di studi e insegnanti (services, ADR-002), con il limite di insegnanti per studio."""

from typing import TYPE_CHECKING

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Studio, Teacher

if TYPE_CHECKING:
    from apps.accounts.models import User


def ensure_studio_has_room(studio_id: int, *, joining_teacher_id: int | None = None) -> None:
    """Uno studio ha al massimo STUDIO_MAX_TEACHERS insegnanti (regola di prodotto, da 1 a 10).

    `joining_teacher_id` esclude dal conteggio chi si sta già spostando, così salvare un
    insegnante già presente non lo conta due volte.
    """
    others = Teacher.objects.filter(studio_id=studio_id)
    if joining_teacher_id is not None:
        others = others.exclude(pk=joining_teacher_id)
    if others.count() >= settings.STUDIO_MAX_TEACHERS:
        raise ValidationError(
            {"studio": f"A studio cannot have more than {settings.STUDIO_MAX_TEACHERS} teachers."}
        )


@transaction.atomic
def add_teacher_to_studio(teacher: Teacher, studio: Studio) -> Teacher:
    """Sposta `teacher` in `studio`, rispettando il limite di insegnanti.

    Prima si blocca la riga dello studio (select_for_update): due ingressi concorrenti si
    mettono in coda, quindi il conteggio non può essere letto due volte prima di un inserimento
    (cosa che permetterebbe un undicesimo insegnante). Il problema della concorrenza è lo stesso
    delle lezioni sovrapposte, qui risolto con un lock di riga invece che con un vincolo
    (docs/learning/concetti/exclusion-constraint.md).
    """
    Studio.objects.select_for_update().get(pk=studio.pk)
    ensure_studio_has_room(studio.pk, joining_teacher_id=teacher.pk)
    if teacher.pk is not None and teacher.students.exclude(studio=studio).exists():
        raise ValidationError(
            {"teacher": "Reassign this teacher's students before moving them to another studio."}
        )
    teacher.studio = studio
    teacher.save()
    return teacher


@transaction.atomic
def create_solo_teacher(user: "User", *, studio_name: str | None = None) -> Teacher:
    """Un insegnante che lavora da solo: uno studio personale di una persona, di cui è titolare.

    Studio e insegnante si puntano a vicenda, quindi si crea prima lo studio, poi l'insegnante,
    poi si salva il titolare sullo studio. Tutto in una transazione: o c'è tutto o niente.
    """
    studio = Studio.objects.create(name=studio_name or user.email)
    teacher = Teacher.objects.create(user=user, studio=studio, is_owner=True)
    studio.owner = teacher
    studio.save(update_fields=["owner", "updated_at"])
    return teacher
