from rest_framework import serializers

from apps.packages.serializers import PackageSerializer

from .models import ParentAccount, ParentStudentLink, Student


class StudentSerializer(serializers.ModelSerializer[Student]):
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
            "studio",
            "is_active",
            "active_package",
            "payment_status",
        ]
        read_only_fields = ["teacher", "studio"]

    def get_payment_status(self, obj: Student) -> str | None:
        # Annotated by students.selectors.students_for; one query only on single-object paths.
        if hasattr(obj, "latest_payment_status"):
            status: str | None = obj.latest_payment_status
            return status
        latest = obj.payments.order_by("-date", "-id").first()
        return latest.status if latest else None


class ParentAccountSerializer(serializers.ModelSerializer[ParentAccount]):
    class Meta:
        model = ParentAccount
        fields = ["id", "students"]


class ParentStudentLinkSerializer(serializers.ModelSerializer[ParentStudentLink]):
    class Meta:
        model = ParentStudentLink
        fields = ["id", "parent", "student"]
