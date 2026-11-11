from concurrent.futures import ThreadPoolExecutor

import pytest
from django.core.cache import cache
from django.db import connection
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import AuditEntry
from apps.common.factories import TeacherFactory

pytestmark = pytest.mark.django_db
URL = "/api/v1/auth/token/"


def attempt(email="t@example.com", password="wrong"):  # noqa: S107
    cache.clear()  # the per-IP throttle is a different layer; reset it between attempts
    return APIClient().post(URL, {"email": email, "password": password})


def make_user():
    return TeacherFactory(user__email="t@example.com").user


def test_sixth_attempt_is_refused_even_with_the_right_password():
    make_user()
    assert [attempt().status_code for _ in range(5)] == [401] * 5
    assert attempt(password="password123").status_code == 401


def test_unknown_locked_and_wrong_answer_with_the_same_body():
    make_user()
    wrong = attempt().json()
    unknown = attempt(email="nobody@example.com").json()
    for _ in range(4):
        attempt()
    locked = attempt(password="password123").json()
    assert wrong == unknown == locked


def test_lock_expires_and_doubles_next_time():
    user = make_user()
    for _ in range(5):
        attempt()
    user.refresh_from_db()
    first = user.locked_until - timezone.now()
    assert 14 * 60 < first.total_seconds() <= 15 * 60
    User.objects.filter(pk=user.pk).update(locked_until=timezone.now())
    for _ in range(5):
        attempt()
    user.refresh_from_db()
    second = user.locked_until - timezone.now()
    assert 29 * 60 < second.total_seconds() <= 30 * 60


def test_success_resets_counters():
    user = make_user()
    for _ in range(3):
        attempt()
    assert attempt(password="password123").status_code == 200
    user.refresh_from_db()
    assert (user.failed_logins, user.lock_level, user.locked_until) == (0, 0, None)


def test_lock_is_capped_at_24_hours():
    user = make_user()
    User.objects.filter(pk=user.pk).update(lock_level=9, failed_logins=4)
    attempt()
    user.refresh_from_db()
    assert (user.locked_until - timezone.now()).total_seconds() <= 24 * 3600


def test_audit_records_failure_lock_and_success():
    make_user()
    for _ in range(5):
        attempt()
    actions = list(AuditEntry.objects.order_by("id").values_list("action", flat=True))
    assert actions == ["login.failure"] * 4 + ["login.locked"]
    User.objects.update(locked_until=None)
    attempt(password="password123")
    assert AuditEntry.objects.filter(action="login.success").count() == 1


@pytest.mark.django_db(transaction=True)
def test_parallel_attempts_are_all_counted():
    user = make_user()

    def hit(_):
        try:
            return attempt().status_code
        finally:
            connection.close()

    with ThreadPoolExecutor(4) as pool:
        list(pool.map(hit, range(4)))
    user.refresh_from_db()
    assert user.failed_logins == 4
