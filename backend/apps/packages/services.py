"""Scritture dei pacchetti (services). Le view non toccano il modello direttamente (ADR-002)."""

import datetime
from decimal import Decimal

from apps.students.models import Student

from .models import Package


def create_package(
    *,
    student: Student,
    total_lessons: int,
    purchase_date: datetime.date,
    price: Decimal,
    expiry_date: datetime.date | None = None,
) -> Package:
    """Crea un pacchetto nuovo, sempre pieno: rimanenti = totali.

    Il client non può scegliere `lessons_remaining`: il serializer lo tratta in sola lettura.
    Da qui in poi lo scala solo `lessons.services.complete_lesson`, quando una lezione si
    svolge. Così il saldo non si può falsare dall'API.
    """
    return Package.objects.create(
        student=student,
        total_lessons=total_lessons,
        lessons_remaining=total_lessons,
        purchase_date=purchase_date,
        expiry_date=expiry_date,
        price=price,
    )
