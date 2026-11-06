from typing import Any

from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import MeSerializer


class ThrottledTokenObtainPairView(TokenObtainPairView):
    """Login with a tight per-client rate (THROTTLE_LOGIN) against password guessing."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


class MeView(RetrieveAPIView[Any]):
    serializer_class = MeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self) -> Any:
        return self.request.user
