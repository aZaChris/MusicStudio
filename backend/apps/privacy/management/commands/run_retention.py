"""Esegue subito le regole di conservazione (lo stesso job che Celery beat lancia ogni notte)."""

from typing import Any

from django.core.management.base import BaseCommand

from apps.privacy import services


class Command(BaseCommand):
    # `help` è il testo che mostra `manage.py help run_retention`: resta in inglese come il resto
    # dell'interfaccia dei comandi.
    help = "Anonymise or delete data past its retention period."

    def handle(self, *args: Any, **options: Any) -> None:
        for rule, count in services.run_retention().items():
            self.stdout.write(f"{rule}: {count}")
