"""Sentry scrubbing and the test-error command (US3, ADR-019)."""

from io import StringIO
from unittest import mock

from django.core.management import call_command

from apps.common import sentry
from apps.common.logging import request_id_var


def _event(url: str = "https://api.example.com/api/v1/lessons/") -> dict:
    return {
        "request": {
            "url": url,
            "headers": {"Authorization": "Bearer eyJ...", "Stripe-Signature": "t=1,v1=x"},
            "cookies": {"sessionid": "s"},
            "data": {"password": "hunter2"},
            "query_string": "email=mario@example.com",
        },
        "exception": {"values": [{"value": "No user mario.rossi@example.com"}]},
        "logentry": {"message": "login failed for anna@example.com"},
        "user": {"email": "mario@example.com"},
    }


def test_credentials_and_emails_are_scrubbed():
    token = request_id_var.set("req-9")
    try:
        event = sentry.before_send(_event(), {})
    finally:
        request_id_var.reset(token)

    headers = event["request"]["headers"]
    assert headers["Authorization"] == headers["Stripe-Signature"] == "[Filtered]"
    assert "cookies" not in event["request"]
    assert "user" not in event
    assert "@" not in event["exception"]["values"][0]["value"]
    assert "@" not in event["logentry"]["message"]
    assert "@" not in event["request"]["query_string"]
    assert event["tags"]["request_id"] == "req-9"


def test_bodies_of_auth_and_webhook_endpoints_are_dropped():
    for path in ("/api/v1/auth/token/", "/api/v1/webhooks/stripe/"):
        event = sentry.before_send(_event(f"https://api.example.com{path}"), {})
        assert "data" not in event["request"]


def test_other_bodies_are_kept():
    assert "data" in sentry.before_send(_event(), {})["request"]


def test_init_uses_safe_defaults():
    with mock.patch.object(sentry.sentry_sdk, "init") as init:
        sentry.init_sentry("https://k@o0.ingest.sentry.io/1", "test", 0.0, None)

    kwargs = init.call_args.kwargs
    assert kwargs["send_default_pii"] is False
    assert kwargs["before_send"] is sentry.before_send


def test_raise_test_error_without_sentry_only_logs():
    out = StringIO()
    call_command("raise_test_error", stdout=out)
    assert "not configured" in out.getvalue()


def test_raise_test_error_with_sentry_sends_an_event():
    out = StringIO()
    client = mock.Mock(**{"is_active.return_value": True})
    with (
        mock.patch("sentry_sdk.get_client", return_value=client),
        mock.patch("sentry_sdk.capture_exception", return_value="evt1") as capture,
        mock.patch("sentry_sdk.flush"),
    ):
        call_command("raise_test_error", stdout=out)

    capture.assert_called_once()
    assert "evt1" in out.getvalue()
