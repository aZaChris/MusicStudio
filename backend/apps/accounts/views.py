from typing import Any

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.common.throttling import ScopedRateThrottle

from . import services
from .serializers import (
    AcceptedResponseSerializer,
    EmailOnlySerializer,
    LoginSerializer,
    LogoutSerializer,
    MeSerializer,
    RegisterSerializer,
    UidTokenSerializer,
)

CHECK_EMAIL = {"detail": "check_email"}


class ThrottledTokenObtainPairView(TokenObtainPairView):
    """Login with a tight per-client rate (THROTTLE_LOGIN) against password guessing."""

    serializer_class = LoginSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


class AnonymousAccountView(APIView):
    """Base for anonymous account endpoints: no JWT parsing, a per-client rate."""

    authentication_classes: list[type] = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]


class RegisterView(AnonymousAccountView):
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
    throttle_scope = "register"

    @extend_schema(request=UidTokenSerializer, responses={200: AcceptedResponseSerializer})
    def post(self, request: Request) -> Response:
        serializer = UidTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.confirm_email(serializer.validated_data["uid"], serializer.validated_data["token"])
        return Response({"detail": "confirmed"})


class ResendConfirmationView(AnonymousAccountView):
    throttle_scope = "register"

    @extend_schema(request=EmailOnlySerializer, responses={202: AcceptedResponseSerializer})
    def post(self, request: Request) -> Response:
        serializer = EmailOnlySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.resend_confirmation(serializer.validated_data["email"])
        return Response(CHECK_EMAIL, status=status.HTTP_202_ACCEPTED)


class MeView(RetrieveAPIView[Any]):
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
