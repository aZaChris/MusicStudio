"""Admin dei promemoria: serve a vedere cosa è stato inviato e cosa è rimasto in coda.

FUTURO (rafforzamento dell'admin, fase 5 in CLAUDE.md): rendere i campi in sola lettura, così da
non poter cambiare a mano lo stato di un invio.
"""

from django.contrib import admin

from .models import ReminderDelivery


@admin.register(ReminderDelivery)
class ReminderDeliveryAdmin(admin.ModelAdmin):
    list_display = ("lesson", "parent", "status", "attempts", "sent_at")
    list_filter = ("status",)
