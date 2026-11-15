"""Serializer di studio e insegnanti. I docstring finiscono in openapi.yaml: qui si usa `#`."""

from rest_framework import serializers

from .models import Studio, Teacher


class TeacherSerializer(serializers.ModelSerializer[Teacher]):
    # Dell'insegnante si espongono solo id, email e se è titolare: nient'altro dell'utente.
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Teacher
        fields = ["id", "email", "is_owner"]


class StudioSerializer(serializers.ModelSerializer[Studio]):
    # Calcolato da studios.selectors.studio_for_owner (annotate), non è una colonna.
    teacher_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Studio
        fields = ["id", "name", "teacher_count"]
