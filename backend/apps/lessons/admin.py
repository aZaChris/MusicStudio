"""Admin delle lezioni, in sola lettura (ADR-041).

Una modifica dall'admin salterebbe i controlli di services.py (sovrapposizioni, saldo del
pacchetto). Le note sono cifrate e non compaiono.
"""

from django.contrib import admin

from apps.common.admin_mixins import ReadOnlyAdmin

from .models import Lesson


@admin.register(Lesson)
class LessonAdmin(ReadOnlyAdmin):
    list_display = ("id", "start_time", "status", "teacher", "student")
    list_filter = ("status",)
    date_hierarchy = "start_time"
    exclude = ("notes",)
