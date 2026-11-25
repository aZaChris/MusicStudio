"""Endpoint di accesso, sessione, registrazione, reset password e MFA.

I docstring delle view finiscono in openapi.yaml (contratto in inglese): dove esistono restano
in inglese, il perché si scrive in commenti `#`. Le view sono sottili: la logica sta in
services.py e mfa.py. Spiegazione: docs/learning/concetti/account-e-token-monouso.md,
revoca-token-jwt.md e mfa-totp.md.
"""

from typing import Any

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.common.throttling import ScopedRateThrottle

from . import mfa, services
from .serializers import (
    AcceptedResponseSerializer,
    EmailOnlySerializer,
    InvalidMfaCode,
    LoginResponseSerializer,
    LoginSerializer,
    LogoutSerializer,
    MeSerializer,
    MfaCodeSerializer,
    MfaPasswordCodeSerializer,
    MfaRecoveryCodesSerializer,
    MfaSetupSerializer,
    MfaStatusSerializer,
    MfaVerifySerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    RegisterSerializer,
    UidTokenSerializer,
)

# Risposta unica degli endpoint anonimi: uguale per account esistente e inesistente.
CHECK_EMAIL = {"detail": "check_email"}


class ThrottledTokenObtainPairView(TokenObtainPairView):
    """Login with a tight per-client rate (THROTTLE_LOGIN) against password guessing."""

    # Il limite per client si somma al blocco per singolo account (services.register_login_failure).

    serializer_class = LoginSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @extend_schema(responses={200: LoginResponseSerializer})
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().post(request, *args, **kwargs)


class AnonymousAccountView(APIView):
    """Base for anonymous account endpoints: no JWT parsing, a per-client rate."""

    # `authentication_classes = []`: un token scaduto in un'intestazione non deve far fallire con
    # 401 una richiesta che non ne ha bisogno.

    authentication_classes: list[type] = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]


class RegisterView(AnonymousAccountView):
    # Risponde sempre 202: non dice se l'email era già registrata (services.register_owner).
    throttle_scope = "register"

    @extend_schema(request=RegisterSerializer, responses={202: AcceptedResponseSerializer})
    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        services.register_owner(
            email=data["email"],
            password=data["password"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            studio_name=data["studio_name"],
            language=data["preferred_language"],
        )
        return Response(CHECK_EMAIL, status=status.HTTP_202_ACCEPTED)


class ConfirmEmailView(AnonymousAccountView):
    # Conferma l'indirizzo con il link ricevuto (uid e token firmato, nessuna tabella di token).
    throttle_scope = "register"

    @extend_schema(request=UidTokenSerializer, responses={200: AcceptedResponseSerializer})
    def post(self, request: Request) -> Response:
        serializer = UidTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.confirm_email(serializer.validated_data["uid"], serializer.validated_data["token"])
        return Response({"detail": "confirmed"})


class ResendConfirmationView(AnonymousAccountView):
    # Rinvia il link di conferma; risposta uniforme anche per email sconosciute.
    throttle_scope = "register"

    @extend_schema(request=EmailOnlySerializer, responses={202: AcceptedResponseSerializer})
    def post(self, request: Request) -> Response:
        serializer = EmailOnlySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.resend_confirmation(serializer.validated_data["email"])
        return Response(CHECK_EMAIL, status=status.HTTP_202_ACCEPTED)


class MeView(RetrieveAPIView[Any]):
    # Profilo di chi chiama: l'oggetto è sempre request.user, quindi non esiste un id da forzare.
    serializer_class = MeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self) -> Any:
        return self.request.user


