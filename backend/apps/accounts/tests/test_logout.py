"""Logout and session revocation (US1, ADR-018)."""

import datetime

import pytest
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from apps.accounts import services
from apps.common.factories import TeacherFactory

pytestmark = pytest.mark.django_db
PASSWORD = "password123"


def _login(email: str) -> tuple[APIClient, dict]:
    client = APIClient()
    tokens = client.post("/api/v1/auth/token/", {"email": email, "password": PASSWORD}).data
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client, tokens


def _refresh(token: str) -> int:
    return APIClient().post("/api/v1/auth/token/refresh/", {"refresh": token}).status_code


def test_logout_makes_the_refresh_token_unusable():
    TeacherFactory(user__email="a@example.com")
    client, tokens = _login("a@example.com")

    res = client.post("/api/v1/auth/logout/", {"refresh": tokens["refresh"]})

    assert res.status_code == 205
    assert _refresh(tokens["refresh"]) == 401


def test_logout_twice_is_harmless():
    TeacherFactory(user__email="a@example.com")
    client, tokens = _login("a@example.com")

    first = client.post("/api/v1/auth/logout/", {"refresh": tokens["refresh"]})
    second = client.post("/api/v1/auth/logout/", {"refresh": tokens["refresh"]})

    assert (first.status_code, second.status_code) == (205, 205)
    assert BlacklistedToken.objects.count() == 1


def test_cannot_log_out_another_users_session():
    TeacherFactory(user__email="a@example.com")
    TeacherFactory(user__email="b@example.com")
    client_a, _ = _login("a@example.com")
    _, tokens_b = _login("b@example.com")

    res = client_a.post("/api/v1/auth/logout/", {"refresh": tokens_b["refresh"]})

    assert res.status_code == 400
    assert _refresh(tokens_b["refresh"]) == 200  # B's session untouched


@pytest.mark.parametrize("bad", ["", "not-a-jwt"])
def test_malformed_token_is_400(bad):
    TeacherFactory(user__email="a@example.com")
    client, _ = _login("a@example.com")

    assert client.post("/api/v1/auth/logout/", {"refresh": bad}).status_code == 400


def test_access_token_is_not_accepted_as_refresh():
    TeacherFactory(user__email="a@example.com")
    client, tokens = _login("a@example.com")

    assert client.post("/api/v1/auth/logout/", {"refresh": tokens["access"]}).status_code == 400


def test_logout_requires_authentication():
    TeacherFactory(user__email="a@example.com")
    _, tokens = _login("a@example.com")

    assert (
        APIClient().post("/api/v1/auth/logout/", {"refresh": tokens["refresh"]}).status_code == 401
    )


def test_rotated_refresh_token_cannot_be_replayed():
    TeacherFactory(user__email="a@example.com")
    _, tokens = _login("a@example.com")

    assert _refresh(tokens["refresh"]) == 200
    assert _refresh(tokens["refresh"]) == 401


def test_revoke_all_sessions_only_affects_that_user():
    TeacherFactory(user__email="a@example.com")
    TeacherFactory(user__email="b@example.com")
    _, phone = _login("a@example.com")
    _, laptop = _login("a@example.com")
    _, other = _login("b@example.com")

    call_command("revoke_sessions", "A@example.com")

    assert (_refresh(phone["refresh"]), _refresh(laptop["refresh"])) == (401, 401)
    assert _refresh(other["refresh"]) == 200


def test_revoke_sessions_unknown_email_fails():
    from django.core.management.base import CommandError

    with pytest.raises(CommandError):
        call_command("revoke_sessions", "nobody@example.com")


def test_admin_action_revokes_sessions(client):
    teacher = TeacherFactory(user__email="a@example.com")
    _, tokens = _login("a@example.com")
    operator = TeacherFactory(user__is_staff=True, user__is_superuser=True).user
    client.force_login(operator)

    res = client.post(
        "/admin/accounts/user/",
        {"action": "revoke_sessions", "_selected_action": [teacher.user.pk]},
    )

    assert res.status_code == 302
    assert _refresh(tokens["refresh"]) == 401


def test_purge_deletes_only_expired_tokens():
    TeacherFactory(user__email="a@example.com")
    _login("a@example.com")
    _login("a@example.com")
    expired = OutstandingToken.objects.first()
    expired.expires_at = timezone.now() - datetime.timedelta(seconds=1)
    expired.save()

    from apps.accounts.tasks import purge_expired_tokens

    assert purge_expired_tokens.delay().get() == 1
    assert OutstandingToken.objects.count() == 1


def test_revoke_all_skips_already_blacklisted():
    teacher = TeacherFactory(user__email="a@example.com")
    _login("a@example.com")

    assert services.revoke_all_sessions(teacher.user) == 1
    assert services.revoke_all_sessions(teacher.user) == 0
