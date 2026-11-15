"""Route dell'app audit, montate sotto /api/v1/audit/ da config/urls.py."""

from django.urls import path

from .views import AuditListView

urlpatterns = [path("", AuditListView.as_view(), name="audit-list")]
