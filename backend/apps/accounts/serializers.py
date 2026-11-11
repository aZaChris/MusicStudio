from typing import Any

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.common.exceptions import DomainError
from apps.students.models import ParentAccount
from apps.studios.models import Teacher

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
    """Sign-in. Unconfirmed accounts are refused only after a correct password, so the
    distinct message reveals nothing an attacker could not already prove."""

    def validate(self, attrs: dict[str, Any]) -> dict[str, str]:
        data = super().validate(attrs)
        if self.user is not None and not self.user.email_verified:
            raise EmailNotConfirmed("Confirm your email address before signing in.")
        return data


class PasswordResetConfirmSerializer(UidTokenSerializer):
    new_password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)


class PasswordChangeSerializer(serializers.Serializer[None]):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
