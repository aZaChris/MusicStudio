from rest_framework import viewsets

from apps.common.permissions import IsTeacherOrStudioOwner, role_scoped_queryset

from .models import Payment
from .serializers import PaymentSerializer


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [IsTeacherOrStudioOwner]
    filterset_fields = ["status", "student"]

    def get_queryset(self):
        return role_scoped_queryset(
            self.request.user,
            Payment.objects.select_related("student"),
            teacher_field="student__teacher",
            studio_field="student__teacher__studio",
            parent_field="student__parent_accounts",
        )
