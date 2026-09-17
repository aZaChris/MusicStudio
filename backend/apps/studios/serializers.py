from rest_framework import serializers

from .models import Studio, Teacher


class TeacherSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Teacher
        fields = ["id", "email", "is_owner"]


class StudioSerializer(serializers.ModelSerializer):
    teacher_count = serializers.IntegerField(source="teachers.count", read_only=True)

    class Meta:
        model = Studio
        fields = ["id", "name", "teacher_count"]
