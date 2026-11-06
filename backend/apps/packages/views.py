from django.db.models import QuerySet
from rest_framework import viewsets

from apps.common.permissions import IsTeacherOrStudioOwner

from .models import Package
from .selectors import packages_for
from .serializers import PackageSerializer
from .services import create_package


class PackageViewSet(viewsets.ModelViewSet[Package]):
    serializer_class = PackageSerializer
    permission_classes = [IsTeacherOrStudioOwner]
    filterset_fields = ["student"]

    def get_queryset(self) -> QuerySet[Package]:
        return packages_for(self.request.user)

    def perform_create(self, serializer: PackageSerializer) -> None:  # type: ignore[override]
        serializer.instance = create_package(**serializer.validated_data)
