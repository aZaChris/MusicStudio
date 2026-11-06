import pytest

from apps.common.factories import PackageFactory, StudentFactory, TeacherFactory
from apps.common.tests.helpers import client_for
from apps.packages.models import Package

pytestmark = pytest.mark.django_db

PAYLOAD = {"total_lessons": 8, "purchase_date": "2026-01-10", "price": "120.00"}


def test_cross_tenant_package_create_is_rejected():
    victim_student = StudentFactory()
    attacker = TeacherFactory()

    res = client_for(attacker.user).post(
        "/api/v1/packages/", {**PAYLOAD, "student": victim_student.id}
    )

    assert res.status_code == 400
    assert "student" in res.data
    assert not Package.objects.filter(student=victim_student).exists()


def test_cross_tenant_package_move_to_foreign_student_is_rejected():
    package = PackageFactory()
    victim_student = StudentFactory()

    res = client_for(package.student.teacher.user).patch(
        f"/api/v1/packages/{package.id}/", {"student": victim_student.id}
    )

    assert res.status_code == 400
    package.refresh_from_db()
    assert package.student_id != victim_student.id
