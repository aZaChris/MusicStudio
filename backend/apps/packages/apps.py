"""Configurazione dell'app Django `packages`."""

from django.apps import AppConfig


class PackagesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.packages"
    label = "packages"
