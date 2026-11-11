import time
from contextlib import contextmanager
from unittest import mock

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts import mfa, totp
from apps.accounts.models import MfaDevice, RecoveryCode, User
from apps.audit.models import AuditEntry
from apps.common.factories import ParentAccountFactory, TeacherFactory

pytestmark = pytest.mark.django_db
PW = "password123"


@contextmanager
def later(seconds):
    """Move the clock that TOTP steps and signed tokens read (no time-freezing library)."""
    real = time.time
    with mock.patch("time.time", lambda: real() + seconds):
        yield


def code_for(user):
    return totp.code_at(MfaDevice.objects.get(user=user).secret, totp.current_step())


def api_for(user):
    cache.clear()
    client = APIClient()
    client.force_authenticate(user)
    return client


def enable(user):
    """Run setup + confirm; returns the recovery codes."""
    api = api_for(user)
    assert api.post("/api/v1/auth/mfa/setup/").status_code == 201
    res = api.post("/api/v1/auth/mfa/confirm/", {"code": code_for(user)})
    assert res.status_code == 200
    return res.json()["recovery_codes"]


def login(user, password=PW):
    cache.clear()
    return APIClient().post("/api/v1/auth/token/", {"email": user.email, "password": password})


def verify(token, code):
    cache.clear()
    return APIClient().post("/api/v1/auth/mfa/verify/", {"mfa_token": token, "code": code})


@pytest.fixture
def user():
    return TeacherFactory().user


def test_only_owners_and_teachers_can_use_mfa():
    parent = ParentAccountFactory().user
    assert api_for(parent).post("/api/v1/auth/mfa/setup/").status_code == 403
    assert api_for(parent).get("/api/v1/auth/mfa/").status_code == 403


def test_setup_needs_a_valid_code_before_it_counts(user):
    api = api_for(user)
    body = api.post("/api/v1/auth/mfa/setup/").json()
    assert body["otpauth_uri"].startswith("otpauth://totp/")
    assert api.get("/api/v1/auth/mfa/").json() == {"enabled": False, "recovery_codes_left": 0}
    assert api.post("/api/v1/auth/mfa/confirm/", {"code": "000000"}).status_code == 400
    assert not mfa.is_enabled(user)
    # an unconfirmed device does not change sign-in
    assert "access" in login(user).json()


def test_enabled_login_gives_no_tokens_until_the_code_is_sent(user):
    codes = enable(user)
    assert len(codes) == 10
    first = login(user).json()
    assert first.keys() == {"mfa_required", "mfa_token"}
    assert verify(first["mfa_token"], "000000").status_code == 401


def test_full_two_step_login_and_replayed_code_refused(user):
    enable(user)
    # the confirm code used the current step; the next one is needed
    device = MfaDevice.objects.get(user=user)
    with later(30):
        token = login(user).json()["mfa_token"]
        code = code_for(user)
        ok = verify(token, code)
        assert ok.status_code == 200
        assert {"access", "refresh"} <= ok.json().keys()
        assert verify(token, code).status_code == 401  # replay
    device.refresh_from_db()
    assert device.last_used_step > 0


def test_recovery_code_works_once(user):
    codes = enable(user)
    token = login(user).json()["mfa_token"]
    assert verify(token, codes[0]).status_code == 200
    assert verify(token, codes[0]).status_code == 401
    assert api_for(user).get("/api/v1/auth/mfa/").json()["recovery_codes_left"] == 9
    assert AuditEntry.objects.filter(action="mfa.recovery_used").count() == 1


def test_mfa_token_expires_and_is_not_a_user_token(user):
    enable(user)
    token = login(user).json()["mfa_token"]
    with later(360):
        assert verify(token, code_for(user)).status_code == 401
    assert verify("garbage", "123456").status_code == 401


def test_wrong_codes_lock_the_account_like_wrong_passwords(user):
    enable(user)
    token = login(user).json()["mfa_token"]
    for _ in range(5):
        assert verify(token, "000000").status_code == 401
    user.refresh_from_db()
    assert user.locked_until is not None
    assert login(user).status_code == 401


def test_verify_is_throttled(user):
    enable(user)
    token = login(user).json()["mfa_token"]
    client = APIClient()
    cache.clear()
    statuses = [
        client.post("/api/v1/auth/mfa/verify/", {"mfa_token": token, "code": "000000"}).status_code
        for _ in range(7)
    ]
    assert 429 in statuses


def test_disable_needs_password_and_code(user):
    enable(user)
    api = api_for(user)
    url = "/api/v1/auth/mfa/disable/"
    with later(30):
        assert api.post(url, {"password": "nope", "code": code_for(user)}).status_code == 400
        assert api.post(url, {"password": PW, "code": "000000"}).status_code == 400
        assert api.post(url, {"password": PW, "code": code_for(user)}).status_code == 204
    assert not mfa.is_enabled(user)
    assert not RecoveryCode.objects.exists()
    assert "access" in login(user).json()


def test_regenerating_codes_invalidates_the_old_ones(user):
    old = enable(user)
    api = api_for(user)
    with later(30):
        res = api.post("/api/v1/auth/mfa/recovery-codes/", {"password": PW, "code": code_for(user)})
    new = res.json()["recovery_codes"]
    assert len(new) == 10
    token = login(user).json()["mfa_token"]
    assert verify(token, old[0]).status_code == 401
    assert verify(token, new[0]).status_code == 200


def test_me_reports_mfa_state(user):
    assert api_for(user).get("/api/v1/auth/me/").json()["mfa_enabled"] is False
    enable(user)
    assert api_for(user).get("/api/v1/auth/me/").json()["mfa_enabled"] is True
    assert User.objects.get(pk=user.pk).mfa_device.secret not in str(
        AuditEntry.objects.values_list("metadata", flat=True)
    )
