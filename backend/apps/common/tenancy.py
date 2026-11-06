"""Tenant context: who is asking, within which studio (ADR-010).

The studio is the tenant. Each request resolves the user's context once — role, studio,
teacher profile or parent profile — with a single query, and caches it on the underlying
Django request so every serializer, selector and permission check in the same request
reuses it.

A middleware cannot do this: JWT authentication runs inside DRF, after middleware.
"""

from dataclasses import dataclass
from typing import Any

from apps.accounts.models import User


@dataclass(frozen=True)
class TenantContext:
    user_id: int | None
    role: str | None
    studio_id: int | None = None
    teacher_id: int | None = None
    parent_id: int | None = None

    @property
    def is_owner(self) -> bool:
        return self.role == User.Role.STUDIO_OWNER and self.studio_id is not None

    @property
    def is_teacher(self) -> bool:
        return self.role == User.Role.TEACHER and self.teacher_id is not None

    @property
    def is_parent(self) -> bool:
        return self.role == User.Role.PARENT and self.parent_id is not None


ANONYMOUS = TenantContext(user_id=None, role=None)

_CACHE_ATTR = "_tenant_context"


def resolve_tenant(user: Any) -> TenantContext:
    """Build the context for `user` with at most one query."""
    if user is None or not getattr(user, "is_authenticated", False):
        return ANONYMOUS

    from apps.students.models import ParentAccount
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
    return TenantContext(user_id=user.pk, role=role)


def get_tenant(request: Any) -> TenantContext:
    """Context for this request, resolved on first use and then cached."""
    if request is None:
        return ANONYMOUS
    django_request = getattr(request, "_request", request)  # DRF Request wraps HttpRequest
    user = getattr(request, "user", None)
    cached: TenantContext | None = getattr(django_request, _CACHE_ATTR, None)
    if cached is not None and cached.user_id == getattr(user, "pk", None):
        return cached
    context = resolve_tenant(user)
    setattr(django_request, _CACHE_ATTR, context)
    return context
