"""The studio is the tenant (ADR-010)."""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.accounts.models import User
from apps.common.factories import ParentAccountFactory, TeacherFactory, UserFactory
from apps.common.tenancy import ANONYMOUS, get_tenant, resolve_tenant
from apps.common.tests.helpers import client_for, make_studio_owner

pytestmark = pytest.mark.django_db


def test_tenant_is_resolved_once_per_request():
    teacher = TeacherFactory()
    request = APIRequestFactory().get("/")
    request.user = User.objects.get(pk=teacher.user.pk)

    with CaptureQueriesContext(connection) as ctx:
        first = get_tenant(request)
        second = get_tenant(request)

    assert len(ctx) == 1
    assert first is second
    assert (first.studio_id, first.teacher_id) == (teacher.studio_id, teacher.id)


@pytest.mark.parametrize(
    ("make_user", "expected"),
    [
        (lambda: TeacherFactory().user, "is_teacher"),
        (lambda: make_studio_owner().user, "is_owner"),
        (lambda: ParentAccountFactory().user, "is_parent"),
    ],
)
def test_context_flags_per_role(make_user, expected):
    ctx = resolve_tenant(make_user())

    flags = {"is_teacher": ctx.is_teacher, "is_owner": ctx.is_owner, "is_parent": ctx.is_parent}
    assert [name for name, value in flags.items() if value] == [expected]


def test_profile_less_users_get_an_empty_context():
    assert resolve_tenant(None) is ANONYMOUS
    ctx = resolve_tenant(UserFactory(role=User.Role.PARENT))
    assert not (ctx.is_teacher or ctx.is_owner or ctx.is_parent)


def test_get_tenant_without_request_is_anonymous():
    assert get_tenant(None) is ANONYMOUS


def test_created_student_inherits_the_teachers_studio():
    teacher = TeacherFactory()

    res = client_for(teacher.user).post(
        "/api/v1/students/", {"first_name": "A", "last_name": "B", "instrument": "Cello"}
    )

    assert res.status_code == 201
    assert res.data["studio"] == teacher.studio_id


def test_force_authenticated_request_resolves_tenant():
    owner = make_studio_owner()
    request = APIRequestFactory().get("/")
    force_authenticate(request, user=owner.user)
    request.user = owner.user

    assert get_tenant(request).studio_id == owner.studio_id


@pytest.mark.django_db(transaction=True)
def test_migration_gives_every_teacher_and_student_a_studio():
    """Apply the real phase 2 migrations to phase 1 data (solo teacher without studio)."""
    executor = MigrationExecutor(connection)
    before = [("studios", "0002_teacher_owner_constraint"), ("students", "0001_initial")]
    after = [
        ("studios", "0004_teacher_studio_required"),
        ("students", "0003_student_studio_required"),
    ]
    executor.migrate(before)
    old = executor.loader.project_state(before).apps
    user = old.get_model("accounts", "User").objects.create(
        username="solo", email="solo@example.com", role="teacher"
    )
    teacher = old.get_model("studios", "Teacher").objects.create(user=user, studio=None)
    old.get_model("students", "Student").objects.create(
        first_name="A", last_name="B", instrument="Piano", teacher=teacher
    )

    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(after)
    new = executor.loader.project_state(after).apps
    migrated = new.get_model("studios", "Teacher").objects.get(pk=teacher.pk)
    student = new.get_model("students", "Student").objects.get(teacher=migrated)

    assert migrated.studio.name == "solo@example.com"
    assert migrated.is_owner is True
    assert migrated.studio.owner_id == migrated.pk
    assert student.studio_id == migrated.studio_id

    MigrationExecutor(connection).migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())
