from rest_framework import serializers

from apps.packages.serializers import PackageSerializer

from .models import ParentAccount, ParentStudentLink, Student


class StudentSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    active_package = PackageSerializer(read_only=True)
    payment_status = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            "id",
            "first_name",
            "last_name",
            "full_name",
            "instrument",
            "teacher",
            "is_active",
            "active_package",
            "payment_status",
        ]
        read_only_fields = ["teacher"]

    def get_payment_status(self, obj: Student) -> str | None:
        latest = obj.payments.order_by("-date").first()
        return latest.status if latest else None

    def create(self, validated_data):
        request = self.context["request"]
        validated_data.setdefault("teacher", request.user.teacher)
        return super().create(validated_data)


class ParentAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParentAccount
        fields = ["id", "students"]


class ParentStudentLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParentStudentLink
        fields = ["id", "parent", "student"]
