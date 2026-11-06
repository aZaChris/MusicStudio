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


def test_user_str_is_email():
    teacher = TeacherFactory(user__email="x@example.com")

    assert str(teacher.user) == "x@example.com"
    assert str(teacher) == "x@example.com"
