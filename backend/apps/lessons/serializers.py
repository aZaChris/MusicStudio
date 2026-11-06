from typing import Any

from rest_framework import serializers

from apps.common.serializers import ScopedRelatedFieldsMixin

from .models import Lesson
from .services import CANCEL_STATUSES


class LessonSerializer(ScopedRelatedFieldsMixin, serializers.ModelSerializer[Lesson]):
    student_name = serializers.CharField(source="student.full_name", read_only=True)

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
            "status",
            "notes",
        ]
        read_only_fields = ["teacher", "status"]


class LessonCompleteSerializer(serializers.Serializer[None]):
    note = serializers.CharField(required=False, allow_blank=True, default="")


class LessonCancelSerializer(serializers.Serializer[None]):
    status = serializers.ChoiceField(choices=list(CANCEL_STATUSES))


class LowPackageStudentSerializer(serializers.Serializer[None]):
    id = serializers.IntegerField()
    full_name = serializers.CharField()


class DashboardSerializer(serializers.Serializer[dict[str, Any]]):
    week = LessonSerializer(many=True)
    upcoming = LessonSerializer(many=True)
    pending_payments_count = serializers.IntegerField()
    active_students_count = serializers.IntegerField()
    low_package_students = LowPackageStudentSerializer(many=True)
