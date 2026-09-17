from rest_framework import serializers

from .models import Package


class PackageSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    is_low = serializers.BooleanField(read_only=True)

    class Meta:
        model = Package
        fields = [
            "id",
            "student",
            "total_lessons",
            "lessons_remaining",
            "purchase_date",
            "expiry_date",
            "price",
            "status",
            "is_low",
        ]

    def create(self, validated_data):
        validated_data.setdefault("lessons_remaining", validated_data["total_lessons"])
        return super().create(validated_data)
