from typing import Any

from rest_framework import serializers

from apps.common.tenancy import get_tenant
from apps.packages.serializers import PackageSerializer
from apps.studios.models import Teacher
from apps.studios.selectors import teachers_for_owner

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


class ReassignStudentSerializer(serializers.Serializer[None]):
    """Target teacher, validated against the owner's own studio only."""

    teacher = serializers.PrimaryKeyRelatedField(queryset=Teacher.objects.none())

    def get_fields(self) -> dict[str, serializers.Field[Any, Any, Any, Any]]:
        fields = super().get_fields()
        teacher_field = fields["teacher"]
        if isinstance(teacher_field, serializers.PrimaryKeyRelatedField):
            ctx = get_tenant(self.context.get("request"))
            teacher_field.queryset = teachers_for_owner(ctx)  # type: ignore[arg-type]
        return fields
