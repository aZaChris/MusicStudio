"""Route dell'app studios, montate sotto /api/v1/ da config/urls.py."""

from django.urls import path

from .views import MyStudioView, StudioTeachersView

urlpatterns = [
    path("studio/", MyStudioView.as_view(), name="my-studio"),
    path("studio/teachers/", StudioTeachersView.as_view(), name="studio-teachers"),
]
