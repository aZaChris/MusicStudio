from __future__ import annotations

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.db.models import QuerySet
from django.http import HttpRequest

from .models import User
from .services import revoke_all_sessions


@admin.action(description="Revoke all sessions (force sign-in again)")
def revoke_sessions(
    modeladmin: admin.ModelAdmin[User], request: HttpRequest, queryset: QuerySet[User]
) -> None:
    total = sum(revoke_all_sessions(user) for user in queryset)
    modeladmin.message_user(request, f"Revoked {total} session(s).", messages.SUCCESS)


@admin.register(User)
class MusicStudioUserAdmin(UserAdmin):
    actions = [revoke_sessions]
