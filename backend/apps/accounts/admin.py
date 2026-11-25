"""Admin degli utenti: l'unico modello modificabile, e ogni modifica va nel registro (ADR-041).

Nessun segreto MFA o codice di recupero è registrato nell'admin. Gruppi e token di simplejwt
li toglie apps/common/admin_config.py.
"""

from __future__ import annotations

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.db.models import QuerySet
from django.http import HttpRequest

from apps.common.admin_mixins import AuditedAdmin, audited_action

from .models import User
from .services import revoke_all_sessions


# Azione dell'admin: l'operatore chiude le sessioni di un utente (ADR-018). Il testo che compare
# nell'interfaccia dell'admin resta in inglese, come il resto dell'admin di Django.
@admin.action(description="Revoke all sessions (force sign-in again)")
@audited_action
def revoke_sessions(
    modeladmin: admin.ModelAdmin[User], request: HttpRequest, queryset: QuerySet[User]
) -> None:
    total = sum(revoke_all_sessions(user) for user in queryset)
    modeladmin.message_user(request, f"Revoked {total} session(s).", messages.SUCCESS)


@admin.register(User)
class MusicStudioUserAdmin(AuditedAdmin, UserAdmin):
    actions = [revoke_sessions]
    list_display = ("email", "role", "is_active", "is_staff", "locked_until", "last_login")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("email",)
    ordering = ("email",)
