"""Admin del registro: l'operatore può guardare le voci, mai crearle, modificarle o cancellarle."""

from django.contrib import admin

from apps.common.admin_mixins import ReadOnlyAdmin

from .models import AuditEntry


@admin.register(AuditEntry)
class AuditEntryAdmin(ReadOnlyAdmin):
    # Un registro che l'operatore può riscrivere non prova niente
    # (docs/learning/concetti/audit-log.md): ReadOnlyAdmin nega i tre permessi di scrittura.
    list_display = (
        "created_at",
        "action",
        "outcome",
        "actor",
        "studio",
        "target_type",
        "target_id",
    )
    list_filter = ("action", "outcome")
    date_hierarchy = "created_at"
