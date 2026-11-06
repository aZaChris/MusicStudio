"""Celery tasks for payments. Thin wrappers: the logic and its idempotency live in services."""

from celery import shared_task
from django.db import InterfaceError, OperationalError

from . import services
from .gateway import PaymentsUnavailable


@shared_task(
    autoretry_for=(OperationalError, InterfaceError),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=8,
)
def process_webhook_event(event_pk: int) -> bool:
    """Apply a stored Stripe event. Running it twice is harmless (processed_at guard)."""
    return services.process_webhook_event(event_pk)


@shared_task(autoretry_for=(PaymentsUnavailable,), retry_backoff=True, max_retries=3)
def reconcile_open_checkouts() -> int:
    """Hourly: resolve attempts whose webhook never arrived (ADR-014)."""
    return services.reconcile_open_checkouts()
