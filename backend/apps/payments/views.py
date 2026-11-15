"""Endpoint dei pagamenti. Le view sono sottili: la logica vive in services.py e selectors.py."""

from typing import cast

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.common.permissions import (
    CanWriteTenantObject,
    IsTeacherOrOwnerRole,
    IsTeacherOrStudioOwner,
)
from apps.common.tenancy import get_tenant

from .filters import PaymentFilter
from .models import Payment
from .selectors import payments_for
from .serializers import PaymentSerializer, ReversalSerializer, ReverseRequestSerializer
from .services import create_payment, delete_payment, reverse_payment, update_payment


class PaymentViewSet(viewsets.ModelViewSet[Payment]):
    # CRUD dei pagamenti, riservato a insegnanti e titolari dello studio.
    # Permessi: docs/learning/concetti/permessi-drf.md e ADR-011. I genitori non passano da qui:
    # il loro portale è in sola lettura.
    # NB: questo è un commento e non un docstring perché drf-spectacular copia i docstring
    # delle view nel contratto openapi.yaml (che resta in inglese e legge anche l'app mobile).
    serializer_class = PaymentSerializer
    permission_classes = [IsTeacherOrStudioOwner, CanWriteTenantObject]
    filterset_class = PaymentFilter

    def get_queryset(self) -> QuerySet[Payment]:
        # Anche per get/update/delete di un singolo id: un id di un altro studio dà 404,
        # non 403 (non si rivela nemmeno che esiste).
        return payments_for(get_tenant(self.request))

    def perform_create(self, serializer: PaymentSerializer) -> None:  # type: ignore[override]
        # La creazione passa dal service, che controlla il pacchetto e scrive l'audit log.
        serializer.instance = create_payment(actor=self.request.user, **serializer.validated_data)

    def perform_update(self, serializer: PaymentSerializer) -> None:  # type: ignore[override]
        instance = cast(Payment, serializer.instance)  # in aggiornamento è sempre valorizzato
        # Il service applica le transizioni di stato consentite (ALLOWED_TRANSITIONS).
        serializer.instance = update_payment(instance, **serializer.validated_data)

    def perform_destroy(self, instance: Payment) -> None:
        # Solo pending e overdue si cancellano; un pagamento pagato dà 409 (service). La
        # cancellazione lascia una voce nel registro delle azioni.
        delete_payment(instance, actor=self.request.user)

    # Storno di un pagamento pagato. Solo insegnanti e titolari: IsTeacherOrOwnerRole rifiuta i
    # genitori anche se possono leggere i pagamenti; CanWriteTenantObject limita il titolare al
    # proprio studio e l'insegnante ai propri studenti. Un id di un altro studio dà 404.
    @extend_schema(request=ReverseRequestSerializer, responses={201: ReversalSerializer})
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsTeacherOrOwnerRole, CanWriteTenantObject],
    )
    def reverse(self, request: Request, pk: str | None = None) -> Response:
        payment = self.get_object()
        body = ReverseRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        reversal = reverse_payment(
            payment, reason=body.validated_data["reason"], actor=request.user
        )
        return Response(
            ReversalSerializer(reversal, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )
