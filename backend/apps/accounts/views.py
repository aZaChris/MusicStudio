from typing import Any

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.common.throttling import ScopedRateThrottle

from . import services
from .serializers import LogoutSerializer, MeSerializer


class ThrottledTokenObtainPairView(TokenObtainPairView):
    """Login with a tight per-client rate (THROTTLE_LOGIN) against password guessing."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


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
