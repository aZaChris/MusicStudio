"""A paid entry is final; a mistake is fixed by a reversal (US1, FR-001..FR-008)."""

import datetime

import pytest
from django.utils import timezone

from apps.audit.models import AuditEntry
from apps.common.factories import PackageFactory, PaymentFactory, StudentFactory, make_reversal
from apps.common.tests.helpers import client_for
from apps.payments.models import Payment

pytestmark = pytest.mark.django_db


def _setup(**payment_fields):
    student = StudentFactory()
    payment = PaymentFactory(student=student, **payment_fields)
    return student, payment, client_for(student.teacher.user)


@pytest.mark.parametrize(
    "change",
    [
        {"amount": "99.00"},
        {"date": "2026-01-02"},
        {"method": "bank_transfer"},
        {"status": "pending"},
        {"status": "paid"},
    ],
)
def test_patch_of_a_paid_entry_is_refused_and_changes_nothing(change):
    _, payment, client = _setup()
    before = Payment.objects.values().get(pk=payment.pk)

    res = client.patch(f"/api/v1/payments/{payment.pk}/", change, format="json")

    assert res.status_code == 409 and res.data["code"] == "payment_final"
    assert Payment.objects.values().get(pk=payment.pk) == before


def test_put_and_student_or_package_change_of_a_paid_entry_are_refused():
    student, payment, client = _setup()
    other = StudentFactory(teacher=student.teacher)
    package = PackageFactory(student=student)
    body = {
        "student": student.pk,
        "amount": "40.00",
        "date": str(payment.date),
        "method": "cash",
        "status": "paid",
    }

    assert client.put(f"/api/v1/payments/{payment.pk}/", body, format="json").status_code == 409
    res = client.patch(f"/api/v1/payments/{payment.pk}/", {"student": other.pk}, format="json")
    assert res.status_code == 409
    res = client.patch(f"/api/v1/payments/{payment.pk}/", {"package": package.pk}, format="json")
    assert res.status_code == 409


def test_a_paid_entry_cannot_be_deleted():
    _, payment, client = _setup()
    res = client.delete(f"/api/v1/payments/{payment.pk}/")
    assert res.status_code == 409 and res.data["code"] == "payment_final"
    assert Payment.objects.filter(pk=payment.pk).exists()


def test_a_reversal_entry_is_final_too():
    _, payment, client = _setup()
    reversal = make_reversal(payment)
    assert (
        client.patch(f"/api/v1/payments/{reversal.pk}/", {"amount": "1"}, format="json").status_code
        == 409
    )
    assert client.delete(f"/api/v1/payments/{reversal.pk}/").status_code == 409


@pytest.mark.parametrize("status", ["pending", "overdue"])
def test_pending_and_overdue_entries_stay_editable_and_removable(status):
    _, payment, client = _setup(status=status)

    edited = client.patch(f"/api/v1/payments/{payment.pk}/", {"amount": "55.00"}, format="json")
    assert edited.status_code == 200 and edited.data["amount"] == "55.00"

    deleted = client.delete(f"/api/v1/payments/{payment.pk}/")
    assert deleted.status_code == 204
    assert not Payment.objects.filter(pk=payment.pk).exists()
    entry = AuditEntry.objects.get(action="payment.delete")
    assert entry.target_id == payment.pk
    assert entry.metadata == {"method": "cash", "amount": "55.00", "status": status}


def test_marking_a_pending_entry_paid_still_works():
    _, payment, client = _setup(status="pending")
    res = client.patch(f"/api/v1/payments/{payment.pk}/", {"status": "paid"}, format="json")
    assert res.status_code == 200 and res.data["status"] == "paid"


def test_reversing_creates_a_linked_entry_and_leaves_the_original_untouched():
    student, payment, client = _setup()
    before = Payment.objects.values().get(pk=payment.pk)

    res = client.post(
        f"/api/v1/payments/{payment.pk}/reverse/", {"reason": "wrong student"}, format="json"
    )

    assert res.status_code == 201
    assert res.data["status"] == "reversal" and res.data["reversal_of"] == payment.pk
    assert res.data["reason"] == "wrong student" and res.data["refund"] is False
    assert res.data["recorded_by"] == student.teacher.user.pk
    assert res.data["amount"] == "40.00" and res.data["method"] == "cash"
    assert Payment.objects.values().get(pk=payment.pk) == before  # byte-identical
    listed = client.get(f"/api/v1/payments/?student={student.pk}").data["results"]
    original = next(r for r in listed if r["id"] == payment.pk)
    assert original["reversed"] is True and original["reversal_id"] == res.data["id"]


