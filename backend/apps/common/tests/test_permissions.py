"""IsTeacherOrOwnerRole: only teachers and owners, reads included."""

import pytest
from django.contrib.auth.models import AnonymousUser
from rest_framework.test import APIRequestFactory

from apps.common.factories import (
    ParentAccountFactory,
    StudentFactory,
    TeacherFactory,
    make_student_account,
)
from apps.common.permissions import IsTeacherOrOwnerRole
from apps.common.tests.helpers import make_studio_owner

pytestmark = pytest.mark.django_db


def _allowed(user, method="get") -> bool:
    request = getattr(APIRequestFactory(), method)("/")
    request.user = user
    return IsTeacherOrOwnerRole().has_permission(request, view=None)


@pytest.mark.parametrize("method", ["get", "post"])
def test_teacher_and_owner_pass(method):
    assert _allowed(TeacherFactory().user, method)
    assert _allowed(make_studio_owner().user, method)


@pytest.mark.parametrize("method", ["get", "post"])
def test_parent_adult_student_and_anonymous_do_not(method):
    assert not _allowed(ParentAccountFactory().user, method)
    assert not _allowed(make_student_account(StudentFactory()), method)
    assert not _allowed(AnonymousUser(), method)
