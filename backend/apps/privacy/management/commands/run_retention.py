"""Run the retention rules now (the same job Celery beat runs every night)."""

from typing import Any

from django.core.management.base import BaseCommand

from apps.privacy import services


class Command(BaseCommand):
    help = "Anonymise or delete data past its retention period."

    def handle(self, *args: Any, **options: Any) -> None:
        for rule, count in services.run_retention().items():
            self.stdout.write(f"{rule}: {count}")
