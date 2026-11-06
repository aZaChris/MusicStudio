from typing import cast

from django.db.models import QuerySet
from rest_framework import viewsets

from apps.common.permissions import CanWriteTenantObject, IsTeacherOrStudioOwner
from apps.common.tenancy import get_tenant

from .models import Payment
from .selectors import payments_for
from .serializers import PaymentSerializer
from .services import create_payment, update_payment


class PaymentViewSet(viewsets.ModelViewSet[Payment]):
    serializer_class = PaymentSerializer
    permission_classes = [IsTeacherOrStudioOwner, CanWriteTenantObject]
    filterset_fields = ["status", "student"]

    def get_queryset(self) -> QuerySet[Payment]:
        return payments_for(get_tenant(self.request))

    def perform_create(self, serializer: PaymentSerializer) -> None:  # type: ignore[override]
        serializer.instance = create_payment(**serializer.validated_data)

    def perform_update(self, serializer: PaymentSerializer) -> None:  # type: ignore[override]
        instance = cast(Payment, serializer.instance)  # always set on update
        serializer.instance = update_payment(instance, **serializer.validated_data)
