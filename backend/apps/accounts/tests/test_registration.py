"""Owner self-registration and email confirmation (US1)."""

import re
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts import services
from apps.accounts.models import User
from apps.audit.models import AuditEntry
from apps.common.factories import StudentFactory, UserFactory
from apps.studios.models import Studio

pytestmark = pytest.mark.django_db

PASSWORD = "Violino-Rosso-2026"


def _body(**overrides):
    return {
        "first_name": "Giulia",
        "last_name": "Verdi",
        "email": "giulia@example.com",
        "password": PASSWORD,
        "studio_name": "Scuola Verdi",
        "accept_terms": True,
        **overrides,
    }


def _register(client, django_capture_on_commit_callbacks, **overrides):
    with django_capture_on_commit_callbacks(execute=True):
        return client.post("/api/v1/auth/register/", _body(**overrides))


def _link_params(body: str) -> dict[str, str]:
    url = re.search(r"http\S+", body).group(0)
    return {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}


def test_registration_creates_unconfirmed_owner_with_studio(django_capture_on_commit_callbacks):
    res = _register(APIClient(), django_capture_on_commit_callbacks)

    assert res.status_code == 202 and res.data == {"detail": "check_email"}
    user = User.objects.get(email="giulia@example.com")
    assert user.role == User.Role.STUDIO_OWNER and not user.email_verified
    assert user.terms_accepted_at is not None and user.preferred_language == "it"
    assert Studio.objects.get(owner__user=user).name == "Scuola Verdi"
    assert AuditEntry.objects.filter(action="registration", actor=user).exists()
    assert len(mail.outbox) == 1 and "/confirm-email?" in mail.outbox[0].body


def test_same_answer_for_an_existing_address(django_capture_on_commit_callbacks):
    existing = UserFactory(email="giulia@example.com")
    client = APIClient()

    res = _register(client, django_capture_on_commit_callbacks, email="GIULIA@example.com ")
    fresh = _register(client, django_capture_on_commit_callbacks, email="nuovo@example.com")

    assert (res.status_code, res.data) == (fresh.status_code, fresh.data)
    assert User.objects.filter(email__iexact="giulia@example.com").count() == 1
    duplicate_notice = mail.outbox[0]
    assert duplicate_notice.to == [existing.email]
    assert "/confirm-email" not in duplicate_notice.body


@pytest.mark.parametrize(
    "overrides",
    [
        {"password": "short"},
        {"password": "password123"},  # too common
        {"password": "giulia@example.com1"},  # too similar to the email
        {"accept_terms": False},
        {"email": "not-an-email"},
    ],
)
def test_invalid_registration_creates_nothing(overrides, django_capture_on_commit_callbacks):
    res = _register(APIClient(), django_capture_on_commit_callbacks, **overrides)

    assert res.status_code == 400
    assert not User.objects.filter(email="giulia@example.com").exists()
    assert mail.outbox == []


def test_weak_password_is_refused_the_same_for_an_existing_address(
    django_capture_on_commit_callbacks,
):
    UserFactory(email="giulia@example.com")

    res = _register(APIClient(), django_capture_on_commit_callbacks, password="short")

    assert res.status_code == 400 and "password" in res.data


def test_unconfirmed_owner_cannot_sign_in_until_confirmed(django_capture_on_commit_callbacks):
    client = APIClient()
    _register(client, django_capture_on_commit_callbacks)
    credentials = {"email": "giulia@example.com", "password": PASSWORD}

    refused = client.post("/api/v1/auth/token/", credentials)
    params = _link_params(mail.outbox[0].body)
    confirmed = client.post("/api/v1/auth/confirm-email/", params)
    again = client.post("/api/v1/auth/confirm-email/", params)
    signed_in = client.post("/api/v1/auth/token/", credentials)

    assert refused.status_code == 401 and refused.data["code"] == "email_not_confirmed"
    assert confirmed.status_code == 200
    assert again.status_code == 400  # single use
    assert signed_in.status_code == 200 and "access" in signed_in.data


def test_wrong_password_on_unconfirmed_account_looks_like_any_wrong_password(
    django_capture_on_commit_callbacks,
):
    client = APIClient()
    _register(client, django_capture_on_commit_callbacks)

    res = client.post("/api/v1/auth/token/", {"email": "giulia@example.com", "password": "nope"})

    assert res.status_code == 401 and res.data.get("code") != "email_not_confirmed"


def test_expired_confirmation_link_is_refused(settings, django_capture_on_commit_callbacks):
    client = APIClient()
    _register(client, django_capture_on_commit_callbacks)
    params = _link_params(mail.outbox[0].body)
    settings.EMAIL_CONFIRM_MAX_AGE_SECONDS = -1

    res = client.post("/api/v1/auth/confirm-email/", params)

    assert res.status_code == 400


def test_resend_is_uniform_and_only_mails_unconfirmed_accounts(
    django_capture_on_commit_callbacks,
):
    client = APIClient()
    _register(client, django_capture_on_commit_callbacks)
    confirmed = UserFactory()
    mail.outbox.clear()

    answers = []
    with django_capture_on_commit_callbacks(execute=True):
        for email in ["giulia@example.com", confirmed.email, "nobody@example.com"]:
            res = client.post("/api/v1/auth/confirm-email/resend/", {"email": email})
            answers.append((res.status_code, res.data))

    assert answers[0] == answers[1] == answers[2] == (202, {"detail": "check_email"})
    assert [m.to for m in mail.outbox] == [["giulia@example.com"]]


def test_registration_is_rate_limited(django_capture_on_commit_callbacks):
    client = APIClient()
    codes = [
        _register(client, django_capture_on_commit_callbacks, email=f"u{i}@example.com").status_code
        for i in range(7)
    ]

    assert codes[:5] == [202] * 5 and codes[-1] == 429


def test_unconfirmed_accounts_are_purged_after_seven_days(django_capture_on_commit_callbacks):
    _register(APIClient(), django_capture_on_commit_callbacks)
    stale = User.objects.get(email="giulia@example.com")
    User.objects.filter(pk=stale.pk).update(date_joined=timezone.now() - timedelta(days=8))
    fresh_unconfirmed = UserFactory(email_verified=False)
    confirmed_old = UserFactory()
    User.objects.filter(pk=confirmed_old.pk).update(date_joined=timezone.now() - timedelta(days=90))
    busy_studio = StudentFactory().studio  # studios with students are never deleted

    deleted = services.purge_unconfirmed(timezone.now() - timedelta(days=7))

    assert deleted == 1
    assert not User.objects.filter(pk=stale.pk).exists()
    assert not Studio.objects.filter(name="Scuola Verdi").exists()
    assert User.objects.filter(pk__in=[fresh_unconfirmed.pk, confirmed_old.pk]).count() == 2
    assert Studio.objects.filter(pk=busy_studio.pk).exists()
