from typing import Any

from rest_framework import serializers

from apps.common.tenancy import get_tenant
from apps.packages.serializers import PackageSerializer
from apps.studios.models import Teacher
from apps.studios.selectors import teachers_for_owner

from .models import ParentAccount, ParentStudentLink, Student


class StudentSerializer(serializers.ModelSerializer[Student]):
    full_name = serializers.CharField(read_only=True)
    # A student may have no active package: the contract must say nullable (typed clients).
    active_package = PackageSerializer(read_only=True, allow_null=True)
    payment_status = serializers.SerializerMethodField()
    # True once the adult student accepted an invitation; no extra query (user_id is local).
    has_account = serializers.SerializerMethodField()

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
            "is_adult",
            "has_account",
            "active_package",
            "payment_status",
        ]
        read_only_fields = ["teacher", "studio"]

    def get_has_account(self, obj: Student) -> bool:
        return obj.user_id is not None

    def validate_is_adult(self, value: bool) -> bool:
        # Only adults may have an account of their own (constitution X): taking the flag away
        # from a student who already signed in would leave a minor with an account.
        if not value and self.instance is not None and self.instance.user_id is not None:
            raise serializers.ValidationError("This student already has an account.")
        return value

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
