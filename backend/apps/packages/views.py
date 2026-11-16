"""Endpoint dei pacchetti di lezioni. Le view sono sottili: logica in services.py e selectors.py."""

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.common.permissions import CanWriteTenantObject, IsTeacherOrStudioOwner
from apps.common.tenancy import get_tenant
from apps.payments.selectors import with_can_pay_online
from apps.payments.serializers import CheckoutSerializer
from apps.payments.services import start_checkout

from .models import Package
from .selectors import packages_for
from .serializers import PackageSerializer
from .services import create_package


class PackageViewSet(viewsets.ModelViewSet[Package]):
    # CRUD dei pacchetti per insegnanti e titolari, più l'azione `checkout` aperta a chi vede il
    # pacchetto. Permessi: docs/learning/concetti/permessi-drf.md e ADR-011.
    # NB: commento e non docstring, perché drf-spectacular copia i docstring nel contratto
    # openapi.yaml (in inglese, letto anche dall'app mobile).
    serializer_class = PackageSerializer
    permission_classes = [IsTeacherOrStudioOwner, CanWriteTenantObject]
    filterset_fields = ["student"]

    def get_queryset(self) -> QuerySet[Package]:
        # Un id di un altro studio dà 404, non 403: non si rivela che esiste.
        return with_can_pay_online(packages_for(get_tenant(self.request)))

    def perform_create(self, serializer: PackageSerializer) -> None:  # type: ignore[override]
        # La creazione passa dal service, che imposta il saldo iniziale.
        serializer.instance = create_package(**serializer.validated_data)

    # `checkout` è fuori da IsTeacherOrStudioOwner di proposito: il genitore che paga deve
    # poterlo chiamare. La visibilità resta garantita da get_queryset (get_object dà 404 se non
    # vede il pacchetto). Dettagli: docs/learning/concetti/pagamenti-online-stripe.md, ADR-013.
    @extend_schema(request=None, responses=CheckoutSerializer)
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def checkout(self, request: Request, pk: str | None = None) -> Response:
        """Online payment link (Stripe Checkout, test mode) for this package.

        Anyone who can see the package may ask — typically the parent who pays. The payment goes
        to the studio's own Stripe account; 409 when the studio has no active account.
        Repeated calls return the same open attempt.
        """
        checkout = start_checkout(self.get_object(), user=request.user)
        return Response(CheckoutSerializer(checkout).data)
