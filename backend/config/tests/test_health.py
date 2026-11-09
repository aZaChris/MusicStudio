import pytest
from django.test import Client, override_settings

from config import health

pytestmark = pytest.mark.django_db


def _broken() -> None:
    raise ConnectionError("down")


def test_live_needs_nothing():
    res = Client().get("/health/live/")

    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_ready_ok_when_dependencies_ok(monkeypatch):
    monkeypatch.setitem(health.CHECKS, "redis", lambda: None)  # no Redis in unit tests

    res = Client().get("/health/ready/")

    assert res.status_code == 200
    assert res.json()["checks"] == {"database": "ok", "redis": "ok"}


@pytest.mark.parametrize("failing", ["database", "redis"])
def test_ready_503_when_a_dependency_is_down(monkeypatch, failing):
    monkeypatch.setitem(health.CHECKS, "redis", lambda: None)
    monkeypatch.setitem(health.CHECKS, failing, _broken)

    res = Client().get("/health/ready/")

    assert res.status_code == 503
    assert res.json()["checks"][failing] == "error"
    # Unauthenticated endpoint: the failure reason stays in the logs, never in the body.
    assert "down" not in res.content.decode()


def test_redis_check_uses_configured_url(monkeypatch):
    pinged = {}

    class FakeRedis:
        def ping(self):
            pinged["ok"] = True

    monkeypatch.setattr(health.redis.Redis, "from_url", lambda url, **kw: FakeRedis())
    health.check_redis()

    assert pinged == {"ok": True}


def test_health_is_post_proof():
    assert Client().post("/health/live/").status_code == 405


@override_settings(
    SECURE_SSL_REDIRECT=True, SECURE_REDIRECT_EXEMPT=[r"^health/"], ALLOWED_HOSTS=["*"]
)
def test_health_is_exempt_from_https_redirect_but_api_is_not():
    client = Client()

    assert client.get("/health/live/").status_code == 200
    assert client.get("/api/v1/students/").status_code == 301
