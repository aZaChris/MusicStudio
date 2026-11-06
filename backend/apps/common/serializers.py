"""Serializer helpers shared by the domain apps."""

from collections.abc import Callable
from typing import Any, ClassVar

from django.db.models import QuerySet
from rest_framework import serializers

from .scoping import packages_visible_to, students_visible_to

ScopeFn = Callable[[Any], QuerySet[Any]]


class ScopedRelatedFieldsMixin(serializers.Serializer[Any]):
    """Restrict writable related fields to objects the requesting user may see.

    DRF validates a primary key against the field's queryset. With the default
    `Model.objects.all()` any id in the database is accepted — that was the
    cross-tenant write hole of feature 001 (audit G1). Replacing the queryset per request
    turns a foreign id into an ordinary 400 "Invalid pk", without revealing whether the
    object exists.
    """

    scoped_fields: ClassVar[dict[str, ScopeFn]] = {
        "student": students_visible_to,
        "package": packages_visible_to,
    }

    def get_fields(self) -> dict[str, serializers.Field[Any, Any, Any, Any]]:
        fields = super().get_fields()
        request = self.context.get("request")
        user = getattr(request, "user", None)
        for name, scope in self.scoped_fields.items():
            field = fields.get(name)
            if isinstance(field, serializers.PrimaryKeyRelatedField) and not field.read_only:
                # The DRF stubs type `queryset` as a manager descriptor; a QuerySet is valid.
                field.queryset = scope(user)  # type: ignore[arg-type]
        return fields
