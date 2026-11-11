"""Account emails: language, links that work, nothing personal in the logs."""

import re
from urllib.parse import parse_qs, urlparse

import pytest
from django.core import mail

from apps.accounts import tokens
from apps.accounts.tasks import send_account_email
from apps.common.factories import UserFactory

pytestmark = pytest.mark.django_db


def _link(body: str) -> dict[str, str]:
    url = re.search(r"http\S+", body).group(0)
    return {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}


def test_confirmation_email_in_italian_with_a_working_link(settings):
    settings.FRONTEND_URL = "https://app.example.test/"
    user = UserFactory(email_verified=False, preferred_language="it", first_name="Anna")

    send_account_email("confirm_email", user.pk)

    (message,) = mail.outbox
    assert message.to == [user.email]
    assert message.subject.startswith("Conferma")
    assert "https://app.example.test/confirm-email?" in message.body
    params = _link(message.body)
    assert tokens.user_for_confirm_token(params["uid"], params["token"]) == user


def test_reset_email_link_is_valid_until_the_password_changes():
    user = UserFactory()

    send_account_email("password_reset", user.pk)
    params = _link(mail.outbox[0].body)

    assert tokens.user_for_reset_token(params["uid"], params["token"]) == user
    user.set_password("another-Password-42")
    user.save()
    assert tokens.user_for_reset_token(params["uid"], params["token"]) is None


@pytest.mark.parametrize("kind", ["duplicate_signup", "password_changed"])
def test_notice_emails_point_to_login_and_reset(kind):
    user = UserFactory(preferred_language="en")

    send_account_email(kind, user.pk)

    assert "/forgot-password" in mail.outbox[0].body


def test_missing_user_sends_nothing():
    send_account_email("confirm_email", 999_999)

    assert mail.outbox == []


def test_log_line_has_no_address_or_link(caplog):
    user = UserFactory()
    caplog.set_level("INFO", logger="apps.accounts.emails")

    send_account_email("password_reset", user.pk)

    text = " ".join(f"{r.getMessage()} {r.__dict__}" for r in caplog.records)
    assert user.email not in text and "token" not in text


@pytest.mark.parametrize("uid", ["", "!!", "MTIzNDU2Nzg5"])
def test_garbage_links_are_refused(uid):
    assert tokens.user_for_confirm_token(uid, "x") is None
    assert tokens.user_for_reset_token(uid, "x") is None


def test_confirmation_link_dies_once_used():
    user = UserFactory(email_verified=False)
    uid, token = tokens.encode_uid(user), tokens.make_confirm_token(user)

    user.email_verified = True
    user.save()

    assert tokens.user_for_confirm_token(uid, token) is None


def test_plain_text_is_not_html_escaped():
    user = UserFactory(first_name="Nicolò D'Angelo")

    send_account_email("password_changed", user.pk)

    assert "Nicolò D'Angelo" in mail.outbox[0].body
