import pytest

from apps.common.factories import PackageFactory, StudentFactory, TeacherFactory
from apps.common.tests.helpers import client_for
from apps.payments.models import Payment

pytestmark = pytest.mark.django_db

PAYLOAD = {"amount": "10.00", "date": "2026-01-10", "method": "cash", "status": "paid"}


def test_cross_tenant_payment_create_is_rejected():
    victim_student = StudentFactory()
    attacker = TeacherFactory()

    res = client_for(attacker.user).post(
        "/api/v1/payments/", {**PAYLOAD, "student": victim_student.id}
    )

    assert res.status_code == 400
    assert "student" in res.data
    assert not Payment.objects.filter(student=victim_student).exists()


def test_cross_tenant_payment_with_foreign_package_is_rejected():
    own_student = StudentFactory()
    foreign_package = PackageFactory()

    res = client_for(own_student.teacher.user).post(
        "/api/v1/payments/",
        {**PAYLOAD, "student": own_student.id, "package": foreign_package.id},
    )

    assert res.status_code == 400
    assert "package" in res.data


def test_cross_tenant_payment_update_to_foreign_student_is_rejected():
    own_student = StudentFactory()
    payment = Payment.objects.create(student=own_student, **PAYLOAD)
    victim_student = StudentFactory()

    res = client_for(own_student.teacher.user).patch(
        f"/api/v1/payments/{payment.id}/", {"student": victim_student.id}
    )

    assert res.status_code == 400
    payment.refresh_from_db()
    assert payment.student_id == own_student.id


def test_payment_update_with_package_of_other_student_is_rejected():
    student = StudentFactory()
    sibling_package = PackageFactory(student=StudentFactory(teacher=student.teacher))
    payment = Payment.objects.create(student=student, **PAYLOAD)

    res = client_for(student.teacher.user).patch(
        f"/api/v1/payments/{payment.id}/", {"package": sibling_package.id}
    )

    assert res.status_code == 400
    assert "package" in res.data
