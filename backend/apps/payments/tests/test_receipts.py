"""Receipts: who can get one, the number, idempotency, language, the cancelled mark (US4)."""

import datetime
from unittest import mock

import pytest

from apps.audit.models import AuditEntry
from apps.common.factories import (
    PaymentFactory,
    StudentFactory,
    TeacherFactory,
    make_reversal,
)
from apps.common.tests.helpers import client_for, make_studio_owner
from apps.payments import pdf
from apps.payments.models import Payment, Receipt

pytestmark = pytest.mark.django_db

REAL_RECEIPT_PDF = pdf.receipt_pdf  # captured before any test patches the module attribute


def _issue(client, payment, **body):
    return client.post(f"/api/v1/payments/{payment.pk}/receipt/", body, format="json")


def _setup(**fields):
    student = StudentFactory()
    return student, PaymentFactory(student=student, **fields), client_for(student.teacher.user)


@pytest.mark.parametrize("status", ["pending", "overdue"])
def test_an_unpaid_entry_has_no_receipt(status):
    _, payment, client = _setup(status=status)

    res = _issue(client, payment)

    assert res.status_code == 409 and res.data["code"] == "not_paid"
    assert not Receipt.objects.exists()


def test_a_reversal_entry_has_no_receipt():
    _, payment, client = _setup()
    reversal = make_reversal(payment)

    res = _issue(client, reversal)

    assert res.status_code == 409 and res.data["code"] == "is_reversal"


def test_the_first_issue_is_201_and_a_repeat_is_200_with_the_same_number_and_language():
    student, payment, client = _setup()

    first = _issue(client, payment, language="en")
    again = _issue(client, payment, language="it")  # the language chosen first is kept

    year = datetime.date.today().year
    assert first.status_code == 201 and again.status_code == 200
    assert first.data["number"] == again.data["number"] == f"{year}-0001"
    assert first.data["language"] == again.data["language"] == "en"
    assert first.data["id"] == again.data["id"] and Receipt.objects.count() == 1
    assert first.data["student_name"] == student.full_name
    assert (first.data["amount"], first.data["method"], first.data["cancelled"]) == (
        "40.00",
        "cash",
        False,
    )


def test_the_language_defaults_to_the_portal_language_of_the_issuer():
    student, payment, client = _setup()
    student.teacher.user.preferred_language = "en"
    student.teacher.user.save()

    assert _issue(client, payment).data["language"] == "en"


def test_a_bad_language_is_a_400():
    _, payment, client = _setup()

    assert _issue(client, payment, language="fr").status_code == 400
    assert not Receipt.objects.exists()


def test_ten_receipts_in_one_studio_are_0001_to_0010_and_studios_are_independent():
    owner = make_studio_owner()
    teacher = TeacherFactory(studio=owner.studio)
    student = StudentFactory(teacher=teacher)
    client = client_for(owner.user)
    numbers = [_issue(client, PaymentFactory(student=student)).data["number"] for _ in range(10)]

    year = datetime.date.today().year
    assert numbers == [f"{year}-{n:04d}" for n in range(1, 11)]
    # Another studio starts at 0001 on its own.
    _, other_payment, other_client = _setup()
    assert _issue(other_client, other_payment).data["number"] == f"{year}-0001"


def test_numbering_restarts_in_a_new_calendar_year():
    student, first, client = _setup()
    second = PaymentFactory(student=student)

    with mock.patch("django.utils.timezone.now") as now:
        now.return_value = datetime.datetime(2026, 12, 31, 12, 0, tzinfo=datetime.UTC)
        a = _issue(client, first).data["number"]
        now.return_value = datetime.datetime(2027, 1, 2, 12, 0, tzinfo=datetime.UTC)
        b = _issue(client, second).data["number"]
        c = _issue(client, PaymentFactory(student=student)).data["number"]

    assert (a, b, c) == ("2026-0001", "2027-0001", "2027-0002")


def test_a_year_is_the_local_one_across_new_years_eve_in_rome():
    # 23:30 UTC on 31 December is 00:30 on 1 January in Rome: the number belongs to the new year.
    _, payment, client = _setup()

    with mock.patch("django.utils.timezone.now") as now:
        now.return_value = datetime.datetime(2026, 12, 31, 23, 30, tzinfo=datetime.UTC)
        number = _issue(client, payment).data["number"]

    assert number == "2027-0001"


def test_issuing_is_audited_once_with_the_number_only():
    _, payment, client = _setup()

    first = _issue(client, payment)
    _issue(client, payment)

    entries = AuditEntry.objects.filter(action="receipt.issue")
    assert entries.count() == 1
    assert entries[0].metadata == {"number": first.data["number"]}
    assert entries[0].target_id == first.data["id"]


def test_the_number_shows_on_the_payment_and_in_the_csv():
    student, payment, client = _setup(date="2026-11-03")
    number = _issue(client, payment).data["number"]

    listed = client.get("/api/v1/payments/").data["results"]
    csv = client.get(
        "/api/v1/payments/register/export/csv/",
        {"date_from": "2026-11-01", "date_to": "2026-11-30"},
    )

    assert next(r for r in listed if r["id"] == payment.pk)["receipt_number"] == number
    assert number in csv.content.decode("utf-8-sig")
    plain = PaymentFactory(student=student)
    assert (
        next(r for r in client.get("/api/v1/payments/").data["results"] if r["id"] == plain.pk)[
            "receipt_number"
        ]
        is None
    )


def test_the_same_data_gives_the_same_pdf_and_a_reversal_marks_it_cancelled():
    _, payment, client = _setup()
    receipt_id = _issue(client, payment).data["id"]
    url = f"/api/v1/receipts/{receipt_id}/pdf/"

    first, second = client.get(url), client.get(url)

    assert first.status_code == 200 and first["Content-Type"] == "application/pdf"
    assert first.content == second.content  # FR-027: same number, same content
    assert f"receipt-{Receipt.objects.get().number}.pdf" in first["Content-Disposition"]

    make_reversal(Payment.objects.get(pk=payment.pk))
    seen = {}

    def spy(**kwargs):
        seen.update(kwargs)
        return REAL_RECEIPT_PDF(**{**kwargs, "compress": False})

    with mock.patch("apps.payments.receipt_views.pdf.receipt_pdf", side_effect=spy):
        cancelled = client.get(url)

    assert cancelled.status_code == 200 and seen["cancelled"] is True
    assert b"CANCELLED" in cancelled.content or b"ANNULLATA" in cancelled.content
    assert client.get("/api/v1/receipts/").data["results"][0]["cancelled"] is True
    # The receipt keeps its number after the reversal.
    assert Receipt.objects.get().number == f"{datetime.date.today().year}-0001"


def test_the_pdf_carries_the_receipts_language():
    _, payment, client = _setup()
    receipt_id = _issue(client, payment, language="it").data["id"]
    seen = {}

    def spy(**kwargs):
        seen.update(kwargs)
        return REAL_RECEIPT_PDF(**{**kwargs, "compress": False})

    with mock.patch("apps.payments.receipt_views.pdf.receipt_pdf", side_effect=spy):
        res = client.get(f"/api/v1/receipts/{receipt_id}/pdf/")

    assert seen["language"] == "it" and b"Ricevuta di pagamento" in res.content
    assert seen["cancelled"] is False
