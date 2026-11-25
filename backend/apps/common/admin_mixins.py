"""Le due regole dell'admin: sola lettura, oppure modifiche registrate (ADR-041, research R4-R5).

`ReadOnlyAdmin`: per i record definitivi (pagamenti, ricevute, consensi, registro...) e per i dati
che si cambiano solo dai service, perché dall'admin salterebbero i loro controlli. L'operatore
li guarda per l'assistenza, non li tocca.
`AuditedAdmin`: per i pochi modelli modificabili. Ogni salvataggio, cancellazione o azione lascia
una voce nel registro con i nomi dei campi cambiati o il numero di righe, mai i valori.
Spiegazione: docs/learning/concetti/admin-blindato.md.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any

from django.contrib import admin
from django.db.models import Model, QuerySet
from django.forms import ModelForm
from django.http import HttpRequest

from apps.audit import services as audit


class ReadOnlyAdmin(admin.ModelAdmin):
    # Nessuna azione in blocco, nemmeno "delete_selected": su questi modelli non ce n'è una lecita.
    actions = None

    def has_add_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False


def _label(model: type[Model] | Model) -> str:
    return model._meta.label_lower


class AuditedAdmin(admin.ModelAdmin):
    def save_model(
        self, request: HttpRequest, obj: Any, form: ModelForm[Any], change: bool
    ) -> None:
        super().save_model(request, obj, form, change)
        audit.record(
            audit.Action.ADMIN_CHANGE,
            actor=request.user,
            target=obj,
            metadata={
                "model": _label(obj),
                "created": not change,
                # Solo i nomi: un valore (un'email, un nome) nel registro sarebbe una copia di dati.
                "fields": ",".join(sorted(form.changed_data)),
            },
        )

    def delete_model(self, request: HttpRequest, obj: Any) -> None:
        # La voce si scrive prima: dopo la cancellazione l'oggetto non ha più un id.
        audit.record(
            audit.Action.ADMIN_DELETE,
            actor=request.user,
            target=obj,
            metadata={"model": _label(obj)},
        )
        super().delete_model(request, obj)

    def delete_queryset(self, request: HttpRequest, queryset: QuerySet[Any]) -> None:
        audit.record(
            audit.Action.ADMIN_DELETE,
            actor=request.user,
            metadata={"model": _label(queryset.model), "count": queryset.count()},
        )
        super().delete_queryset(request, queryset)


Action = Callable[[Any, HttpRequest, QuerySet[Any]], Any]


def audited_action(func: Action) -> Action:
    """Avvolge un'azione dell'admin: una voce sola, con il nome dell'azione e quante righe."""

    @functools.wraps(func)
    def wrapper(modeladmin: Any, request: HttpRequest, queryset: QuerySet[Any]) -> Any:
        audit.record(
            audit.Action.ADMIN_CHANGE,
            actor=request.user,
            metadata={
                "model": _label(queryset.model),
                "action": func.__name__,
                "count": queryset.count(),
            },
        )
        return func(modeladmin, request, queryset)

    return wrapper
