"""Classi di permesso di DRF (ADR-011).

Due livelli:
- `has_permission` (livello view): questo ruolo può chiamare questa azione?
- `has_object_permission` (livello oggetto): questo utente può cambiare *questo* oggetto?
Che cosa un utente può vedere si decide prima, dal queryset con ambito (`scoping.py`): gli
oggetti fuori dal tenant danno 404 prima ancora che un permesso venga valutato.
Spiegazione: docs/learning/concetti/permessi-drf.md.
"""

from typing import Any

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request

from apps.accounts.models import User

from .tenancy import get_tenant


class IsTeacherOrStudioOwner(BasePermission):
    """Scrittura per insegnanti e titolari; lettura per qualunque utente autenticato.

    Ciò che un lettore vede davvero lo decide comunque il queryset con ambito.
    """

    def has_permission(self, request: Request, view: Any) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return getattr(user, "role", None) in (User.Role.TEACHER, User.Role.STUDIO_OWNER)


class IsTeacherOrOwnerRole(BasePermission):
    # Solo insegnanti e titolari, anche in lettura: genitori e studenti adulti no. A differenza di
    # IsTeacherOrStudioOwner (che in lettura lascia passare chiunque sia autenticato) serve agli
    # endpoint che i genitori non devono vedere affatto: inviti, registro di cassa, ricevute.
    def has_permission(self, request: Request, view: Any) -> bool:
        return getattr(request.user, "role", None) in (User.Role.TEACHER, User.Role.STUDIO_OWNER)


class IsFamilyRole(BasePermission):
    # Genitori e studenti adulti: le persone a cui si mostra come pagare (fase 8).
    def has_permission(self, request: Request, view: Any) -> bool:
        return getattr(request.user, "role", None) in (User.Role.PARENT, User.Role.STUDENT)


class IsStudioOwner(BasePermission):
    # Solo il titolare dello studio (gestione dello studio, registro delle azioni).
    def has_permission(self, request: Request, view: Any) -> bool:
        user = request.user
        return bool(
            user and user.is_authenticated and getattr(user, "role", None) == User.Role.STUDIO_OWNER
        )


class CanWriteTenantObject(BasePermission):
    """Regola di scrittura per oggetto: i titolari scrivono tutto nel loro studio, gli insegnanti
    gli oggetti dei propri studenti, i genitori mai. Qui le letture passano sempre (la
    visibilità l'ha già imposta il queryset con ambito).
    """

    def has_object_permission(self, request: Request, view: Any, obj: Any) -> bool:
        if request.method in SAFE_METHODS:
            return True
        ctx = get_tenant(request)
        studio_id, teacher_id = obj.tenant_keys()
        if ctx.is_owner:
            return bool(studio_id == ctx.studio_id)
        if ctx.is_teacher:
            return bool(teacher_id == ctx.teacher_id)
        return False
