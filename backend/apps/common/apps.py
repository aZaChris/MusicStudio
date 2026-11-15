"""Configurazione dell'app `common`: codice condiviso tra le app di dominio."""

from django.apps import AppConfig


class CommonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.common"
    label = "common"

    def ready(self) -> None:
        # Si collegano qui i segnali (cache dashboard, request id nei log e in Celery), perché
        # solo a questo punto tutte le app sono caricate. Import locale per lo stesso motivo.
        from . import logging, signals

        signals.connect()
        logging.connect_signals()
