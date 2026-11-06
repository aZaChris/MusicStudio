"""Read queries for payments."""

from typing import Any

from django.db.models import QuerySet

from apps.common.scoping import role_scoped_queryset

from .models import Payment


def payments_for(user: Any) -> QuerySet[Payment]:
    return role_scoped_queryset(
        user,
        Payment.objects.select_related("student"),
        teacher_field="student__teacher",
        studio_field="student__teacher__studio",
        parent_field="student__parent_accounts",
    )
