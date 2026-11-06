import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from rest_framework.test import APIRequestFactory

from apps.accounts.models import User
from apps.common.exceptions import exception_handler
from apps.common.factories import StudentFactory, UserFactory
from apps.common.scoping import students_visible_to
from apps.common.tests.helpers import client_for

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "user_factory",
    [
        AnonymousUser,
        lambda: UserFactory(role=User.Role.TEACHER),  # teacher role, no profile
        lambda: UserFactory(role=User.Role.PARENT),  # parent role, no profile
        lambda: UserFactory(role=""),  # unknown role
    ],
)
def test_users_without_profile_see_nothing(user_factory):
    StudentFactory()

    assert not students_visible_to(user_factory()).exists()


def test_teacher_role_without_profile_cannot_create_student():
    user = UserFactory(role=User.Role.TEACHER)

    res = client_for(user).post(
        "/api/v1/students/", {"first_name": "A", "last_name": "B", "instrument": "Piano"}
    )

    assert res.status_code == 400


def test_teacher_creates_own_student():
    from apps.common.factories import TeacherFactory

    teacher = TeacherFactory()

    res = client_for(teacher.user).post(
        "/api/v1/students/", {"first_name": "A", "last_name": "B", "instrument": "Piano"}
    )

    assert res.status_code == 201
    assert res.data["teacher"] == teacher.id
    assert res.data["active_package"] is None
    assert res.data["payment_status"] is None


def test_exception_handler_converts_plain_django_validation_error():
    request = APIRequestFactory().get("/")

    response = exception_handler(ValidationError("boom"), {"request": request})

    assert response is not None
    assert response.status_code == 400
    assert response.data == ["boom"]
