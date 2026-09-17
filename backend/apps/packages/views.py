from rest_framework import viewsets

from apps.common.permissions import IsTeacherOrStudioOwner, role_scoped_queryset

from .models import Package
from .serializers import PackageSerializer


class PackageViewSet(viewsets.ModelViewSet):
    serializer_class = PackageSerializer
    permission_classes = [IsTeacherOrStudioOwner]
    filterset_fields = ["student"]

    def get_queryset(self):
        return role_scoped_queryset(
            self.request.user,
            Package.objects.select_related("student"),
            teacher_field="student__teacher",
            studio_field="student__teacher__studio",
            parent_field="student__parent_accounts",
        )
