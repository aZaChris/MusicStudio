"""Password reset and change (US2): uniform, single use, sessions end, lock cleared."""

import re
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient

from apps.audit.models import AuditEntry
from apps.common.factories import UserFactory
from apps.common.tests.helpers import client_for

pytestmark = pytest.mark.django_db

NEW = "Contrabbasso-Blu-77"


def _params(message) -> dict[str, str]:  # type: ignore[no-untyped-def]
    url = re.search(r"http\S+/reset-password\S+", message.body).group(0)
    return {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}


def _request_reset(client, capture, email):  # type: ignore[no-untyped-def]
    with capture(execute=True):
        return client.post("/api/v1/auth/password-reset/", {"email": email})


def _login(client, email, password):  # type: ignore[no-untyped-def]
    return client.post("/api/v1/auth/token/", {"email": email, "password": password})


def test_uniform_answer_and_mail_only_for_real_accounts(django_capture_on_commit_callbacks):
    user = UserFactory()
    client = APIClient()

    real = _request_reset(client, django_capture_on_commit_callbacks, user.email)
    fake = _request_reset(client, django_capture_on_commit_callbacks, "ghost@example.com")

    assert (
        (real.status_code, real.data)
        == (fake.status_code, fake.data)
        == (
            202,
            {"detail": "check_email"},
        )
    )
    assert [m.to for m in mail.outbox] == [[user.email]]


def test_reset_sets_password_ends_sessions_and_notifies(django_capture_on_commit_callbacks):
    user = UserFactory()
    client = APIClient()
    old_refresh = _login(client, user.email, "password123").data["refresh"]
    _request_reset(client, django_capture_on_commit_callbacks, user.email)
    params = _params(mail.outbox[0])

    with django_capture_on_commit_callbacks(execute=True):
        res = client.post("/api/v1/auth/password-reset/confirm/", {**params, "new_password": NEW})
    reused = client.post("/api/v1/auth/password-reset/confirm/", {**params, "new_password": NEW})

    assert res.status_code == 200
    assert reused.status_code == 400  # single use: the password hash changed
    assert client.post("/api/v1/auth/token/refresh/", {"refresh": old_refresh}).status_code == 401
    assert _login(client, user.email, NEW).status_code == 200
    assert "password" in mail.outbox[-1].subject.lower()
    assert AuditEntry.objects.filter(action="password.reset", actor=user).exists()


def test_older_link_dies_when_a_newer_one_is_used(django_capture_on_commit_callbacks):
    user = UserFactory()
    client = APIClient()
    _request_reset(client, django_capture_on_commit_callbacks, user.email)
    _request_reset(client, django_capture_on_commit_callbacks, user.email)
    older, newer = _params(mail.outbox[0]), _params(mail.outbox[1])

    with django_capture_on_commit_callbacks(execute=True):
        ok = client.post("/api/v1/auth/password-reset/confirm/", {**newer, "new_password": NEW})
    stale = client.post(
        "/api/v1/auth/password-reset/confirm/", {**older, "new_password": "Altro-Viola-55"}
    )

    assert ok.status_code == 200 and stale.status_code == 400


def test_link_expires_after_one_hour(settings, django_capture_on_commit_callbacks):
    user = UserFactory()
    client = APIClient()
    _request_reset(client, django_capture_on_commit_callbacks, user.email)
    settings.PASSWORD_RESET_TIMEOUT = -1

    res = client.post(
        "/api/v1/auth/password-reset/confirm/", {**_params(mail.outbox[0]), "new_password": NEW}
    )

    assert res.status_code == 400


def test_weak_new_password_is_refused(django_capture_on_commit_callbacks):
    user = UserFactory()
    client = APIClient()
    _request_reset(client, django_capture_on_commit_callbacks, user.email)

    res = client.post(
        "/api/v1/auth/password-reset/confirm/",
        {**_params(mail.outbox[0]), "new_password": "12345678"},
    )

    assert res.status_code == 400 and "password" in res.data


def test_reset_clears_a_lock(django_capture_on_commit_callbacks):
    user = UserFactory(
        failed_logins=5, lock_level=2, locked_until=timezone.now() + timedelta(hours=1)
    )
    client = APIClient()
    _request_reset(client, django_capture_on_commit_callbacks, user.email)

    with django_capture_on_commit_callbacks(execute=True):
        client.post(
            "/api/v1/auth/password-reset/confirm/",
            {**_params(mail.outbox[0]), "new_password": NEW},
        )

    user.refresh_from_db()
    assert (user.failed_logins, user.lock_level, user.locked_until) == (0, 0, None)


def test_change_password_needs_the_current_one_and_ends_sessions(
    django_capture_on_commit_callbacks,
):
    user = UserFactory()
    other_device = _login(APIClient(), user.email, "password123").data["refresh"]
    client = client_for(user)

    wrong = client.post(
        "/api/v1/auth/password/change/", {"current_password": "nope", "new_password": NEW}
    )
    with django_capture_on_commit_callbacks(execute=True):
        ok = client.post(
            "/api/v1/auth/password/change/",
            {"current_password": "password123", "new_password": NEW},
        )

    assert wrong.status_code == 400 and "current_password" in wrong.data
    assert ok.status_code == 200
    assert (
        APIClient().post("/api/v1/auth/token/refresh/", {"refresh": other_device}).status_code
        == 401
    )
    assert AuditEntry.objects.filter(action="password.change", actor=user).exists()


def test_reset_request_is_rate_limited(django_capture_on_commit_callbacks):
    client = APIClient()
    codes = [
        _request_reset(client, django_capture_on_commit_callbacks, "x@example.com").status_code
        for _ in range(6)
    ]

    assert codes[-1] == 429