def test_the_reversal_is_dated_today_never_backdated():
    _, payment, client = _setup(date=datetime.date(2026, 1, 5))
    res = client.post(f"/api/v1/payments/{payment.pk}/reverse/", {"reason": "x"}, format="json")
    assert res.data["date"] == str(timezone.localdate())


def test_reversal_is_audited_with_actor_studio_and_no_reason_text():
    student, payment, client = _setup()
    res = client.post(
        f"/api/v1/payments/{payment.pk}/reverse/", {"reason": "very private"}, format="json"
    )
    entry = AuditEntry.objects.get(action="payment.reverse")
    assert (entry.actor_id, entry.studio_id) == (student.teacher.user.pk, student.studio_id)
    assert entry.target_id == res.data["id"]
    assert entry.metadata == {"method": "cash", "amount": "40.00"}


@pytest.mark.parametrize("status", ["pending", "overdue"])
def test_reversing_an_unpaid_entry_is_refused(status):
    _, payment, client = _setup(status=status)
    res = client.post(f"/api/v1/payments/{payment.pk}/reverse/", {"reason": "x"}, format="json")
    assert res.status_code == 409 and res.data["code"] == "not_paid"


def test_a_second_reversal_and_a_reversal_of_a_reversal_are_refused():
    _, payment, client = _setup()
    first = client.post(f"/api/v1/payments/{payment.pk}/reverse/", {"reason": "x"}, format="json")
    again = client.post(f"/api/v1/payments/{payment.pk}/reverse/", {"reason": "y"}, format="json")
    of_reversal = client.post(
        f"/api/v1/payments/{first.data['id']}/reverse/", {"reason": "z"}, format="json"
    )
    assert again.status_code == 409 and again.data["code"] == "already_reversed"
    assert of_reversal.status_code == 409 and of_reversal.data["code"] == "is_reversal"
    assert Payment.objects.filter(reversal_of=payment).count() == 1


@pytest.mark.parametrize("reason", [None, "", "   ", "x" * 201])
def test_the_reason_is_required_and_short(reason):
    _, payment, client = _setup()
    body = {} if reason is None else {"reason": reason}
    res = client.post(f"/api/v1/payments/{payment.pk}/reverse/", body, format="json")
    assert res.status_code == 400 and "reason" in res.data
    assert not Payment.objects.filter(reversal_of=payment).exists()


def test_a_card_entry_reversal_says_no_money_is_returned():
    _, payment, client = _setup(method="card")
    res = client.post(f"/api/v1/payments/{payment.pk}/reverse/", {"reason": "x"}, format="json")
    assert res.status_code == 201 and res.data["refund"] is False and res.data["method"] == "card"


def test_the_creator_is_recorded_on_manual_payments():
    student = StudentFactory()
    client = client_for(student.teacher.user)
    res = client.post(
        "/api/v1/payments/",
        {"student": student.pk, "amount": "10.00", "date": "2026-11-01", "method": "cash"},
        format="json",
    )
    assert res.data["recorded_by"] == student.teacher.user.pk


def test_the_list_filters_by_period_and_method():
    student = StudentFactory()
    client = client_for(student.teacher.user)
    PaymentFactory(student=student, date="2026-10-31", method="cash")
    inside = PaymentFactory(student=student, date="2026-11-15", method="bank_transfer")
    PaymentFactory(student=student, date="2026-12-01", method="bank_transfer")

    res = client.get("/api/v1/payments/?date_from=2026-11-01&date_to=2026-11-30")
    assert [r["id"] for r in res.data["results"]] == [inside.pk]
    res = client.get("/api/v1/payments/?method=cash")
    assert len(res.data["results"]) == 1
