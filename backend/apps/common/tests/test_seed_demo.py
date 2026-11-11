import datetime
from unittest import mock

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


@pytest.mark.parametrize("hour_utc", [10, 22, 23])
def test_seed_demo_stays_idempotent_whatever_the_hour(hour_utc):
    # Between 22:00 and 24:00 UTC the UTC date and the Rome date differ: the idempotency check
    # once compared the two and inserted the reminder lesson twice (a CI run after midnight in
    # Rome failed on the teacher-overlap constraint).
    now = datetime.datetime(2026, 11, 11, hour_utc, 1, tzinfo=datetime.UTC)
    with mock.patch("django.utils.timezone.now", return_value=now):
        call_command("seed_demo", "--force")
        lessons = Lesson.objects.count()
        call_command("seed_demo", "--force")

    assert Lesson.objects.count() == lessons
