import pytest
from rest_framework.test import APIClient

from apps.common.factories import PackageFactory, StudentFactory

pytestmark = pytest.mark.django_db


def _client_for(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_payment_creation_rejects_package_student_mismatch():
    student = StudentFactory()
    other_student = StudentFactory(teacher=student.teacher)
    mismatched_package = PackageFactory(student=other_student)

    client = _client_for(student.teacher.user)
    res = client.post(
        "/api/v1/payments/",
        {
            "student": student.id,
            "package": mismatched_package.id,
            "amount": "50.00",
            "date": "2026-01-10",
            "method": "cash",
            "status": "paid",
        },
        format="json",
    )

    assert res.status_code == 400
    assert "package" in res.data


def test_payment_creation_succeeds_with_matching_package():
    student = StudentFactory()
    package = PackageFactory(student=student)

    client = _client_for(student.teacher.user)
    res = client.post(
        "/api/v1/payments/",
        {
            "student": student.id,
            "package": package.id,
            "amount": "50.00",
            "date": "2026-01-10",
            "method": "cash",
            "status": "paid",
        },
        format="json",
    )

    assert res.status_code == 201


def test_payment_status_transition_pending_to_paid():
    student = StudentFactory()
    client = _client_for(student.teacher.user)
    create_res = client.post(
        "/api/v1/payments/",
        {
            "student": student.id,
            "amount": "30.00",
            "date": "2026-01-10",
            "method": "manual_entry",
            "status": "pending",
        },
        format="json",
    )
    payment_id = create_res.data["id"]

    patch_res = client.patch(f"/api/v1/payments/{payment_id}/", {"status": "paid"}, format="json")

    assert patch_res.status_code == 200
    assert patch_res.data["status"] == "paid"


def test_parent_cannot_write_a_payment():
    from apps.common.factories import ParentAccountFactory, link_parent_to_student

    student = StudentFactory()
    parent = ParentAccountFactory()
    link_parent_to_student(parent, student)

    client = _client_for(parent.user)
    res = client.post(
        "/api/v1/payments/",
        {"student": student.id, "amount": "10.00", "date": "2026-01-10", "method": "cash"},
        format="json",
    )

    assert res.status_code == 403
