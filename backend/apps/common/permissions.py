"""DRF permission classes (role checks). Data visibility lives in `scoping.py`."""

from typing import Any

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request

from apps.accounts.models import User


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
