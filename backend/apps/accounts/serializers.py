from typing import Any

from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.audit import services as audit
from apps.common.exceptions import DomainError
from apps.students.models import ParentAccount
from apps.studios.models import Teacher

from . import services
from .models import User


class TeacherProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Teacher
        fields = ["id", "studio", "is_owner"]


class ParentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParentAccount
        fields = ["id"]


class MeSerializer(serializers.ModelSerializer):
    # A user has at most one profile; the missing one is null. allow_null documents that.
    teacher = TeacherProfileSerializer(read_only=True, allow_null=True)
    parent_account = ParentProfileSerializer(read_only=True, allow_null=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "role",
            "preferred_language",
            "email_verified",
            "teacher",
            "parent_account",
        ]


class LogoutSerializer(serializers.Serializer[None]):
    refresh = serializers.CharField(write_only=True)


class AcceptedResponseSerializer(serializers.Serializer[None]):
    """Uniform answer of the anonymous account endpoints (no account enumeration)."""

    detail = serializers.CharField()


class RegisterSerializer(serializers.Serializer[None]):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
    studio_name = serializers.CharField(max_length=200)
    accept_terms = serializers.BooleanField()
    preferred_language = serializers.ChoiceField(
        choices=User.Language.choices, default=User.Language.IT
    )

    def validate_accept_terms(self, value: bool) -> bool:
        if not value:
            raise serializers.ValidationError("You must accept the terms and privacy notice.")
        return value


class EmailOnlySerializer(serializers.Serializer[None]):
    email = serializers.EmailField()


class UidTokenSerializer(serializers.Serializer[None]):
    uid = serializers.CharField(max_length=64)
    token = serializers.CharField(max_length=512)


class EmailNotConfirmed(DomainError):
    """401 with a machine-readable code, so the portal can offer to resend the link."""

    status_code = 401
    code = "email_not_confirmed"


class LoginSerializer(TokenObtainPairSerializer):
    """Sign-in with a per-account lockout. Wrong, unknown and locked all answer with the
    same generic 401, so the response never says whether the address exists or is locked.
    Unconfirmed accounts are refused only after a correct password."""

    def validate(self, attrs: dict[str, Any]) -> dict[str, str]:
        email = services.normalize_email(str(attrs.get(self.username_field, "")))
        user = User.objects.filter(email__iexact=email).first()
        if user is not None and services.is_locked(user):
            audit.record("login.failure", actor=user, outcome=audit.Outcome.DENIED)
            raise self._generic_failure()
        try:
            data = super().validate(attrs)
        except AuthenticationFailed:
            if user is None:
                make_password("x")  # same work as a real check, so timing does not leak
                audit.record("login.failure", outcome=audit.Outcome.FAILURE)
            else:
                services.register_login_failure(user)
            raise
        assert self.user is not None  # noqa: S101 - set by super().validate on success
        services.register_login_success(self.user)
        if not self.user.email_verified:
            raise EmailNotConfirmed("Confirm your email address before signing in.")
        audit.record("login.success", actor=self.user)
        return data

    def _generic_failure(self) -> AuthenticationFailed:
        return AuthenticationFailed(self.error_messages["no_active_account"], "no_active_account")


class PasswordResetConfirmSerializer(UidTokenSerializer):
    new_password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)


class PasswordChangeSerializer(serializers.Serializer[None]):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
