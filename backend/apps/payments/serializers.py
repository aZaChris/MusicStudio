from rest_framework import serializers

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
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

    def validate(self, attrs):
        student = attrs.get("student", getattr(self.instance, "student", None))
        package = attrs.get("package", getattr(self.instance, "package", None))
        if package is not None and package.student_id != student.id:
            raise serializers.ValidationError(
                {"package": "Package must belong to the same student as the payment."}
            )
        return attrs
