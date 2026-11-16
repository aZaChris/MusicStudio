"""Il registro quadra con rimborsi, contestazioni e storni a mano insieme (US3, fase 9, SC-005)."""

import csv
import datetime
import io
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.common.factories import PaymentFactory, StudentFactory, TeacherFactory, make_reversal
from apps.common.tenancy import resolve_tenant
from apps.common.tests.helpers import client_for
from apps.payments import selectors
from apps.payments.models import Payment
from apps.payments.services import add_provider_reversal

pytestmark = pytest.mark.django_db


def _refund(payment: Payment, amount: str, ref: str, cause: str = "refund") -> None:
    add_provider_reversal(payment, amount=Decimal(amount), cause=cause, provider_ref=ref)


def _month_start():
    return timezone.localdate().replace(day=1)


def _world():
    teacher = TeacherFactory()
    student = StudentFactory(teacher=teacher)
    today = timezone.localdate()

    def paid(amount: str, method: str) -> Payment:
        return PaymentFactory(
            student=student, amount=amount, method=method, date=today, status="paid"
        )

    return teacher, student, today, paid


def test_the_totals_match_a_hand_calculation_with_every_kind_of_reversal():
    teacher, student, today, paid = _world()
    paid("100.00", "cash")  # nessuna correzione
    card_partial = paid("200.00", "card")
    _refund(card_partial, "50.00", "re_1")  # rimborso parziale
    bank = paid("80.00", "bank_transfer")
    make_reversal(bank, date=today)  # storno a mano, intero
    card_lost = paid("120.00", "card")
    _refund(card_lost, "120.00", "dp_1", cause="dispute")  # contestazione persa
    PaymentFactory(student=student, amount="40.00", method="cash", date=today, status="pending")

    summary = selectors.register_summary(resolve_tenant(teacher.user), today, today)

    by = {line["method"]: line for line in summary["by_method"]}
    assert (by["cash"]["received"], by["cash"]["reversed"], by["cash"]["net"]) == (
        Decimal("100.00"), Decimal("0.00"), Decimal("100.00"),
    )  # fmt: skip
    assert (by["card"]["received"], by["card"]["reversed"], by["card"]["net"]) == (
        Decimal("320.00"), Decimal("170.00"), Decimal("150.00"),
    )  # fmt: skip
    assert (by["bank_transfer"]["received"], by["bank_transfer"]["reversed"]) == (
        Decimal("80.00"), Decimal("80.00"),
    )  # fmt: skip
    totals = summary["totals"]
    assert (totals["received"], totals["reversed"], totals["net"]) == (
        Decimal("500.00"), Decimal("250.00"), Decimal("250.00"),
    )  # fmt: skip
    assert summary["counts"] == {"paid": 4, "pending": 1, "overdue": 0, "reversal": 3}


def test_a_refund_made_later_belongs_to_the_month_it_was_made_not_the_payments():
    teacher = TeacherFactory()
    student = StudentFactory(teacher=teacher)
    last_month_day = _month_start() - datetime.timedelta(days=5)
    old = PaymentFactory(student=student, amount="90.00", method="card", date=last_month_day)
    _refund(old, "90.00", "re_late")  # datato oggi
    ctx = resolve_tenant(teacher.user)
    last_start = last_month_day.replace(day=1)

    closed = selectors.register_summary(
        ctx, last_start, _month_start() - datetime.timedelta(days=1)
    )
    current = selectors.register_summary(ctx, _month_start(), timezone.localdate())

    # Il mese chiuso non cambia: mostra ancora l'incasso e nessuno storno.
    assert (closed["totals"]["received"], closed["totals"]["reversed"]) == (
        Decimal("90.00"), Decimal("0.00"),
    )  # fmt: skip
    assert (current["totals"]["received"], current["totals"]["reversed"]) == (
        Decimal("0.00"), Decimal("90.00"),
    )  # fmt: skip


def test_the_csv_carries_the_cause_and_the_provider_reference():
    teacher, _, today, paid = _world()
    payment = paid("100.00", "card")
    _refund(payment, "30.00", "re_csv")
    make_reversal(paid("10.00", "cash"), date=today)

    res = client_for(teacher.user).get(
        f"/api/v1/payments/register/export/csv/?date_from={today}&date_to={today}"
    )

    rows = list(csv.DictReader(io.StringIO(res.content.decode("utf-8-sig")), delimiter=";"))
    refund = next(r for r in rows if r["provider_ref"] == "re_csv")
    assert (refund["cause"], refund["status"], refund["amount"]) == ("refund", "reversal", "-30.00")
    manual = next(r for r in rows if r["status"] == "reversal" and r["provider_ref"] == "")
    assert manual["cause"] == "manual"
    original = next(r for r in rows if r["status"] == "paid" and r["amount"] == "100.00")
    assert original["cause"] == "" and original["provider_ref"] == ""


def test_the_receipt_is_cancelled_only_when_the_payment_is_fully_reversed():
    teacher, _, _, paid = _world()
    payment = paid("100.00", "card")
    client = client_for(teacher.user)
    assert (
        client.post(
            f"/api/v1/payments/{payment.pk}/receipt/", {"language": "en"}, format="json"
        ).status_code
        == 201
    )

    def cancelled() -> bool:
        return client.get("/api/v1/receipts/").data["results"][0]["cancelled"]

    assert cancelled() is False
    _refund(payment, "40.00", "re_1")
    assert cancelled() is False  # un rimborso parziale non annulla la ricevuta
    _refund(payment, "60.00", "re_2")
    assert cancelled() is True  # tutto stornato: annullata, con lo stesso numero
