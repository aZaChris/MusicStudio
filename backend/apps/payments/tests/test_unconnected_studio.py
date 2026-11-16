"""Uno studio che non collega nessun conto lavora come nella fase 8 (US4, fase 9, SC-008)."""

import datetime

import pytest

from apps.common.factories import (
    PackageFactory,
    ParentAccountFactory,
    StudentFactory,
    StudioPaymentAccountFactory,
    link_parent_to_student,
)
from apps.common.tests.helpers import client_for, make_studio_owner
from apps.payments.models import Payment

pytestmark = pytest.mark.django_db
IBAN = "IT60X0542811101000000123456"


@pytest.fixture(params=[True, False], ids=["switch-on", "switch-off"])
def switch(request, settings):
    # Il risultato per uno studio senza conto è lo stesso con l'interruttore acceso o spento.
    settings.ONLINE_PAYMENTS_ENABLED = request.param
    return request.param


def test_the_account_is_not_started_or_not_there_at_all(switch):
    owner = make_studio_owner()

    res = client_for(owner.user).get("/api/v1/payment-account/")

    if switch:
        assert res.status_code == 200 and res.data["state"] == "not_started"
        assert res.data["can_accept_online"] is False
    else:
        assert res.status_code == 404


def test_no_package_is_payable_online_and_checkout_refuses(switch):
    owner = make_studio_owner()
    package = PackageFactory(student=StudentFactory(teacher=owner))
    client = client_for(owner.user)

    assert client.get(f"/api/v1/packages/{package.pk}/").data["can_pay_online"] is False
    res = client.post(f"/api/v1/packages/{package.pk}/checkout/")
    assert res.status_code == 409 and res.data["code"] == "online_payments_not_available"


def test_the_whole_phase_8_walk_works_without_a_connected_account(switch):
    owner = make_studio_owner()
    student = StudentFactory(teacher=owner)
    package = PackageFactory(student=student, price="120.00")
    parent = ParentAccountFactory()
    link_parent_to_student(parent, student)
    client = client_for(owner.user)
    today = datetime.date.today().isoformat()

    # Registro: un pagamento a mano, uno storno, i totali e l'esportazione.
    made = client.post(
        "/api/v1/payments/",
        {
            "student": student.pk,
            "amount": "40.00",
            "date": today,
            "method": "cash",
            "status": "paid",
        },
        format="json",
    )
    assert made.status_code == 201
    other = client.post(
        "/api/v1/payments/",
        {
            "student": student.pk,
            "amount": "25.00",
            "date": today,
            "method": "cash",
            "status": "paid",
        },
        format="json",
    )
    reversal = client.post(
        f"/api/v1/payments/{other.data['id']}/reverse/", {"reason": "mistake"}, format="json"
    )
    assert reversal.status_code == 201
    summary = client.get(
        f"/api/v1/payments/register/summary/?date_from={today}&date_to={today}"
    ).data
    totals = summary["totals"]
    assert (totals["received"], totals["reversed"], totals["net"]) == ("65.00", "25.00", "40.00")
    csv = client.get(f"/api/v1/payments/register/export/csv/?date_from={today}&date_to={today}")
    assert csv.status_code == 200

    # Istruzioni di pagamento: il titolare le salva e il genitore le vede (pacchetto aperto).
    saved = client.put(
        "/api/v1/payment-instructions/",
        {"account_holder": "Studio Armonia", "iban": IBAN},
        format="json",
    )
    assert saved.status_code == 200
    seen = client_for(parent.user).get("/api/v1/payment-instructions/open/").data
    assert [i["iban"] for i in seen] == [IBAN] and seen[0]["student_ids"] == [student.pk]
    assert package.pk  # il pacchetto è ancora da pagare: da qui le istruzioni

    # Ricevuta non fiscale per un pagamento incassato.
    receipt = client.post(
        f"/api/v1/payments/{made.data['id']}/receipt/", {"language": "it"}, format="json"
    )
    assert receipt.status_code == 201 and receipt.data["number"].endswith("-0001")


def test_connecting_an_account_later_leaves_earlier_entries_untouched(settings):
    settings.ONLINE_PAYMENTS_ENABLED = True
    owner = make_studio_owner()
    student = StudentFactory(teacher=owner)
    client = client_for(owner.user)
    client.post(
        "/api/v1/payments/",
        {
            "student": student.pk,
            "amount": "40.00",
            "date": "2026-11-01",
            "method": "cash",
            "status": "paid",
        },
        format="json",
    )
    before = list(Payment.objects.values())

    StudioPaymentAccountFactory(studio=owner.studio)

    assert list(Payment.objects.values()) == before
    rows = client.get("/api/v1/payments/").data["results"]
    assert [(r["amount"], r["status"], r["method"]) for r in rows] == [("40.00", "paid", "cash")]
