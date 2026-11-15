"""One rule for "paid": a paid entry that was not reversed (research R5)."""

import pytest

from apps.common.factories import (
    PackageFactory,
    PaymentFactory,
    StudentFactory,
    make_reversal,
)
from apps.common.tenancy import resolve_tenant
from apps.common.tests.helpers import client_for
from apps.payments import selectors
from apps.payments.models import Payment
from apps.payments.services import package_is_paid
from apps.students.selectors import students_for

pytestmark = pytest.mark.django_db


def test_a_paid_entry_makes_the_package_paid_until_it_is_reversed():
    package = PackageFactory()
    payment = PaymentFactory(student=package.student, package=package)
    assert package_is_paid(package)

    make_reversal(payment)

    assert not package_is_paid(package)


def test_with_two_paid_entries_reversing_one_leaves_the_package_paid():
    package = PackageFactory()
    first = PaymentFactory(student=package.student, package=package)
    PaymentFactory(student=package.student, package=package)
    make_reversal(first)
    assert package_is_paid(package)


def test_pending_and_reversal_rows_never_count_as_paid():
    package = PackageFactory()
    PaymentFactory(student=package.student, package=package, status=Payment.Status.PENDING)
    assert not package_is_paid(package)
    assert selectors.effective_paid(Payment.objects.all()).count() == 0


def test_checkout_is_allowed_again_after_a_reversal(fake_stripe):
    package = PackageFactory()
    payment = PaymentFactory(student=package.student, package=package)
    owner = package.student.teacher.user
    assert client_for(owner).post(f"/api/v1/packages/{package.id}/checkout/").status_code == 409

    make_reversal(payment)

    assert client_for(owner).post(f"/api/v1/packages/{package.id}/checkout/").status_code == 200


def test_open_packages_follow_the_same_rule():
    student = StudentFactory()
    paid = PackageFactory(student=student)
    open_ = PackageFactory(student=student)
    PaymentFactory(student=student, package=paid)
    ctx = resolve_tenant(student.teacher.user)

    assert set(selectors.open_packages(ctx)) == {open_}

    make_reversal(Payment.objects.get(package=paid, status="paid"))
    assert set(selectors.open_packages(ctx)) == {open_, paid}


def test_the_roster_status_falls_back_to_the_earlier_entry_or_none():
    student = StudentFactory()
    ctx = resolve_tenant(student.teacher.user)
    older = PaymentFactory(student=student, date="2026-01-01", status=Payment.Status.PENDING)
    newer = PaymentFactory(student=student, date="2026-02-01")

    assert students_for(ctx).get(pk=student.pk).latest_payment_status == "paid"

    make_reversal(newer)
    assert students_for(ctx).get(pk=student.pk).latest_payment_status == "pending"

    older.delete()
    assert students_for(ctx).get(pk=student.pk).latest_payment_status is None
