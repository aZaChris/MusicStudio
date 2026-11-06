"""Small helpers shared by API tests."""

from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.common.factories import StudioFactory, TeacherFactory
from apps.studios.models import Teacher


def client_for(user: User) -> APIClient:
    """Authenticate as a *fresh* copy of `user`, like a real request does.

    The factory's instance has its teacher/parent profile cached; reusing it would hide
    the query that loads the profile and make query budgets unrealistically low.
    """
    client = APIClient()
    client.force_authenticate(user=User.objects.get(pk=user.pk))
    return client


def make_studio_owner() -> Teacher:
    owner = TeacherFactory(studio=StudioFactory(), is_owner=True)
    owner.user.role = User.Role.STUDIO_OWNER
    owner.user.save()
    return owner
