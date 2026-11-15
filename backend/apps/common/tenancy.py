"""Contesto del tenant: chi chiede, e in quale studio (ADR-010).

Lo studio è il tenant. A ogni richiesta il contesto dell'utente (ruolo, studio, profilo
insegnante o genitore) si risolve una volta sola, con una query, e si tiene nella richiesta
Django sottostante: ogni serializer, selector e controllo di permesso della stessa richiesta lo
riusa. Spiegazione: docs/learning/concetti/multi-tenancy.md.

Un middleware non può farlo: l'autenticazione JWT gira dentro DRF, dopo i middleware.
"""

from dataclasses import dataclass
from typing import Any

import sentry_sdk

from apps.accounts.models import User


@dataclass(frozen=True)
class TenantContext:
    # Immutabile (frozen): una volta risolto non si cambia per sbaglio a metà richiesta.
    # I quattro `is_*` richiedono anche l'id corrispondente: un utente con ruolo ma senza profilo
    # (dati incoerenti) non ottiene nessun accesso.
    user_id: int | None
    role: str | None
    studio_id: int | None = None
    teacher_id: int | None = None
    parent_id: int | None = None
    student_id: int | None = None

    @property
    def is_owner(self) -> bool:
        return self.role == User.Role.STUDIO_OWNER and self.studio_id is not None

    @property
    def is_teacher(self) -> bool:
        return self.role == User.Role.TEACHER and self.teacher_id is not None

    @property
    def is_parent(self) -> bool:
        return self.role == User.Role.PARENT and self.parent_id is not None

    @property
    def is_student(self) -> bool:
        return self.role == User.Role.STUDENT and self.student_id is not None


# Contesto di chi non è autenticato: nessun ruolo, quindi `scope` restituisce sempre vuoto.
ANONYMOUS = TenantContext(user_id=None, role=None)

_CACHE_ATTR = "_tenant_context"


def resolve_tenant(user: Any) -> TenantContext:
    """Costruisce il contesto di `user` con al massimo una query."""
    if user is None or not getattr(user, "is_authenticated", False):
        return ANONYMOUS

    # Import locali: evitano il giro circolare tra `common` e le app di dominio.
    from apps.students.models import ParentAccount, Student
    from apps.studios.models import Teacher

    role = getattr(user, "role", None)
    if role in (User.Role.TEACHER, User.Role.STUDIO_OWNER):
        row = Teacher.objects.filter(user_id=user.pk).values("id", "studio_id").first()
        if row is not None:
            return TenantContext(
                user_id=user.pk, role=role, studio_id=row["studio_id"], teacher_id=row["id"]
            )
    elif role == User.Role.PARENT:
        parent_id = (
            ParentAccount.objects.filter(user_id=user.pk).values_list("id", flat=True).first()
        )
        if parent_id is not None:
            return TenantContext(user_id=user.pk, role=role, parent_id=parent_id)
    elif role == User.Role.STUDENT:
        student_id = Student.objects.filter(user_id=user.pk).values_list("id", flat=True).first()
        if student_id is not None:
            return TenantContext(user_id=user.pk, role=role, student_id=student_id)
    return TenantContext(user_id=user.pk, role=role)


def get_tenant(request: Any) -> TenantContext:
    """Contesto di questa richiesta, risolto al primo uso e poi in cache."""
    if request is None:
        return ANONYMOUS
    django_request = getattr(request, "_request", request)  # DRF Request wraps HttpRequest
    user = getattr(request, "user", None)
    # La cache vale solo se l'utente è lo stesso: se è cambiato, il contesto si ricalcola.
    cached: TenantContext | None = getattr(django_request, _CACHE_ATTR, None)
    if cached is not None and cached.user_id == getattr(user, "pk", None):
        return cached
    context = resolve_tenant(user)
    setattr(django_request, _CACHE_ATTR, context)
    # I report degli errori dicono quale tenant e utente hanno incontrato il bug; non fa nulla
    # se Sentry è spento.
    sentry_sdk.set_tag("studio_id", context.studio_id)
    sentry_sdk.set_tag("user_id", context.user_id)
    return context
