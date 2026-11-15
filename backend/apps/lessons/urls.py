"""Route dell'app lessons, montate sotto /api/v1/ da config/urls.py."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DashboardView, LessonViewSet

router = DefaultRouter()
router.register("lessons", LessonViewSet, basename="lesson")

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("", include(router.urls)),
]
