"""Serializer di esportazione, consensi e conferma password. I docstring finiscono in
openapi.yaml: qui si usano commenti `#` (CLAUDE.md, "Gotchas")."""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import ConsentRecord


class PasswordSerializer(serializers.Serializer[None]):
    # Cancellare un account o ritirare un consenso chiede la password: un token rubato da solo
    # non basta per distruggere i dati. `write_only` e niente trim: la password non si altera.
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class ConsentSerializer(serializers.ModelSerializer):
    # Dei figli si mostrano id e nome, non altro.
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
