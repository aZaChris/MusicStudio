"""Serializer dei pacchetti. I docstring di serializer e view finiscono in openapi.yaml:
qui si usano commenti `#` (CLAUDE.md, "Gotchas")."""

from rest_framework import serializers

from apps.common.serializers import ScopedRelatedFieldsMixin

from .models import Package


class PackageSerializer(ScopedRelatedFieldsMixin, serializers.ModelSerializer[Package]):
    # `ScopedRelatedFieldsMixin`: lo studente indicato deve essere visibile a chi scrive, altrimenti
    # un insegnante potrebbe agganciare un pacchetto a uno studente di un altro studio (BOLA).
    # `status` e `is_low` sono calcolati dal modello, non salvati: mai incoerenti con la data.
    status = serializers.CharField(read_only=True)
    is_low = serializers.BooleanField(read_only=True)
    # Fase 9: il conto Stripe dello studio è attivo e il pacchetto è ancora da pagare. Dal queryset
    # (nessuna query per riga); falso se l'oggetto non arriva da un elenco.
    can_pay_online = serializers.BooleanField(read_only=True, default=False)

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
            "can_pay_online",
        ]
        # Il saldo lo muovono solo i service (vedi services.create_package).
        read_only_fields = ["lessons_remaining"]
