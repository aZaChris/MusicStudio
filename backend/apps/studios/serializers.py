from rest_framework import serializers

from .models import Studio, Teacher


class TeacherSerializer(serializers.ModelSerializer[Teacher]):
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Teacher
        fields = ["id", "email", "is_owner"]


class StudioSerializer(serializers.ModelSerializer[Studio]):
    # Annotated by studios.selectors.studio_for_owner.
    teacher_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Studio
        fields = ["id", "name", "teacher_count"]