class LogoutView(APIView):
    """End this device's session: its refresh token can no longer be used (ADR-018)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=LogoutSerializer,
        responses={205: OpenApiResponse(description="Session ended (also if already ended)")},
    )
    def post(self, request: Request) -> Response:
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.logout(request.user, serializer.validated_data["refresh"])  # type: ignore[arg-type]
        return Response(status=status.HTTP_205_RESET_CONTENT)


class PasswordResetRequestView(AnonymousAccountView):
    # Chiede il link di reset; risposta uniforme (research R3).
    throttle_scope = "password_reset"

    @extend_schema(request=EmailOnlySerializer, responses={202: AcceptedResponseSerializer})
    def post(self, request: Request) -> Response:
        serializer = EmailOnlySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.request_password_reset(serializer.validated_data["email"])
        return Response(CHECK_EMAIL, status=status.HTTP_202_ACCEPTED)


class PasswordResetConfirmView(AnonymousAccountView):
    # Imposta la nuova password con il link; chiude tutte le sessioni dell'account.
    throttle_scope = "password_reset"

    @extend_schema(
        request=PasswordResetConfirmSerializer, responses={200: AcceptedResponseSerializer}
    )
    def post(self, request: Request) -> Response:
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        services.reset_password(data["uid"], data["token"], data["new_password"])
        return Response({"detail": "password_changed"})


class PasswordChangeView(APIView):
    """Change the password; every session of the account ends (sign in again)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=PasswordChangeSerializer, responses={200: AcceptedResponseSerializer})
    def post(self, request: Request) -> Response:
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        services.change_password(
            request.user,  # type: ignore[arg-type]
            data["current_password"],
            data["new_password"],
        )
        return Response({"detail": "password_changed"})


class MfaVerifyView(AnonymousAccountView):
    """Second step of sign-in. Every failure answers the same 401."""

    # Anonima perché a questo punto il client ha solo l'mfa_token firmato, non ancora i JWT.

    throttle_scope = "mfa"

    @extend_schema(request=MfaVerifySerializer, responses={200: LoginResponseSerializer})
    def post(self, request: Request) -> Response:
        serializer = MfaVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = mfa.complete_login(
            serializer.validated_data["mfa_token"], serializer.validated_data["code"]
        )
        if user is None:
            raise InvalidMfaCode("Invalid code.")
        refresh = RefreshToken.for_user(user)
        return Response({"refresh": str(refresh), "access": str(refresh.access_token)})


class CanUseMfa(BasePermission):
    """Titolari, insegnanti e operatori; genitori e studenti accedono con la sola password."""

    def has_permission(self, request: Request, view: Any) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and mfa.is_eligible(user))


class MfaStatusView(APIView):
    # Se la MFA è attiva e quanti codici di recupero restano.
    permission_classes = [CanUseMfa]

    @extend_schema(responses={200: MfaStatusSerializer})
    def get(self, request: Request) -> Response:
        return Response(mfa.status(request.user))  # type: ignore[arg-type]


class MfaSetupView(APIView):
    # Inizia l'attivazione: restituisce il segreto e l'URI per il QR. Si attiva solo alla conferma.
    permission_classes = [CanUseMfa]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "mfa"

    @extend_schema(request=None, responses={201: MfaSetupSerializer})
    def post(self, request: Request) -> Response:
        secret, uri = mfa.begin_setup(request.user)  # type: ignore[arg-type]
        return Response({"secret": secret, "otpauth_uri": uri}, status=status.HTTP_201_CREATED)


class MfaConfirmView(APIView):
    # Conferma con un primo codice; restituisce i codici di recupero (si vedono una volta sola).
    permission_classes = [CanUseMfa]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "mfa"

    @extend_schema(request=MfaCodeSerializer, responses={200: MfaRecoveryCodesSerializer})
    def post(self, request: Request) -> Response:
        serializer = MfaCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        codes = mfa.confirm_setup(request.user, serializer.validated_data["code"])  # type: ignore[arg-type]
        return Response({"recovery_codes": codes})


class MfaDisableView(APIView):
    # Disattiva la MFA: richiede password e un codice valido.
    permission_classes = [CanUseMfa]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "mfa"

    @extend_schema(
        request=MfaPasswordCodeSerializer, responses={204: OpenApiResponse(description="Disabled")}
    )
    def post(self, request: Request) -> Response:
        serializer = MfaPasswordCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        mfa.disable(request.user, data["password"], data["code"])  # type: ignore[arg-type]
        return Response(status=status.HTTP_204_NO_CONTENT)


class MfaRecoveryCodesView(APIView):
    # Rigenera i codici di recupero (i vecchi smettono di valere): password e codice richiesti.
    permission_classes = [CanUseMfa]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "mfa"

    @extend_schema(request=MfaPasswordCodeSerializer, responses={200: MfaRecoveryCodesSerializer})
    def post(self, request: Request) -> Response:
        serializer = MfaPasswordCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        codes = mfa.regenerate_recovery_codes(request.user, data["password"], data["code"])  # type: ignore[arg-type]
        return Response({"recovery_codes": codes})
