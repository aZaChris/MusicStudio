from rest_framework import serializers

from .models import Lesson


class LessonSerializer(serializers.ModelSerializer):
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

    def create(self, validated_data):
        student = validated_data["student"]
        validated_data.setdefault("teacher", student.teacher)
        validated_data.setdefault("package", student.active_package)
        return super().create(validated_data)


class LessonCompleteSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default="")


class LessonCancelSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[Lesson.Status.CANCELLED, Lesson.Status.NO_SHOW])


class LowPackageStudentSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()


class DashboardSerializer(serializers.Serializer):
    week = LessonSerializer(many=True)
    upcoming = LessonSerializer(many=True)
    pending_payments_count = serializers.IntegerField()
    active_students_count = serializers.IntegerField()
    low_package_students = LowPackageStudentSerializer(many=True)
