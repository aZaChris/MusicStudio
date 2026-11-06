"""Payment status is a small state machine (FR-012)."""

import pytest

from apps.common.factories import StudentFactory
from apps.common.tests.helpers import client_for
from apps.payments.models import Payment

pytestmark = pytest.mark.django_db

ALLOWED = {("pending", "paid"), ("pending", "overdue"), ("overdue", "paid")}
STATUSES = ["pending", "paid", "overdue"]


@pytest.mark.parametrize("current", STATUSES)
@pytest.mark.parametrize("target", STATUSES)
def test_status_transitions(current, target):
    student = StudentFactory()
    payment = Payment.objects.create(
        student=student, amount="10", date="2026-01-01", method="cash", status=current
    )

    res = client_for(student.teacher.user).patch(
        f"/api/v1/payments/{payment.id}/", {"status": target}
    )

    payment.refresh_from_db()
    if current == target or (current, target) in ALLOWED:
        assert res.status_code == 200
        assert payment.status == target
    else:
        assert res.status_code == 400
        assert "status" in res.data
        assert payment.status == current


def test_paid_payment_other_fields_stay_editable():
    student = StudentFactory()
    payment = Payment.objects.create(
        student=student, amount="10", date="2026-01-01", method="cash", status="paid"
    )

    res = client_for(student.teacher.user).patch(
        f"/api/v1/payments/{payment.id}/", {"method": "bank_transfer"}
    )

    assert res.status_code == 200
