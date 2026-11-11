from typing import Any

from django.contrib import admin
from django.http import HttpRequest

from .models import AuditEntry


@admin.register(AuditEntry)
class AuditEntryAdmin(admin.ModelAdmin):
    """Read-only: the operator can inspect entries, never edit or delete them."""

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

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False
