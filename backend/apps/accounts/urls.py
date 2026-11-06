from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import MeView, ThrottledTokenObtainPairView

urlpatterns = [
    path("token/", ThrottledTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", MeView.as_view(), name="me"),
]
