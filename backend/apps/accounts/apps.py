"""Configurazione dell'app Django `accounts` (utenti, sessioni, inviti, MFA)."""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    label = "accounts"
