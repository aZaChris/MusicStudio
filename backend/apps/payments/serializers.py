from rest_framework import serializers

from apps.common.serializers import ScopedRelatedFieldsMixin

from .models import CheckoutSession, Payment


class PaymentSerializer(ScopedRelatedFieldsMixin, serializers.ModelSerializer[Payment]):
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
        read_only_fields = ["checkout"]


class CheckoutSerializer(serializers.Serializer[CheckoutSession]):
    """Response of POST /packages/{id}/checkout/: where to send the payer."""

    checkout_id = serializers.UUIDField(source="id")
    url = serializers.URLField()
    expires_at = serializers.DateTimeField()
