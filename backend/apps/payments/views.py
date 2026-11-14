"""Endpoint dei pagamenti. Le view sono sottili: la logica vive in services.py e selectors.py."""

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
    # CRUD dei pagamenti, riservato a insegnanti e titolari dello studio.
    # Permessi: docs/learning/concetti/permessi-drf.md e ADR-011. I genitori non passano da qui:
    # il loro portale è in sola lettura.
    # NB: questo è un commento e non un docstring perché drf-spectacular copia i docstring
    # delle view nel contratto openapi.yaml (che resta in inglese e legge anche l'app mobile).
    serializer_class = PaymentSerializer
    permission_classes = [IsTeacherOrStudioOwner, CanWriteTenantObject]
    filterset_fields = ["status", "student"]

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
