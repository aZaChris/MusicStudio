import pytest
from rest_framework.test import APIClient

from apps.common.factories import (
    LessonFactory,
    PackageFactory,
    ParentAccountFactory,
    StudentFactory,
    link_parent_to_student,
)
from apps.payments.models import Payment

pytestmark = pytest.mark.django_db


def _client_for(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_parent_sees_only_linked_student():
    linked_student = StudentFactory()
    other_student = StudentFactory()
    parent = ParentAccountFactory()
    link_parent_to_student(parent, linked_student)

    client = _client_for(parent.user)
    res = client.get("/api/v1/students/")

    ids = [s["id"] for s in res.data["results"]]
    assert ids == [linked_student.id]

    detail_other = client.get(f"/api/v1/students/{other_student.id}/")
    assert detail_other.status_code == 404


def test_parent_with_multiple_students_sees_only_their_own():
    parent = ParentAccountFactory()
    child_a = StudentFactory()
    child_b = StudentFactory()
    unrelated = StudentFactory()
    link_parent_to_student(parent, child_a)
    link_parent_to_student(parent, child_b)

    client = _client_for(parent.user)
    res = client.get("/api/v1/students/")

    ids = {s["id"] for s in res.data["results"]}
    assert ids == {child_a.id, child_b.id}
    assert unrelated.id not in ids


def test_parent_sees_linked_students_lessons_and_payments_readonly():
    student = StudentFactory()
    package = PackageFactory(student=student)
    lesson = LessonFactory(student=student, package=package)
    Payment.objects.create(student=student, amount="40.00", date="2026-01-01", method="cash", status="paid")
    parent = ParentAccountFactory()
    link_parent_to_student(parent, student)

    client = _client_for(parent.user)

    lessons_res = client.get("/api/v1/lessons/")
    assert lesson.id in [item["id"] for item in lessons_res.data["results"]]

    payments_res = client.get("/api/v1/payments/")
    assert len(payments_res.data["results"]) == 1

    packages_res = client.get("/api/v1/packages/")
    assert len(packages_res.data["results"]) == 1


def test_parent_cannot_write_anywhere():
    student = StudentFactory()
    parent = ParentAccountFactory()
    link_parent_to_student(parent, student)

    client = _client_for(parent.user)

    assert client.post("/api/v1/students/", {"first_name": "x"}, format="json").status_code == 403
    assert (
        client.post(f"/api/v1/lessons/{LessonFactory(student=student).id}/complete/", {}, format="json").status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/payments/",
            {"student": student.id, "amount": "1", "date": "2026-01-01", "method": "cash"},
            format="json",
        ).status_code
        == 403
    )
