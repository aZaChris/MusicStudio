"""Gli eventi di Stripe elaborati si cancellano dopo 90 giorni (fase 9, ADR-039)."""

import datetime

import pytest
from django.utils import timezone

from apps.payments import tasks
from apps.payments.models import WebhookEvent

pytestmark = pytest.mark.django_db


def _event(name: str, *, processed_days_ago: int | None) -> WebhookEvent:
    processed = (
        None
        if processed_days_ago is None
        else timezone.now() - datetime.timedelta(days=processed_days_ago)
    )
    return WebhookEvent.objects.create(
        stripe_event_id=name, type="refund.updated", payload={}, processed_at=processed
    )


def test_old_processed_events_go_and_recent_or_unprocessed_ones_stay():
    _event("old", processed_days_ago=91)
    _event("edge", processed_days_ago=89)
    _event("recent", processed_days_ago=1)
    _event("stuck", processed_days_ago=None)  # mai elaborato: lo cerca ancora qualcuno
    WebhookEvent.objects.filter(stripe_event_id="stuck").update(
        received_at=timezone.now() - datetime.timedelta(days=400)
    )

    deleted = tasks.purge_old_webhook_events()

    assert deleted == 1
    assert set(WebhookEvent.objects.values_list("stripe_event_id", flat=True)) == {
        "edge",
        "recent",
        "stuck",
    }


def test_running_it_twice_deletes_nothing_more():
    _event("old", processed_days_ago=200)

    assert tasks.purge_old_webhook_events() == 1
    assert tasks.purge_old_webhook_events() == 0
