"""Route dell'app students, montate sotto /api/v1/ da config/urls.py."""

from rest_framework.routers import DefaultRouter

from .views import StudentViewSet

router = DefaultRouter()
router.register("students", StudentViewSet, basename="student")

urlpatterns = router.urls
