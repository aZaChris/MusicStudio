"""Serializer dei pagamenti: cosa entra e cosa esce dall'API."""

from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from apps.common.serializers import ScopedRelatedFieldsMixin
from apps.common.tenancy import get_tenant

from .models import CheckoutSession, Payment


class PaymentSerializer(ScopedRelatedFieldsMixin, serializers.ModelSerializer[Payment]):
    # Pagamento in lettura e scrittura. Il mixin limita i campi `student` e `package` agli
    # oggetti del proprio studio: senza, un insegnante potrebbe collegare un pagamento a uno
    # studente di un altro studio (docs/learning/concetti/isolamento-tenant-e-bola.md).
    # Commento e non docstring: i docstring dei serializer finiscono in openapi.yaml.

    student_name = serializers.CharField(source="student.full_name", read_only=True)
    # Fase 8: campi calcolati o riservati al personale (specs/008-cash-register-receipts).
    # `reversed` e `reversal_id` si ricavano dalla riga di storno già caricata dal selector.
    reversed = serializers.SerializerMethodField()
    reversal_id = serializers.SerializerMethodField()
    # Chi ha creato la riga e perché è stata stornata: li vede solo il personale dello studio.
    recorded_by = serializers.IntegerField(source="recorded_by_id", read_only=True, allow_null=True)
    reason = serializers.CharField(read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "student",
            "student_name",
            "package",
            "amount",
            "date",
            "method",
            "status",
            "checkout",
            "reversal_of",
            "reversed",
            "reversal_id",
            "recorded_by",
            "reason",
        ]
        # `checkout` lo imposta solo il webhook: dall'API non si può forgiare un pagamento
        # "online" a mano.
        read_only_fields = ["checkout", "reversal_of"]

    def _reversal(self, obj: Payment) -> Payment | None:
        # Il selector fa select_related("reversal"): niente query. Senza storno Django solleva
        # RelatedObjectDoesNotExist, che è un ObjectDoesNotExist.
        try:
            return obj.reversal
        except ObjectDoesNotExist:
            return None

    def get_reversed(self, obj: Payment) -> bool:
        return self._reversal(obj) is not None

    def get_reversal_id(self, obj: Payment) -> int | None:
        reversal = self._reversal(obj)
        return reversal.pk if reversal else None

    def validate_status(self, value: str) -> str:
        # Lo storno nasce solo dal service `reverse_payment`: dall'API non si forgia.
        if value == Payment.Status.REVERSAL:
            raise serializers.ValidationError(
                "A reversal can only be made with the reverse action."
            )
        return value

    def to_representation(self, instance: Payment) -> dict[str, Any]:
        data: dict[str, Any] = super().to_representation(instance)
        # Genitori e studenti adulti vedono i pagamenti ma non chi li ha registrati né il motivo
        # di uno storno (testo libero, cifrato nel database).
        ctx = get_tenant(self.context.get("request"))
        if not (ctx.is_owner or ctx.is_teacher):
            data.pop("reason", None)
            data.pop("recorded_by", None)
        return data


class ReverseRequestSerializer(serializers.Serializer[None]):
    # Corpo di POST /payments/{id}/reverse/: il motivo è obbligatorio e breve. È testo libero,
    # quindi nel database finisce cifrato (constitution X).
    reason = serializers.CharField(min_length=1, max_length=200, trim_whitespace=True)


class ReversalSerializer(PaymentSerializer):
    # Risposta di reverse: la riga di storno più `refund`, sempre false. Lo storno corregge il
    # registro, non restituisce denaro: il prodotto non muove soldi (FR-007).
    refund = serializers.SerializerMethodField()

    class Meta(PaymentSerializer.Meta):
        fields = [*PaymentSerializer.Meta.fields, "refund"]

    def get_refund(self, obj: Payment) -> bool:
        return False


class CheckoutSerializer(serializers.Serializer[CheckoutSession]):
    """Response of POST /packages/{id}/checkout/: where to send the payer."""

    # Risposta di POST /packages/{id}/checkout/: dove mandare chi deve pagare.
    # Il docstring resta in inglese perché entra nel contratto OpenAPI.

    checkout_id = serializers.UUIDField(source="id")
    url = serializers.URLField()
    expires_at = serializers.DateTimeField()
