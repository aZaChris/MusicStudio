"""Admin dei consensi, in sola lettura: sono la prova di cosa ha accettato il genitore (ADR-041)."""

from django.contrib import admin

from apps.common.admin_mixins import ReadOnlyAdmin

from .models import ConsentRecord


@admin.register(ConsentRecord)
class ConsentRecordAdmin(ReadOnlyAdmin):
    list_display = ("id", "parent", "notice_version", "given_at", "withdrawn_at")
