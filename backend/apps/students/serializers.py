"""Serializer di studenti, genitori e collegamenti. I docstring finiscono in openapi.yaml:
qui si usano commenti `#` (CLAUDE.md, "Gotchas")."""

from typing import Any

from rest_framework import serializers

from apps.common.tenancy import get_tenant
from apps.packages.serializers import PackageSerializer
from apps.studios.models import Teacher
from apps.studios.selectors import teachers_for_owner

from .models import ParentAccount, ParentStudentLink, Student


class StudentSerializer(serializers.ModelSerializer[Student]):
    full_name = serializers.CharField(read_only=True)
    # Uno studente può non avere un pacchetto attivo: il contratto deve dire nullable
    # (client tipizzati).
    active_package = PackageSerializer(read_only=True, allow_null=True)
    payment_status = serializers.SerializerMethodField()
    # True quando lo studente adulto ha accettato l'invito; nessuna query in più (user_id è
    # già nella riga).
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
        # Insegnante e studio non si scelgono dal client: li imposta il service dal contesto.
        read_only_fields = ["teacher", "studio"]

    def get_has_account(self, obj: Student) -> bool:
        return obj.user_id is not None

    def validate_is_adult(self, value: bool) -> bool:
        # Solo gli adulti possono avere un account proprio (constitution X): togliere il flag a chi
        # ha già un account lascerebbe un minore con un account.
        if not value and self.instance is not None and self.instance.user_id is not None:
            raise serializers.ValidationError("This student already has an account.")
        return value

    def get_payment_status(self, obj: Student) -> str | None:
        # Annotato da students.selectors.students_for; una query sola solo sui percorsi a oggetto
        # singolo (creazione, modifica).
        if hasattr(obj, "latest_payment_status"):
            status: str | None = obj.latest_payment_status
            return status
        # Come nel selector: gli storni e i pagamenti stornati non contano per lo stato.
        latest = (
            obj.payments.filter(reversal__isnull=True)
            .exclude(status="reversal")
            .order_by("-date", "-id")
            .first()
        )
        return latest.status if latest else None


class ParentAccountSerializer(serializers.ModelSerializer[ParentAccount]):
    # Il genitore è un account con accesso in sola lettura ai propri figli (ADR-011).
    class Meta:
        model = ParentAccount
        fields = ["id", "students"]


class ParentStudentLinkSerializer(serializers.ModelSerializer[ParentStudentLink]):
    # Il collegamento genitore-studente è una tabella vera, con vincolo di unicità sulla coppia.
    class Meta:
        model = ParentStudentLink
        fields = ["id", "parent", "student"]


class ReassignStudentSerializer(serializers.Serializer[None]):
    """Target teacher, validated against the owner's own studio only."""

    # Il docstring sopra è nel contratto: resta in inglese. L'insegnante di destinazione si
    # sceglie solo tra quelli dello studio del titolare (queryset deciso in get_fields).
    teacher = serializers.PrimaryKeyRelatedField(queryset=Teacher.objects.none())

    def get_fields(self) -> dict[str, serializers.Field[Any, Any, Any, Any]]:
        fields = super().get_fields()
        # Il queryset dipende dall'utente che chiama, quindi si imposta qui e non nella classe.
        teacher_field = fields["teacher"]
        if isinstance(teacher_field, serializers.PrimaryKeyRelatedField):
            ctx = get_tenant(self.context.get("request"))
            teacher_field.queryset = teachers_for_owner(ctx)  # type: ignore[arg-type]
        return fields
