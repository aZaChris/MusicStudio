"""Constitution X: logs never carry personal data, passwords, codes or tokens.

Runs the account flows with every logger captured at DEBUG, then looks for the values that
were typed or sent in any record (message, arguments and extra fields).
"""

import logging
import re
import time
from urllib.parse import unquote

import pytest
from django.core import mail
from rest_framework.test import APIClient

from apps.accounts import mfa, totp
from apps.accounts.models import User
from apps.common.tests.helpers import client_for, make_studio_owner

pytestmark = pytest.mark.django_db

EMAIL = "zelinda.quattrocchi@example.com"
NAME, SURNAME = "Zelinda", "Quattrocchi"
PASSWORD = "Violoncello-Azzurro-77"
NEW_PASSWORD = "Contrabbasso-Rosso-88"
INVITED = "ospite.invitato@example.com"


def links() -> list[str]:
    return re.findall(r"http\S+", " ".join(m.body for m in mail.outbox))


def secrets_in(url: str) -> list[str]:
    """Link parameters, decoded (what the API receives)."""
    return [unquote(v) for v in re.findall(r"(?:uid|token)=([^&\s]+)", url)]


def test_account_flows_leave_no_personal_data_in_logs(caplog, django_capture_on_commit_callbacks):
    caplog.set_level(logging.DEBUG)
    api = APIClient()
    sensitive = {EMAIL, NAME, SURNAME, PASSWORD, NEW_PASSWORD, INVITED}

    with django_capture_on_commit_callbacks(execute=True):
        res = api.post(
            "/api/v1/auth/register/",
            {
                "first_name": NAME,
                "last_name": SURNAME,
                "email": EMAIL,
                "password": PASSWORD,
                "studio_name": "Scuola Quattrocchi",
                "accept_terms": True,
            },
            format="json",
        )
    assert res.status_code == 202
    confirm_url = links()[-1]
    sensitive.update(secrets_in(confirm_url))
    uid, token = secrets_in(confirm_url)[:2]
    api.post("/api/v1/auth/confirm-email/", {"uid": uid, "token": token})

    # sign in (wrong, then right), then MFA setup and a two-step sign-in
    api.post("/api/v1/auth/token/", {"email": EMAIL, "password": "wrong-password-1"})
    login = api.post("/api/v1/auth/token/", {"email": EMAIL, "password": PASSWORD}).json()
    user = User.objects.get(email=EMAIL)
    owner = client_for(user)
    secret, _ = mfa.begin_setup(user)
    code = totp.code_at(secret, totp.current_step())
    codes = mfa.confirm_setup(user, code)
    sensitive.update({secret, code, *codes, login["access"], login["refresh"]})
    mfa_token = api.post("/api/v1/auth/token/", {"email": EMAIL, "password": PASSWORD}).json()[
        "mfa_token"
    ]
    api.post("/api/v1/auth/mfa/verify/", {"mfa_token": mfa_token, "code": codes[0]})
    sensitive.add(mfa_token)

    # password reset
    with django_capture_on_commit_callbacks(execute=True):
        api.post("/api/v1/auth/password-reset/", {"email": EMAIL})
    reset_url = links()[-1]
    sensitive.update(secrets_in(reset_url))
    uid, token = secrets_in(reset_url)[:2]
    api.post(
        "/api/v1/auth/password-reset/confirm/",
        {"uid": uid, "token": token, "new_password": NEW_PASSWORD},
    )

    # invitation sent and accepted
    boss = make_studio_owner()
    with django_capture_on_commit_callbacks(execute=True):
        client_for(boss.user).post(
            "/api/v1/invitations/", {"email": INVITED, "role": "teacher"}, format="json"
        )
    invite_token = secrets_in(links()[-1])[0]
    sensitive.add(invite_token)
    api.post(
        "/api/v1/invitations/accept/",
        {"token": invite_token, "password": PASSWORD, "accept_terms": True, "first_name": "Ospite"},
    )
    assert owner is not None and time.time()

    assert caplog.records, "the flows should have logged something"
    standard = set(logging.LogRecord("n", 10, "p", 1, "m", (), None).__dict__) | {"message"}
    for record in caplog.records:
        extras = {k: v for k, v in record.__dict__.items() if k not in standard}
        text = f"{record.getMessage()} {extras}"
        for value in sensitive:
            assert value not in text, f"{value[:6]}… found in log: {text[:120]}"
