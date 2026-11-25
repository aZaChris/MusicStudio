"""Admin dei promemoria: cosa è stato inviato e cosa è in coda, in sola lettura (ADR-041)."""

from django.contrib import admin

from apps.common.admin_mixins import ReadOnlyAdmin

from .models import ReminderDelivery


@admin.register(ReminderDelivery)
class ReminderDeliveryAdmin(ReadOnlyAdmin):
    # Lo stato di un invio lo cambia solo il task: a mano si perderebbe la traccia dei tentativi.
    list_display = ("lesson", "parent", "status", "attempts", "sent_at")
    list_filter = ("status",)
