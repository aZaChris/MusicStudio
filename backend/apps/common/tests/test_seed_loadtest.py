import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.accounts.models import User
from apps.lessons.models import Lesson
from apps.studios.models import Studio

pytestmark = pytest.mark.django_db
SMALL = ["--studios=2", "--teachers=2", "--students=3", "--weeks-back=2", "--weeks-ahead=2"]


def test_refuses_without_debug_or_explicit_flag(settings):
    settings.DEBUG = False
    with pytest.raises(CommandError):
        call_command("seed_loadtest", *SMALL)


def test_seeds_a_consistent_dataset_and_refuses_twice():
    call_command("seed_loadtest", *SMALL, "--i-know-this-is-not-production")

    assert Studio.objects.filter(owner__isnull=False).count() == 2
    assert User.objects.filter(role=User.Role.STUDIO_OWNER).count() == 2
    assert User.objects.filter(role=User.Role.PARENT).count() == 12
    assert Lesson.objects.count() == 12 * 4  # 12 students x 4 weeks, no overlap errors
    assert User.objects.get(email="lt-owner-0@example.com").check_password("loadtest-password")
    with pytest.raises(CommandError):
        call_command("seed_loadtest", *SMALL, "--i-know-this-is-not-production")
