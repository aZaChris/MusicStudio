import pytest
from django.db import IntegrityError, transaction

from apps.accounts.models import User
from apps.common.factories import TeacherFactory, UserFactory
from apps.common.tests.helpers import client_for, make_studio_owner
from apps.studios.models import Teacher

pytestmark = pytest.mark.django_db


def test_owner_sees_studio_with_teacher_count():
    owner = make_studio_owner()
    TeacherFactory(studio=owner.studio)

    res = client_for(owner.user).get("/api/v1/studio/")

    assert res.status_code == 200
    assert res.data["teacher_count"] == 2


def test_owner_lists_only_own_studio_teachers():
    owner = make_studio_owner()
    member = TeacherFactory(studio=owner.studio)
    TeacherFactory()  # solo teacher of another tenant

    res = client_for(owner.user).get("/api/v1/studio/teachers/")

    assert {t["id"] for t in res.data["results"]} == {owner.id, member.id}


def test_owner_without_teacher_profile_gets_404_not_500():
    user = UserFactory(role=User.Role.STUDIO_OWNER)
    client = client_for(user)

    assert client.get("/api/v1/studio/").status_code == 404
    assert client.get("/api/v1/studio/teachers/").data["results"] == []


def test_teacher_without_studio_cannot_exist():
    """Phase 1 found filter(studio=None) leaking every solo teacher; since phase 2 the
    database makes a studio-less teacher impossible (ADR-010)."""
    with pytest.raises(IntegrityError), transaction.atomic():
        Teacher.objects.create(user=UserFactory(), studio=None)


def test_teacher_cannot_access_studio_endpoints():
    teacher = TeacherFactory()

    assert client_for(teacher.user).get("/api/v1/studio/").status_code == 403
