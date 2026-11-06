"""Write use-cases for packages."""

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
    """A new package starts full: remaining = total. Clients cannot choose otherwise."""
    return Package.objects.create(
        student=student,
        total_lessons=total_lessons,
        lessons_remaining=total_lessons,
        purchase_date=purchase_date,
        expiry_date=expiry_date,
        price=price,
    )
