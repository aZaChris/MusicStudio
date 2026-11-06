"""Audit G4: package creation and the system-managed remaining counter."""

import datetime

import pytest

from apps.common.factories import PackageFactory, StudentFactory
from apps.common.tests.helpers import client_for
from apps.packages.models import Package

pytestmark = pytest.mark.django_db


def test_create_package_without_remaining_starts_full():
    student = StudentFactory()

    res = client_for(student.teacher.user).post(
        "/api/v1/packages/",
        {"student": student.id, "total_lessons": 8, "purchase_date": "2026-01-10", "price": "120"},
    )

    assert res.status_code == 201
    assert res.data["lessons_remaining"] == 8
    assert res.data["status"] == Package.Status.ACTIVE


def test_client_cannot_set_lessons_remaining():
    package = PackageFactory(total_lessons=8, lessons_remaining=8)

    res = client_for(package.student.teacher.user).patch(
        f"/api/v1/packages/{package.id}/", {"lessons_remaining": 0}
    )

    assert res.status_code == 200
    package.refresh_from_db()
    assert package.lessons_remaining == 8


@pytest.mark.parametrize(
    ("remaining", "expiry_offset_days", "status", "is_low"),
    [
        (5, None, Package.Status.ACTIVE, False),
        (2, None, Package.Status.ACTIVE, True),
        (0, None, Package.Status.COMPLETED, False),
        (5, -1, Package.Status.EXPIRED, False),
    ],
)
def test_package_status_and_low_flag(remaining, expiry_offset_days, status, is_low):
    expiry = (
        datetime.date.today() + datetime.timedelta(days=expiry_offset_days)
        if expiry_offset_days is not None
        else None
    )
    package = PackageFactory(total_lessons=8, lessons_remaining=remaining, expiry_date=expiry)

    assert package.status == status
    assert package.is_low is is_low
    assert str(package).endswith(f"{remaining}/8")
