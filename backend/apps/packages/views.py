from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.common.permissions import CanWriteTenantObject, IsTeacherOrStudioOwner
from apps.common.tenancy import get_tenant
from apps.payments.serializers import CheckoutSerializer
from apps.payments.services import start_checkout

from .models import Package
from .selectors import packages_for
from .serializers import PackageSerializer
from .services import create_package


class PackageViewSet(viewsets.ModelViewSet[Package]):
    serializer_class = PackageSerializer
    permission_classes = [IsTeacherOrStudioOwner, CanWriteTenantObject]
    filterset_fields = ["student"]

    def get_queryset(self) -> QuerySet[Package]:
        return packages_for(get_tenant(self.request))

    def perform_create(self, serializer: PackageSerializer) -> None:  # type: ignore[override]
        serializer.instance = create_package(**serializer.validated_data)

    @extend_schema(request=None, responses=CheckoutSerializer)
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def checkout(self, request: Request, pk: str | None = None) -> Response:
        """Online payment link (Stripe Checkout, test mode) for this package.

        Anyone who can see the package may ask — typically the parent who pays.
        Repeated calls return the same open attempt.
        """
        checkout = start_checkout(self.get_object(), user=request.user)
        return Response(CheckoutSerializer(checkout).data)
