from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from . import health

urlpatterns = [
    path("health/live/", health.live, name="health-live"),
    path("health/ready/", health.ready, name="health-ready"),
    # Configurable path: a non-default admin URL cuts most automated login scanning.
    path(settings.ADMIN_URL, admin.site.urls),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.accounts.invitation_urls")),
    path("api/v1/", include("apps.studios.urls")),
    path("api/v1/", include("apps.students.urls")),
    path("api/v1/", include("apps.packages.urls")),
    path("api/v1/", include("apps.lessons.urls")),
    path("api/v1/", include("apps.payments.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
