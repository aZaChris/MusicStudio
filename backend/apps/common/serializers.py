"""Strumenti per i serializer condivisi dalle app di dominio.

I docstring dei serializer finiscono in openapi.yaml (contratto in inglese): dove servono
si usano commenti `#`.
"""

from collections.abc import Callable
from typing import Any, ClassVar

from django.db.models import QuerySet
from rest_framework import serializers

from .scoping import packages_visible_to, students_visible_to
from .tenancy import TenantContext, get_tenant

ScopeFn = Callable[[TenantContext], QuerySet[Any]]


class ScopedRelatedFieldsMixin(serializers.Serializer[Any]):
    """Restrict writable related fields to objects the requesting user may see.

    DRF validates a primary key against the field's queryset. With the default
    `Model.objects.all()` any id in the database is accepted — that was the
    cross-tenant write hole of feature 001 (audit G1). Replacing the queryset per request
    turns a foreign id into an ordinary 400 "Invalid pk", without revealing whether the
    object exists.
    """

    # Il docstring sopra resta in inglese: i serializer che ereditano questo mixin lo copiano
    # nella descrizione di openapi.yaml (contratto). In breve: DRF valida la chiave primaria
    # contro il queryset del campo, e con `Model.objects.all()` qualsiasi id sarebbe accettato
    # (falla di scrittura tra tenant, audit G1). Sostituendo il queryset a ogni richiesta un id
    # estraneo diventa un normale 400, senza rivelare se esiste.
    # Spiegazione: docs/learning/concetti/isolamento-tenant-e-bola.md.

    # Nome del campo -> funzione che dà gli oggetti visibili. Per estendere: una voce in più.
    scoped_fields: ClassVar[dict[str, ScopeFn]] = {
        "student": students_visible_to,
        "package": packages_visible_to,
    }

    def get_fields(self) -> dict[str, serializers.Field[Any, Any, Any, Any]]:
        fields = super().get_fields()
        ctx = get_tenant(self.context.get("request"))
        for name, scope in self.scoped_fields.items():
            field = fields.get(name)
            if isinstance(field, serializers.PrimaryKeyRelatedField) and not field.read_only:
                # Gli stub di DRF tipizzano `queryset` come descrittore di manager: un QuerySet
                # però è valido.
                field.queryset = scope(ctx)  # type: ignore[arg-type]
        return fields
