from rest_framework import serializers

from apps.students.models import ParentAccount
from apps.studios.models import Teacher

from .models import User


class TeacherProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Teacher
        fields = ["id", "studio", "is_owner"]


class ParentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParentAccount
        fields = ["id"]


class MeSerializer(serializers.ModelSerializer):
    teacher = TeacherProfileSerializer(read_only=True)
    parent_account = ParentProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "role",
            "preferred_language",
            "teacher",
            "parent_account",
        ]
