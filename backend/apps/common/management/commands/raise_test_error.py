import logging
from typing import Any

import sentry_sdk
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Send a test error to Sentry and the logs, to check the setup after a deploy."

    def handle(self, *args: Any, **options: Any) -> None:
        if sentry_sdk.get_client().is_active():
            try:
                raise RuntimeError("MusicStudio test error (raise_test_error)")
            except RuntimeError as exc:
                event_id = sentry_sdk.capture_exception(exc)
                logger.exception("Test error sent to Sentry, event %s", event_id)
            sentry_sdk.flush(timeout=5)
            self.stdout.write(f"Sent. Look for event {event_id} in Sentry.")
        else:
            logger.error("Test error: Sentry is not configured (SENTRY_DSN empty)")
            self.stdout.write("Sentry is not configured; the error went to the logs only.")
