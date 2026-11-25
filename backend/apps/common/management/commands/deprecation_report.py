"""Promemoria delle deprecazioni: giorni rimasti e chiamate recenti (research R1b, ADR-040).

Lo lancia ogni settimana .github/workflows/deprecation-watch.yml. Esce con errore quando alla
rimozione mancano 30 giorni o meno (o la data è passata e il codice c'è ancora): il fallimento
del workflow arriva al proprietario con l'email di GitHub, senza bloccare le pull request.
"""

from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.common import deprecation

WARN_DAYS = 30


class Command(BaseCommand):
    help = "List deprecated endpoints; fail when a removal date is 30 days away or past."

    def handle(self, *args: Any, **options: Any) -> None:
        registry = deprecation.load_registry()
        if not registry:
            self.stdout.write("No active deprecations.")
            return
        today = deprecation._now().date()
        due = []
        for item in registry:
            left = (item.sunset - today).days
            # Le chiamate stanno nei log JSON; senza un archivio interrogabile non si inventano.
            # FUTURO (conteggio chiamate): leggerle dall'archivio dei log, se ne avremo uno.
            self.stdout.write(
                f"{item.endpoint}: removal {item.sunset} ({left} days left), "
                f"replacement {item.successor or '-'}, report {item.report}, "
                "calls in the last 30 days: unknown"
            )
            if left <= WARN_DAYS:
                due.append(item.endpoint)
        if due:
            raise CommandError(
                "Remove these endpoints or extend their date with a written reason: "
                + ", ".join(due)
            )
