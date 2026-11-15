"""Route dell'app packages, montate sotto /api/v1/ da config/urls.py."""

from rest_framework.routers import DefaultRouter

from .views import PackageViewSet

router = DefaultRouter()
router.register("packages", PackageViewSet, basename="package")

urlpatterns = router.urls
