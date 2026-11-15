"""Serializer delle lezioni e della dashboard.

I docstring di serializer e view finiscono in openapi.yaml: qui si usano commenti `#`
(vedi CLAUDE.md, "Gotchas").
"""

from typing import Any

from rest_framework import serializers

from apps.common.serializers import ScopedRelatedFieldsMixin

from .models import Lesson
from .services import CANCEL_STATUSES


class LessonSerializer(ScopedRelatedFieldsMixin, serializers.ModelSerializer[Lesson]):
    # Il mixin limita studente e pacchetto a quelli del proprio studio
    # (docs/learning/concetti/isolamento-tenant-e-bola.md).
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    # Mantenuto per compatibilità con l'API; il database salva end_time (ADR-009).
    # Limiti: da 5 minuti a 8 ore.
    duration_minutes = serializers.IntegerField(min_value=5, max_value=480, default=30)

    class Meta:
        model = Lesson
        fields = [
            "id",
            "student",
            "student_name",
            "teacher",
            "package",
            "start_time",
            "duration_minutes",
            "end_time",
            "status",
            "notes",
        ]
        # L'insegnante lo decide il service, lo stato cambia solo con complete/cancel e la
        # fine si calcola da inizio e durata: nessuno dei tre si può scrivere a mano.
        read_only_fields = ["teacher", "status", "end_time"]


class LessonCompleteSerializer(serializers.Serializer[None]):
    # Corpo di POST /lessons/{id}/complete/: una nota facoltativa.
    note = serializers.CharField(required=False, allow_blank=True, default="")


class LessonCancelSerializer(serializers.Serializer[None]):
    # Corpo di POST /lessons/{id}/cancel/: "cancelled" oppure "no_show".
    status = serializers.ChoiceField(choices=list(CANCEL_STATUSES))


class LowPackageStudentSerializer(serializers.Serializer[None]):
    # Studente con pacchetto in esaurimento, mostrato nella dashboard.
    id = serializers.IntegerField()
    full_name = serializers.CharField()


class DashboardSerializer(serializers.Serializer[dict[str, Any]]):
    # Risposta della dashboard dell'insegnante (cache: vedi cache.py).
    week = LessonSerializer(many=True)
    upcoming = LessonSerializer(many=True)
    pending_payments_count = serializers.IntegerField()
    active_students_count = serializers.IntegerField()
    low_package_students = LowPackageStudentSerializer(many=True)
