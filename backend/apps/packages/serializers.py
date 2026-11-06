from rest_framework import serializers

from apps.common.serializers import ScopedRelatedFieldsMixin

from .models import Package


class PackageSerializer(ScopedRelatedFieldsMixin, serializers.ModelSerializer[Package]):
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
        read_only_fields = ["lessons_remaining"]
