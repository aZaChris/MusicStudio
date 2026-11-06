import pytest
from django.core.management import CommandError, call_command

from apps.accounts.models import User
from apps.lessons.models import Lesson

pytestmark = pytest.mark.django_db


def test_seed_demo_refuses_without_debug():
    with pytest.raises(CommandError):
        call_command("seed_demo")


def test_seed_demo_runs_with_force_and_is_idempotent():
    call_command("seed_demo", "--force")
    users, lessons = User.objects.count(), Lesson.objects.count()

    call_command("seed_demo", "--force")

    assert users > 0
    assert (User.objects.count(), Lesson.objects.count()) == (users, lessons)
