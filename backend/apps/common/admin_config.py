"""Configurazione dell'admin degli operatori, in un modulo suo (ADR-041).

Sta qui e non in apps.py: Django sceglie la configurazione predefinita di un'app cercando le
classi AppConfig del suo modulo apps.py, e due classi lì lo confonderebbero.
"""

from django.contrib import admin
from django.contrib.admin.apps import AdminConfig


class OperatorAdminConfig(AdminConfig):
    # Sostituisce "django.contrib.admin" in INSTALLED_APPS: `admin.site` diventa l'admin degli
    # operatori, così i `@admin.register` esistenti lo usano senza cambiare.
    default_site = "apps.common.admin_site.OperatorAdminSite"

    def ready(self) -> None:
        super().ready()  # autodiscover: qui tutti gli admin.py sono già stati importati
        from django.contrib.auth.models import Group
        from rest_framework_simplejwt.token_blacklist.models import (
            BlacklistedToken,
            OutstandingToken,
        )

        # Fuori dall'admin ciò che le librerie registrano da sole: i gruppi non li usiamo, e le
        # tabelle di simplejwt contengono i refresh token interi (sessioni: azione "Revoke").
        for model in (Group, OutstandingToken, BlacklistedToken):
            if admin.site.is_registered(model):
                admin.site.unregister(model)
