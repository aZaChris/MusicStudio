"""Celery reliability settings (US4, ADR-016) — pinned so they cannot silently regress."""

from django.conf import settings

from config.celery import app


def test_tasks_are_acknowledged_late_and_redelivered_on_worker_loss():
    assert settings.CELERY_TASK_ACKS_LATE is True
    assert settings.CELERY_TASK_REJECT_ON_WORKER_LOST is True
    assert settings.CELERY_WORKER_PREFETCH_MULTIPLIER == 1


def test_worker_children_are_recycled_before_the_container_limit():
    # 2 figli x soglia, in KB, devono stare sotto i 512 MB del container worker.
    assert settings.CELERY_WORKER_MAX_TASKS_PER_CHILD > 0
    assert 0 < settings.CELERY_WORKER_MAX_MEMORY_PER_CHILD * 2 < 512 * 1024


def test_every_task_has_a_time_limit_and_json_only():
    assert 0 < settings.CELERY_TASK_SOFT_TIME_LIMIT < settings.CELERY_TASK_TIME_LIMIT
    assert settings.CELERY_ACCEPT_CONTENT == ["json"]


def test_visibility_timeout_exceeds_the_longest_task():
    timeout = settings.CELERY_BROKER_TRANSPORT_OPTIONS["visibility_timeout"]
    assert timeout > settings.CELERY_TASK_TIME_LIMIT


def test_beat_schedules_reminders_reconciliation_accounts_token_purge_and_retention():
    tasks = {entry["task"] for entry in app.conf.beat_schedule.values()}
    assert tasks == {
        "apps.notifications.tasks.send_lesson_reminders",
        "apps.payments.tasks.reconcile_open_checkouts",
        "apps.payments.tasks.refresh_payment_accounts",  # fase 9
        "apps.payments.tasks.purge_old_webhook_events",  # fase 9
        "apps.accounts.tasks.purge_expired_tokens",
        "apps.privacy.tasks.run_retention",
    }
    app.loader.import_default_modules()
    assert tasks <= set(app.tasks)
