from rest_framework import serializers

from .models import AuditEntry


class AuditEntrySerializer(serializers.ModelSerializer[AuditEntry]):
    actor_email = serializers.SerializerMethodField()

    class Meta:
        model = AuditEntry
        fields = [
            "id",
            "created_at",
            "action",
            "outcome",
            "actor_email",
            "target_type",
            "target_id",
            "metadata",
        ]

    def get_actor_email(self, obj: AuditEntry) -> str | None:
        return obj.actor.email if obj.actor else None


class AuditFilterSerializer(serializers.Serializer[None]):
    action = serializers.ChoiceField(choices=AuditEntry.Action.choices, required=False)
    since = serializers.DateTimeField(required=False)
    until = serializers.DateTimeField(required=False)
