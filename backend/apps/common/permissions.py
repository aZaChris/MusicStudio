"""Constitution Principle I (Tenant Isolation & RBAC) choke point.

Every ViewSet touching Student/Lesson/Package/Payment data MUST scope its queryset
through `role_scoped_queryset` (ORM-level filtering) rather than relying on
serializer-level hiding or view-level checks alone.
"""
from rest_framework.permissions import BasePermission

from apps.accounts.models import User


def role_scoped_queryset(
    user, base_qs, *, teacher_field: str, studio_field: str, parent_field: str
):
    """Filter `base_qs` to exactly what `user` is allowed to see, based on role.

    - teacher_field / studio_field / parent_field are ORM lookup paths (Django
      double-underscore syntax) from `base_qs`'s model down to a Teacher, a Studio,
      and a ParentAccount respectively.
    """
    role = getattr(user, "role", None)  # AnonymousUser (e.g. schema generation) has none

    if role == User.Role.STUDIO_OWNER:
        teacher = getattr(user, "teacher", None)
        if teacher is None or teacher.studio_id is None:
            return base_qs.none()
        return base_qs.filter(**{studio_field: teacher.studio}).distinct()

    if role == User.Role.TEACHER:
        teacher = getattr(user, "teacher", None)
        if teacher is None:
            return base_qs.none()
        return base_qs.filter(**{teacher_field: teacher}).distinct()

    if role == User.Role.PARENT:
        parent_account = getattr(user, "parent_account", None)
        if parent_account is None:
            return base_qs.none()
        return base_qs.filter(**{parent_field: parent_account}).distinct()

    return base_qs.none()


class IsTeacherOrStudioOwner(BasePermission):
    """Allows write access to teacher/studio_owner roles; read-only reachable by anyone
    authenticated (actual data visibility is still enforced by the scoped queryset)."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return request.user.role in (User.Role.TEACHER, User.Role.STUDIO_OWNER)


class IsStudioOwner(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == User.Role.STUDIO_OWNER)
