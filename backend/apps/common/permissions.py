"""DRF permission classes (ADR-011).

Two levels:
- `has_permission` (view level): may this role call this action at all?
- `has_object_permission` (object level): may this user change *this* object?
What a user can see is decided earlier, by the scoped queryset (`scoping.py`): objects
outside the tenant are 404 before any permission runs.
"""

from typing import Any

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request

from apps.accounts.models import User

from .tenancy import get_tenant


class IsTeacherOrStudioOwner(BasePermission):
    """Write access for teacher/studio_owner; read access for any authenticated user.

    What a reader actually sees is still decided by the scoped queryset.
    """

    def has_permission(self, request: Request, view: Any) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return getattr(user, "role", None) in (User.Role.TEACHER, User.Role.STUDIO_OWNER)


class IsStudioOwner(BasePermission):
    def has_permission(self, request: Request, view: Any) -> bool:
        user = request.user
        return bool(
            user and user.is_authenticated and getattr(user, "role", None) == User.Role.STUDIO_OWNER
        )


class CanWriteTenantObject(BasePermission):
    """Object-level write rule: owners write anything in their studio, teachers write the
    objects of their own students, parents never write. Reads are always allowed here
    (visibility was already enforced by the scoped queryset).
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
