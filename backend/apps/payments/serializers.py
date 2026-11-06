from rest_framework import serializers

from apps.common.serializers import ScopedRelatedFieldsMixin

from .models import Payment


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
        ]
