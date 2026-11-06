from django.contrib import admin

from .models import ReminderDelivery


@admin.register(ReminderDelivery)
class ReminderDeliveryAdmin(admin.ModelAdmin):
    list_display = ("lesson", "parent", "status", "attempts", "sent_at")
    list_filter = ("status",)
