"""Every audited action is recorded by the service that performs it (one check per action).

`COVERED_ELSEWHERE` names actions whose own test suite already asserts the entry; the last
test fails when a new Action is added without a check here or there.
"""

import re
import time
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlparse

import pytest
from django.core import mail
from rest_framework.test import APIClient

from apps.accounts import mfa, services, tokens, totp
from apps.accounts.models import User
from apps.audit.models import AuditEntry
from apps.common.factories import StudentFactory, TeacherFactory
from apps.common.tests.helpers import client_for, make_studio_owner

pytestmark = pytest.mark.django_db
PW = "Pianoforte-Verde-31"

# Asserted in the suite of the feature that owns the action.
COVERED_ELSEWHERE = {
    "login.failure",  # test_lockout
    "login.locked",  # test_lockout
    "login.success",  # test_lockout
    "password.reset",  # test_password_reset
    "password.change",  # test_password_reset
    "mfa.recovery_used",  # test_mfa
    "mfa.reset_by_operator",  # test_operator_commands
    "account.unlock_by_operator",  # test_operator_commands
    "invitation.accept",  # test_invitations
    "consent.withdraw",  # apps/privacy/tests
    "privacy.export",  # apps/privacy/tests
    "privacy.erase",  # apps/privacy/tests
}


def actions() -> set[str]:
    return set(AuditEntry.objects.values_list("action", flat=True))


def test_registration_and_email_confirmation():
    services.register_owner(
        email="new@example.com",
        password=PW,
        first_name="N",
        last_name="O",
        studio_name="S",
    )
    assert "registration" in actions()
    user = User.objects.get(email="new@example.com")
    services.confirm_email(tokens.encode_uid(user), tokens.make_confirm_token(user))
    assert "email.confirm" in actions()


def test_mfa_enable_and_disable():
    user = TeacherFactory().user
    secret, _ = mfa.begin_setup(user)
    mfa.confirm_setup(user, totp.code_at(secret, totp.current_step()))
    assert "mfa.enable" in actions()
    code = totp.code_at(secret, totp.current_step() + 1)
    real = time.time
    with mock.patch("time.time", lambda: real() + 30):
        mfa.disable(user, "password123", code)
    assert "mfa.disable" in actions()


def test_invitation_send_revoke_accept_role_change_and_consent(
    django_capture_on_commit_callbacks,
):
    owner = make_studio_owner()
    client = client_for(owner.user)
    with django_capture_on_commit_callbacks(execute=True):
        sent = client.post(
            "/api/v1/invitations/", {"email": "t@example.com", "role": "teacher"}, format="json"
        )
    assert "invitation.send" in actions()
    url = re.search(r"http\S+/invitations/accept\S+", mail.outbox[-1].body).group(0)
    token = parse_qs(urlparse(url).query)["token"][0]
    APIClient().post(
        "/api/v1/invitations/accept/",
        {"token": token, "password": PW, "accept_terms": True, "first_name": "T"},
    )
    assert "role.change" in actions()

    child = StudentFactory(teacher=TeacherFactory(studio=owner.studio))
    with django_capture_on_commit_callbacks(execute=True):
        second = client.post(
            "/api/v1/invitations/",
            {"email": "p@example.com", "role": "parent", "student_ids": [child.pk]},
            format="json",
        )
    token = parse_qs(
        urlparse(re.search(r"http\S+/invitations/accept\S+", mail.outbox[-1].body).group(0)).query
    )["token"][0]
    APIClient().post(
        "/api/v1/invitations/accept/",
        {"token": token, "password": PW, "accept_terms": True, "consent": True},
    )
    assert "consent.give" in actions()

    with django_capture_on_commit_callbacks(execute=True):
        third = client.post(
            "/api/v1/invitations/", {"email": "x@example.com", "role": "teacher"}, format="json"
        )
    client.post(f"/api/v1/invitations/{third.data['id']}/revoke/")
    assert "invitation.revoke" in actions()
    assert sent.status_code == second.status_code == 201


def test_manual_payment_is_audited_with_actor_and_studio():
    teacher = TeacherFactory()
    child = StudentFactory(teacher=teacher)
    res = client_for(teacher.user).post(
        "/api/v1/payments/",
        {"student": child.pk, "amount": "40.00", "date": "2026-11-01", "method": "cash"},
        format="json",
    )
    assert res.status_code == 201
    entry = AuditEntry.objects.get(action="payment.record")
    assert (entry.actor_id, entry.studio_id) == (teacher.user.pk, child.studio_id)
    assert entry.target_id == res.data["id"]
    assert entry.metadata == {"method": "cash", "amount": "40.00"}


def test_every_action_has_a_check():
    here = set(re.findall(r'"([a-z]+(?:\.[a-z_]+)?)" in actions\(\)', Path(__file__).read_text()))
    here |= {"payment.record"}
    missing = {a.value for a in AuditEntry.Action} - here - COVERED_ELSEWHERE
    assert not missing, f"No test checks that these actions are recorded: {missing}"
