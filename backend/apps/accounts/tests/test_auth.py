import pytest
from rest_framework.test import APIClient

from apps.common.factories import TeacherFactory

pytestmark = pytest.mark.django_db


def test_login_returns_tokens_and_me_works():
    teacher = TeacherFactory(user__email="t@example.com")
    client = APIClient()

    res = client.post("/api/v1/auth/token/", {"email": "t@example.com", "password": "password123"})
    assert res.status_code == 200

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
    me = client.get("/api/v1/auth/me/")
    assert me.status_code == 200
    assert me.data["email"] == "t@example.com"
    assert me.data["teacher"]["id"] == teacher.id

    refreshed = client.post("/api/v1/auth/token/refresh/", {"refresh": res.data["refresh"]})
    assert refreshed.status_code == 200


def test_login_is_throttled_after_five_attempts():
    TeacherFactory(user__email="t@example.com")
    client = APIClient()
    bad = {"email": "t@example.com", "password": "wrong"}

    statuses = [client.post("/api/v1/auth/token/", bad).status_code for _ in range(6)]

    assert statuses[:5] == [401] * 5
    assert statuses[5] == 429


@pytest.mark.parametrize("num_proxies", [0, 1])
def test_forged_forwarded_for_cannot_reset_the_login_throttle(settings, num_proxies):
    # Each attempt claims a different origin; only the right-most entries we trust count.
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, "NUM_PROXIES": num_proxies}
    TeacherFactory(user__email="t@example.com")
    client = APIClient()
    bad = {"email": "t@example.com", "password": "wrong"}

    statuses = [
        client.post(
            "/api/v1/auth/token/", bad, HTTP_X_FORWARDED_FOR=f"10.0.0.{i}, 203.0.113.7"
        ).status_code
        for i in range(6)
    ]

    assert statuses[5] == 429


def test_user_str_is_email():
    teacher = TeacherFactory(user__email="x@example.com")

    assert str(teacher.user) == "x@example.com"
    assert str(teacher) == "x@example.com"
