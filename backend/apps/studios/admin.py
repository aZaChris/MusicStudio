"""Admin di studi e insegnanti, in sola lettura (ADR-041).

Il limite di insegnanti per studio e il titolare si cambiano solo da services.py.
"""

from django.contrib import admin

from apps.common.admin_mixins import ReadOnlyAdmin

from .models import Studio, Teacher


@admin.register(Studio)
class StudioAdmin(ReadOnlyAdmin):
    list_display = ("id", "name", "owner", "created_at")


@admin.register(Teacher)
class TeacherAdmin(ReadOnlyAdmin):
    list_display = ("id", "user", "studio", "is_owner")
    list_filter = ("is_owner",)
