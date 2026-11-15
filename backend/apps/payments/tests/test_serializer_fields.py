"""New payment fields: derived ones, staff-only ones, and the ones a client cannot write."""

import pytest

from apps.common.factories import (
    ParentAccountFactory,
    PaymentFactory,
    StudentFactory,
    link_parent_to_student,
    make_reversal,
    make_student_account,
)
from apps.common.tests.helpers import client_for
from apps.payments.models import Payment

pytestmark = pytest.mark.django_db


def _item(client, payment) -> dict:
    results = client.get("/api/v1/payments/").data["results"]
    return next(r for r in results if r["id"] == payment.pk)


def test_staff_see_reversal_fields_reason_and_author():
    student = StudentFactory()
    owner = student.teacher.user
    original = PaymentFactory(student=student)
    reversal = make_reversal(original, reason="wrong student", recorded_by=owner)
    client = client_for(owner)

    original_item = _item(client, original)
    reversal_item = _item(client, reversal)

    assert original_item["reversed"] is True and original_item["reversal_id"] == reversal.pk
    assert original_item["reversal_of"] is None
    assert reversal_item["reversal_of"] == original.pk
    assert reversal_item["status"] == "reversal"
    assert reversal_item["reason"] == "wrong student"
    assert reversal_item["recorded_by"] == owner.pk
    assert reversal_item["reversed"] is False


def test_an_entry_without_reversal_reads_not_reversed():
    student = StudentFactory()
    entry = PaymentFactory(student=student)
    item = _item(client_for(student.teacher.user), entry)
    assert item["reversed"] is False and item["reversal_id"] is None


@pytest.mark.parametrize("kind", ["parent", "student"])
def test_parents_and_adult_students_do_not_see_reason_or_author(kind):
    student = StudentFactory()
    original = PaymentFactory(student=student)
    reversal = make_reversal(original, reason="private text", recorded_by=student.teacher.user)
    if kind == "parent":
        parent = ParentAccountFactory()
        link_parent_to_student(parent, student)
        user = parent.user
    else:
        user = make_student_account(student)
    client = client_for(user)

    item = _item(client, reversal)

    assert "reason" not in item and "recorded_by" not in item
    assert item["status"] == "reversal" and item["reversal_of"] == original.pk


def test_a_client_cannot_forge_a_reversal_on_create_or_update():
    student = StudentFactory()
    teacher = student.teacher.user
    original = PaymentFactory(student=student)
    client = client_for(teacher)
    base = {"student": student.pk, "amount": "10.00", "date": "2026-11-01", "method": "cash"}

    created = client.post("/api/v1/payments/", {**base, "status": "reversal"}, format="json")
    assert created.status_code == 400 and "status" in created.data

    forged_link = client.post(
        "/api/v1/payments/",
        {**base, "status": "pending", "reversal_of": original.pk, "reason": "x", "recorded_by": 1},
        format="json",
    )
    assert forged_link.status_code == 201
    row = Payment.objects.get(pk=forged_link.data["id"])
    assert row.reversal_of_id is None and row.reason == "" and row.recorded_by_id in (None, teacher.pk)

    pending = PaymentFactory(student=student, status=Payment.Status.PENDING)
    patched = client.patch(f"/api/v1/payments/{pending.pk}/", {"status": "reversal"}, format="json")
    assert patched.status_code == 400
