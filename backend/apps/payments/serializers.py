"""Serializer dei pagamenti: cosa entra e cosa esce dall'API."""

from rest_framework import serializers

from apps.common.serializers import ScopedRelatedFieldsMixin

from .models import CheckoutSession, Payment


class PaymentSerializer(ScopedRelatedFieldsMixin, serializers.ModelSerializer[Payment]):
    # Pagamento in lettura e scrittura. Il mixin limita i campi `student` e `package` agli
    # oggetti del proprio studio: senza, un insegnante potrebbe collegare un pagamento a uno
    # studente di un altro studio (docs/learning/concetti/isolamento-tenant-e-bola.md).
    # Commento e non docstring: i docstring dei serializer finiscono in openapi.yaml.

    student_name = serializers.CharField(source="student.full_name", read_only=True)

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
        ]
        # `checkout` lo imposta solo il webhook: dall'API non si può forgiare un pagamento
        # "online" a mano.
        read_only_fields = ["checkout"]


class CheckoutSerializer(serializers.Serializer[CheckoutSession]):
    """Response of POST /packages/{id}/checkout/: where to send the payer."""

    # Risposta di POST /packages/{id}/checkout/: dove mandare chi deve pagare.
    # Il docstring resta in inglese perché entra nel contratto OpenAPI.

    checkout_id = serializers.UUIDField(source="id")
    url = serializers.URLField()
    expires_at = serializers.DateTimeField()
