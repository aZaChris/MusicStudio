"""Admin degli utenti, con l'azione per chiudere tutte le sessioni.

FUTURO (rafforzamento dell'admin, fase 5 in CLAUDE.md): colonne e filtri per ruolo, e nessuna
modifica diretta dei campi di blocco e dei dati personali.
"""

from __future__ import annotations

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.db.models import QuerySet
from django.http import HttpRequest

from .models import User
from .services import revoke_all_sessions


# Azione dell'admin: l'operatore chiude le sessioni di un utente (ADR-018). Il testo che compare
# nell'interfaccia dell'admin resta in inglese, come il resto dell'admin di Django.
@admin.action(description="Revoke all sessions (force sign-in again)")
def revoke_sessions(
    modeladmin: admin.ModelAdmin[User], request: HttpRequest, queryset: QuerySet[User]
) -> None:
    total = sum(revoke_all_sessions(user) for user in queryset)
    modeladmin.message_user(request, f"Revoked {total} session(s).", messages.SUCCESS)


@admin.register(User)
class MusicStudioUserAdmin(UserAdmin):
    actions = [revoke_sessions]
