"""Export behaviour: period rules, audit, formula safety, throttle (US2, FR-014..FR-017)."""

import csv
import io

import pytest

from apps.audit.models import AuditEntry
from apps.common.factories import PaymentFactory, StudentFactory, make_reversal
from apps.common.tests.helpers import client_for
from apps.payments.models import Payment

pytestmark = pytest.mark.django_db

CSV = "/api/v1/payments/register/export/csv/"
PDF = "/api/v1/payments/register/export/pdf/"
YEAR = {"date_from": "2026-01-01", "date_to": "2026-12-31"}  # 365 days: allowed


def _rows(res):
    return list(csv.DictReader(io.StringIO(res.content.decode("utf-8-sig")), delimiter=";"))


@pytest.mark.parametrize("url", [CSV, PDF])
def test_a_period_over_a_year_is_refused_with_a_clear_code(url):
    client = client_for(StudentFactory().teacher.user)

    res = client.get(url, {"date_from": "2026-01-01", "date_to": "2027-01-02"})  # 367 days

    assert res.status_code == 400 and res.data["code"] == "period_too_long"


@pytest.mark.parametrize("url", [CSV, PDF])
def test_a_leap_year_and_a_full_year_are_accepted(url):
    client = client_for(StudentFactory().teacher.user)

    assert client.get(url, YEAR).status_code == 200
    assert client.get(url, {"date_from": "2028-01-01", "date_to": "2028-12-31"}).status_code == 200


@pytest.mark.parametrize("url", [CSV, PDF])
def test_both_dates_are_required_and_must_be_in_order(url):
    client = client_for(StudentFactory().teacher.user)

    assert client.get(url).status_code == 400
    assert client.get(url, {"date_from": "2026-01-01"}).status_code == 400
    assert client.get(url, {"date_from": "2026-02-01", "date_to": "2026-01-01"}).status_code == 400


def test_csv_has_one_row_per_entry_with_signed_amounts_and_statuses():
    student = StudentFactory()
    paid = PaymentFactory(student=student, date="2026-11-02")
    PaymentFactory(student=student, date="2026-11-03", status=Payment.Status.PENDING)
    make_reversal(paid, date="2026-11-20", reason="wrong student")
    res = client_for(student.teacher.user).get(
        CSV, {"date_from": "2026-11-01", "date_to": "2026-11-30"}
    )

    rows = _rows(res)

    assert res.status_code == 200 and res["Content-Type"].startswith("text/csv")
    assert (
        "attachment" in res["Content-Disposition"]
        and "2026-11-01_2026-11-30" in res["Content-Disposition"]
    )
    assert [(r["date"], r["status"], r["amount"]) for r in rows] == [
        ("2026-11-02", "reversed", "40.00"),
        ("2026-11-03", "pending", "40.00"),
        ("2026-11-20", "reversal", "-40.00"),
    ]
    assert rows[2]["reason"] == "wrong student" and rows[2]["reversal_of"] == str(paid.pk)


def test_a_formula_in_a_student_name_is_neutralised_in_the_response_body():
    student = StudentFactory(first_name="=cmd|' /C calc'!A0", last_name="Evil")
    PaymentFactory(student=student, date="2026-11-02")

    res = client_for(student.teacher.user).get(
        CSV, {"date_from": "2026-11-01", "date_to": "2026-11-30"}
    )

    assert _rows(res)[0]["student"].startswith("'=cmd|")
    assert b";=cmd" not in res.content and b"\n=cmd" not in res.content


@pytest.mark.parametrize(("url", "fmt"), [(CSV, "csv"), (PDF, "pdf")])
def test_each_export_is_audited_with_the_period_and_the_count_only(url, fmt):
    student = StudentFactory(last_name="Segretissimo")
    PaymentFactory(student=student, date="2026-11-02")
    PaymentFactory(student=student, date="2026-11-03")

    res = client_for(student.teacher.user).get(
        url, {"date_from": "2026-11-01", "date_to": "2026-11-30"}
    )

    assert res.status_code == 200
    entry = AuditEntry.objects.get(action="register.export")
    assert entry.actor_id == student.teacher.user.pk and entry.studio_id == student.studio_id
    assert entry.metadata == {"format": fmt, "from": "2026-11-01", "to": "2026-11-30", "rows": 2}
    assert "Segretissimo" not in str(entry.metadata)


def test_the_pdf_is_an_attachment_with_the_studio_name():
    student = StudentFactory()
    res = client_for(student.teacher.user).get(PDF, YEAR)

    assert res.status_code == 200 and res["Content-Type"] == "application/pdf"
    assert res.content.startswith(b"%PDF")
    assert "register-2026-01-01_2026-12-31.pdf" in res["Content-Disposition"]


def test_exports_are_throttled_per_user():
    client = client_for(StudentFactory().teacher.user)

    codes = [client.get(CSV, YEAR).status_code for _ in range(6)]

    assert codes == [200] * 5 + [429]
    # Another user has their own counter.
    assert client_for(StudentFactory().teacher.user).get(PDF, YEAR).status_code == 200


def test_the_export_throttle_scope_is_configured_in_production_settings():
    # A throttle scope without a rate does not fail loudly: the fail-open throttle would let the
    # exports through unlimited. This keeps base.py (the production rates) honest.
    from config.settings import base

    assert "register_export" in base.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
