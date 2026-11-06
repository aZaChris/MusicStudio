"""Write use-cases for payments."""

from typing import Any

from django.core.exceptions import ValidationError

from apps.packages.models import Package
from apps.students.models import Student

from .models import Payment


def ensure_package_matches_student(student: Student, package: Package | None) -> None:
    """The one place that enforces "a payment's package belongs to the payment's student"."""
    if package is not None and package.student_id != student.pk:
        raise ValidationError(
            {"package": "Package must belong to the same student as the payment."}
        )


def create_payment(*, student: Student, package: Package | None = None, **fields: Any) -> Payment:
    ensure_package_matches_student(student, package)
    return Payment.objects.create(student=student, package=package, **fields)


def update_payment(payment: Payment, **changes: Any) -> Payment:
    for field, value in changes.items():
        setattr(payment, field, value)
    ensure_package_matches_student(payment.student, payment.package)
    payment.save()
    return payment
