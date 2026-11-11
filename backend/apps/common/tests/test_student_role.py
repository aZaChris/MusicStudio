"""Adult student accounts: read-only, and only their own record and what hangs off it."""

import pytest

from apps.common.factories import (
    LessonFactory,
    PackageFactory,
    StudentFactory,
    make_student_account,
)
from apps.common.tenancy import resolve_tenant
from apps.common.tests.helpers import client_for

pytestmark = pytest.mark.django_db


def test_student_context_points_to_their_record():
    student = StudentFactory()
    user = make_student_account(student)

    ctx = resolve_tenant(user)

    assert ctx.is_student and ctx.student_id == student.pk
    assert not (ctx.is_owner or ctx.is_teacher or ctx.is_parent)


def test_student_reads_only_self():
    me = StudentFactory()
    classmate = StudentFactory(teacher=me.teacher)
    user = make_student_account(me)
    LessonFactory(student=me)
    LessonFactory(student=classmate)
    PackageFactory(student=me)
    PackageFactory(student=classmate)
    client = client_for(user)

    students = client.get("/api/v1/students/").data["results"]
    lessons = client.get("/api/v1/lessons/").data["results"]
    packages = client.get("/api/v1/packages/").data["results"]

    assert [s["id"] for s in students] == [me.pk]
    assert {lesson["student"] for lesson in lessons} == {me.pk}
    assert {p["student"] for p in packages} == {me.pk}
    assert client.get(f"/api/v1/students/{classmate.pk}/").status_code == 404


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("post", "/api/v1/students/", {"first_name": "A", "last_name": "B", "instrument": "x"}),
        ("patch", "/api/v1/students/{me}/", {"first_name": "Hacked"}),
        ("delete", "/api/v1/students/{me}/", None),
        ("post", "/api/v1/packages/", {"student": "{me}", "total_lessons": 5, "price": "10"}),
        ("post", "/api/v1/payments/", {"student": "{me}", "amount": "10"}),
    ],
)
def test_student_cannot_write(method, path, body):
    me = StudentFactory()
    client = client_for(make_student_account(me))
    path = path.format(me=me.pk)
    body = {k: (v.format(me=me.pk) if isinstance(v, str) else v) for k, v in (body or {}).items()}

    res = getattr(client, method)(path, body)

    assert res.status_code == 403
    me.refresh_from_db()
    assert me.first_name != "Hacked"


def test_teacher_marks_a_student_adult_and_cannot_undo_it_once_they_have_an_account():
    me = StudentFactory()
    client = client_for(me.teacher.user)
    url = f"/api/v1/students/{me.pk}/"

    res = client.patch(url, {"is_adult": True}, format="json")
    assert res.status_code == 200
    assert (res.data["is_adult"], res.data["has_account"]) == (True, False)

    make_student_account(me)
    res = client.patch(url, {"is_adult": False}, format="json")
    assert res.status_code == 400
    assert client.get(url).data["has_account"] is True


def test_has_account_cannot_be_written():
    me = StudentFactory()
    client = client_for(me.teacher.user)
    client.patch(f"/api/v1/students/{me.pk}/", {"has_account": True}, format="json")
    me.refresh_from_db()
    assert me.user_id is None
