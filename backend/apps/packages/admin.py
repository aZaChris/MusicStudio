"""Admin dei pacchetti, in sola lettura: il saldo cambia solo dai service (ADR-041)."""

from django.contrib import admin

from apps.common.admin_mixins import ReadOnlyAdmin

from .models import Package


@admin.register(Package)
class PackageAdmin(ReadOnlyAdmin):
    list_display = ("id", "student", "total_lessons", "lessons_remaining", "expiry_date")
