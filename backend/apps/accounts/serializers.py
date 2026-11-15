"""Serializer di accesso, registrazione, profilo, reset password e MFA.

I docstring dei serializer finiscono in openapi.yaml (contratto in inglese): dove esistono restano
in inglese e il perché si scrive in commenti `#` (CLAUDE.md, "Gotchas").
Spiegazione: docs/learning/concetti/account-e-token-monouso.md e mfa-totp.md.
"""

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
    # Profilo insegnante dentro /me/: solo id, studio e se è titolare.
    class Meta:
        model = Teacher
        fields = ["id", "studio", "is_owner"]


class ParentProfileSerializer(serializers.ModelSerializer):
    # Profilo genitore dentro /me/: solo l'id.
    class Meta:
        model = ParentAccount
        fields = ["id"]


class MeSerializer(serializers.ModelSerializer):
    # Un utente ha al massimo un profilo; quello che manca è null. allow_null lo scrive nel
    # contratto.
    teacher = TeacherProfileSerializer(read_only=True, allow_null=True)
    parent_account = ParentProfileSerializer(read_only=True, allow_null=True)
    # Sempre presenti (anche vuoti): i client tipizzati non devono gestire `undefined`.
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
    # Il refresh token da mettere in lista nera (ADR-018).
    refresh = serializers.CharField(write_only=True)


class AcceptedResponseSerializer(serializers.Serializer[None]):
    """Uniform answer of the anonymous account endpoints (no account enumeration)."""

    # Risposta identica per account esistente e inesistente: chi sta a guardare non può scoprire
    # quali email sono registrate.

    detail = serializers.CharField()


class RegisterSerializer(serializers.Serializer[None]):
    # Registrazione di un titolare. `max_length=128` sulla password evita hash lunghissimi (DoS).
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
    """401 con un codice leggibile da una macchina: il portale può offrire di rinviare il link."""

    status_code = 401
    code = "email_not_confirmed"


class InvalidMfaCode(DomainError):
    """401 per token o codice errati al secondo passo; un solo corpo per ogni causa."""

    status_code = 401
    code = "invalid_mfa"


class LoginSerializer(TokenObtainPairSerializer):
    """Sign-in with a per-account lockout. Wrong, unknown and locked all answer with the
    same generic 401, so the response never says whether the address exists or is locked.
    Unconfirmed accounts are refused only after a correct password."""

    # Il docstring sopra è nel contratto: resta in inglese. In breve: password sbagliata, utente
    # sconosciuto e account bloccato danno tutti lo stesso 401, e per l'utente sconosciuto si fa
    # lo stesso lavoro di hashing, così nemmeno i tempi rivelano se l'email esiste (ADR-028).
    # L'ordine conta: prima il blocco, poi la password, poi la conferma email, poi la MFA.

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
    # Il link (uid e token) più la nuova password.
    new_password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)


class PasswordChangeSerializer(serializers.Serializer[None]):
    # Cambio da utente connesso: serve anche la password attuale.
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)


class LoginResponseSerializer(serializers.Serializer[None]):
    """Either the token pair, or `mfa_required` + `mfa_token` when a second step is due."""

    # Tutti i campi sono opzionali perché la risposta ha due forme (coppia di token oppure MFA).

    access = serializers.CharField(required=False)
    refresh = serializers.CharField(required=False)
    mfa_required = serializers.BooleanField(required=False)
    mfa_token = serializers.CharField(required=False)


class MfaVerifySerializer(serializers.Serializer[None]):
    # Secondo passo dell'accesso: il token firmato del primo passo più il codice.
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
    # Disattivare la MFA o rigenerare i codici chiede password e codice: un token rubato
    # da solo non basta.
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class MfaRecoveryCodesSerializer(serializers.Serializer[None]):
    recovery_codes = serializers.ListField(child=serializers.CharField())
