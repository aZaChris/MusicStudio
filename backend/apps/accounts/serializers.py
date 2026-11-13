from typing import Any

from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.audit import services as audit
from apps.common.exceptions import DomainError
from apps.students.models import ParentAccount
from apps.studios.models import Teacher

from . import mfa, services
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
    # Always present (possibly empty): typed clients must not have to guard against undefined.
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    mfa_enabled = serializers.SerializerMethodField()

    def get_mfa_enabled(self, obj: User) -> bool:
        return mfa.is_enabled(obj)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "preferred_language",
            "email_verified",
            "mfa_enabled",
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


class InvalidMfaCode(DomainError):
    """401 for a bad token or code at the second step; one body for every cause."""

    status_code = 401
    code = "invalid_mfa"


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
        if mfa.is_enabled(self.user):
            return {"mfa_required": True, "mfa_token": mfa.make_login_token(self.user)}  # type: ignore[dict-item]
        audit.record("login.success", actor=self.user)
        return data

    def _generic_failure(self) -> AuthenticationFailed:
        return AuthenticationFailed(self.error_messages["no_active_account"], "no_active_account")


class PasswordResetConfirmSerializer(UidTokenSerializer):
    new_password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)


class PasswordChangeSerializer(serializers.Serializer[None]):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)


class LoginResponseSerializer(serializers.Serializer[None]):
    """Either the token pair, or `mfa_required` + `mfa_token` when a second step is due."""

    access = serializers.CharField(required=False)
    refresh = serializers.CharField(required=False)
    mfa_required = serializers.BooleanField(required=False)
    mfa_token = serializers.CharField(required=False)


class MfaVerifySerializer(serializers.Serializer[None]):
    mfa_token = serializers.CharField(max_length=512)
    code = serializers.CharField(max_length=32)


class MfaStatusSerializer(serializers.Serializer[None]):
    enabled = serializers.BooleanField()
    recovery_codes_left = serializers.IntegerField()


class MfaSetupSerializer(serializers.Serializer[None]):
    secret = serializers.CharField()
    otpauth_uri = serializers.CharField()


class MfaCodeSerializer(serializers.Serializer[None]):
    code = serializers.CharField(max_length=32)


class MfaPasswordCodeSerializer(MfaCodeSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class MfaRecoveryCodesSerializer(serializers.Serializer[None]):
    recovery_codes = serializers.ListField(child=serializers.CharField())
