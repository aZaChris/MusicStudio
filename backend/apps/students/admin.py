"""Admin di studenti e genitori, in sola lettura (ADR-041).

Sono dati personali di minori: l'admin serve solo a guardare, per l'assistenza. Gli elenchi
mostrano id e studio, i nomi solo nella pagina del singolo studente.
"""

from django.contrib import admin

from apps.common.admin_mixins import ReadOnlyAdmin

from .models import ParentAccount, ParentStudentLink, Student


@admin.register(Student)
class StudentAdmin(ReadOnlyAdmin):
    list_display = ("id", "studio", "teacher", "is_active", "is_adult", "anonymised_at")
    list_filter = ("is_active", "is_adult")


@admin.register(ParentAccount)
class ParentAccountAdmin(ReadOnlyAdmin):
    list_display = ("id", "user", "created_at")


@admin.register(ParentStudentLink)
class ParentStudentLinkAdmin(ReadOnlyAdmin):
    list_display = ("id", "parent", "student", "created_at")
