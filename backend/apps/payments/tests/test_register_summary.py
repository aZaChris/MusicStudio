"""Register totals match a hand calculation, and a closed month never changes (US2, SC-002)."""

import datetime
from decimal import Decimal
from unittest import mock

import pytest

from apps.common.factories import PaymentFactory, StudentFactory, make_reversal
from apps.common.tests.helpers import client_for
from apps.payments.models import Payment

pytestmark = pytest.mark.django_db

URL = "/api/v1/payments/register/summary/"


def _world():
    """Entries around November 2026, with the expected figures worked out by hand below."""
    student = StudentFactory()
    pay = lambda amount, date, method, **kw: PaymentFactory(  # noqa: E731
        student=student, amount=amount, date=date, method=method, **kw
    )
    pay("40.00", "2026-11-02", "cash")  # reversed on 3 December
    pay("60.00", "2026-11-10", "cash")
    bank = pay("100.00", "2026-11-10", "bank_transfer")  # reversed on 20 November
    pay("20.00", "2026-11-30", "manual_entry")
    pay("30.00", "2026-11-15", "card")
    pay("15.00", "2026-11-05", "cash", status="pending")
    pay("25.00", "2026-11-06", "bank_transfer", status="overdue")
    pay("50.00", "2026-10-31", "cash")  # the day before November
    december = pay("70.00", "2026-12-01", "cash")
    make_reversal(Payment.objects.get(amount="40.00"), date=datetime.date(2026, 12, 3))
    make_reversal(bank, date=datetime.date(2026, 11, 20))
    return student, december


def _summary(client, start, end):
    res = client.get(URL, {"date_from": start, "date_to": end})
    assert res.status_code == 200, res.data
    return res.data


def _by_method(data):
    return {line["method"]: line for line in data["by_method"]}


def test_november_totals_overall_and_per_method():
    student, _ = _world()
    data = _summary(client_for(student.teacher.user), "2026-11-01", "2026-11-30")

    # received: cash 40+60, bank 100, manual 20, card 30; reversed: only the bank 100 (20 Nov)
    assert data["totals"] == {"received": "250.00", "reversed": "100.00", "net": "150.00"}
    lines = _by_method(data)
    assert (lines["cash"]["received"], lines["cash"]["reversed"], lines["cash"]["net"]) == (
        "100.00",
        "0.00",
        "100.00",
    )
    assert (
        lines["bank_transfer"]["net"] == "0.00" and lines["bank_transfer"]["reversed"] == "100.00"
    )
    assert lines["manual_entry"]["net"] == "20.00" and lines["card"]["net"] == "30.00"
    # pending and overdue are counted but never summed
    assert data["counts"] == {"paid": 5, "pending": 1, "overdue": 1, "reversal": 1}
    assert data["period"] == {"from": "2026-11-01", "to": "2026-11-30"}


def test_a_closed_month_never_changes_the_reversal_falls_in_december():
    student, _ = _world()
    client = client_for(student.teacher.user)

    november = _summary(client, "2026-11-01", "2026-11-30")
    december = _summary(client, "2026-12-01", "2026-12-31")

    # The 3 December reversal of a November payment: November still counts the original as
    # received, and does not count the reversal; December counts the reversal.
    assert _by_method(november)["cash"]["received"] == "100.00"
    assert _by_method(december)["cash"]["received"] == "70.00"
    assert _by_method(december)["cash"]["reversed"] == "40.00"
    assert december["totals"] == {"received": "70.00", "reversed": "40.00", "net": "30.00"}


def test_every_method_is_listed_even_with_zero_and_the_sum_of_lines_is_the_total():
    student, _ = _world()
    data = _summary(client_for(student.teacher.user), "2026-11-01", "2026-11-30")

    assert [line["method"] for line in data["by_method"]] == [
        "cash",
        "bank_transfer",
        "manual_entry",
        "card",
    ]
    assert sum(Decimal(line["net"]) for line in data["by_method"]) == Decimal(data["totals"]["net"])


def test_an_empty_period_is_zeros_not_an_error():
    student = StudentFactory()
    data = _summary(client_for(student.teacher.user), "2030-01-01", "2030-01-31")

    assert data["totals"] == {"received": "0.00", "reversed": "0.00", "net": "0.00"}
    assert data["counts"] == {"paid": 0, "pending": 0, "overdue": 0, "reversal": 0}
    assert len(data["by_method"]) == 4


def test_without_parameters_the_summary_is_the_current_month():
    student = StudentFactory()
    today = datetime.date(2026, 11, 15)
    with mock.patch("django.utils.timezone.now") as now:
        now.return_value = datetime.datetime(2026, 11, 15, 12, 0, tzinfo=datetime.UTC)
        PaymentFactory(student=student, date="2026-11-01", amount="10.00")
        PaymentFactory(student=student, date="2026-10-31", amount="99.00")
        res = client_for(student.teacher.user).get(URL)

    assert res.data["period"] == {"from": "2026-11-01", "to": "2026-11-30"}
    assert res.data["totals"]["received"] == "10.00"
    assert today.month == 11


def test_a_bad_period_is_a_400():
    student = StudentFactory()
    client = client_for(student.teacher.user)

    assert client.get(URL, {"date_from": "2026-11-30", "date_to": "2026-11-01"}).status_code == 400
    assert client.get(URL, {"date_from": "not-a-date"}).status_code == 400


def test_the_reversal_is_dated_in_local_time_across_midnight():
    # 23:30 UTC on 30 November is 00:30 on 1 December in Rome (UTC+1): the reversal belongs
    # to the local day, so it must land in December and leave November untouched.
    student = StudentFactory()
    payment = PaymentFactory(student=student, date="2026-11-10", amount="40.00")
    client = client_for(student.teacher.user)

    with mock.patch("django.utils.timezone.now") as now:
        now.return_value = datetime.datetime(2026, 11, 30, 23, 30, tzinfo=datetime.UTC)
        res = client.post(f"/api/v1/payments/{payment.pk}/reverse/", {"reason": "x"}, format="json")

    assert res.data["date"] == "2026-12-01"
    assert _summary(client, "2026-11-01", "2026-11-30")["totals"]["reversed"] == "0.00"
    assert _summary(client, "2026-12-01", "2026-12-31")["totals"]["reversed"] == "40.00"
