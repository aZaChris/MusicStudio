"""What a reversal changes around the entry: package, checkout, roster (FR-005, edge cases)."""

import pytest

from apps.common.factories import (
    LessonFactory,
    PackageFactory,
    PaymentFactory,
    StudentFactory,
    connected_package,
)
from apps.common.tests.helpers import client_for
from apps.lessons.models import Lesson
from apps.payments.models import Payment

pytestmark = pytest.mark.django_db


def _reverse(client, payment):
    res = client.post(f"/api/v1/payments/{payment.pk}/reverse/", {"reason": "x"}, format="json")
    assert res.status_code == 201, res.data
    return res


def test_reversing_the_only_paid_entry_makes_the_package_payable_again(fake_stripe):
    package = connected_package()
    payment = PaymentFactory(student=package.student, package=package)
    client = client_for(package.student.teacher.user)
    assert client.post(f"/api/v1/packages/{package.pk}/checkout/").status_code == 409

    _reverse(client, payment)

    assert client.post(f"/api/v1/packages/{package.pk}/checkout/").status_code == 200


def test_with_two_paid_entries_reversing_one_leaves_the_package_paid(fake_stripe):
    package = PackageFactory()
    first = PaymentFactory(student=package.student, package=package)
    PaymentFactory(student=package.student, package=package)
    client = client_for(package.student.teacher.user)

    _reverse(client, first)

    assert client.post(f"/api/v1/packages/{package.pk}/checkout/").status_code == 409


def test_completed_lessons_are_not_touched_by_a_reversal():
    package = PackageFactory(lessons_remaining=5)
    payment = PaymentFactory(student=package.student, package=package)
    lesson = LessonFactory(student=package.student, package=package, status="completed")
    client = client_for(package.student.teacher.user)

    _reverse(client, payment)

    lesson.refresh_from_db()
    package.refresh_from_db()
    assert lesson.status == Lesson.Status.COMPLETED and package.lessons_remaining == 5


def test_the_roster_payment_status_updates_after_a_reversal():
    student = StudentFactory()
    PaymentFactory(student=student, date="2026-01-01", status=Payment.Status.PENDING)
    paid = PaymentFactory(student=student, date="2026-02-01")
    client = client_for(student.teacher.user)

    def status():
        rows = client.get("/api/v1/students/").data["results"]
        return next(r for r in rows if r["id"] == student.pk)["payment_status"]

    assert status() == "paid"
    _reverse(client, paid)
    assert status() == "pending"
