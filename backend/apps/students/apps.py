"""Configurazione dell'app Django `students` (studenti e genitori)."""

from django.apps import AppConfig


class StudentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.students"
    label = "students"
