from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import ConsentRecord


class PasswordSerializer(serializers.Serializer[None]):
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class ConsentSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = ConsentRecord
        fields = ["id", "notice_version", "given_at", "withdrawn_at", "children"]

    @extend_schema_field(
        serializers.ListField(child=serializers.DictField(child=serializers.CharField()))
    )
    def get_children(self, obj: ConsentRecord) -> list[dict[str, object]]:
        return [{"id": s.pk, "name": s.full_name} for s in obj.students.all()]


class AcceptedSerializer(serializers.Serializer[None]):
    detail = serializers.CharField()
