"""Receipts respect the tenant and the family boundary (FR-030, FR-031, FR-032)."""

import pytest
from rest_framework.test import APIClient

from apps.common.factories import StudentFactory
from apps.common.tests.helpers import client_for
from apps.common.tests.idor_world import World, build_world
from apps.payments.models import Payment, Receipt

pytestmark = pytest.mark.django_db


@pytest.fixture
def world() -> World:
    world = build_world()
    Payment.objects.update(status=Payment.Status.PAID)
    return world


def _issue(world: World, who: str, target: str):
    payment = getattr(world, target).payment
    return client_for(world.users[who]).post(
        f"/api/v1/payments/{payment.pk}/receipt/", {"language": "it"}, format="json"
    )


def _receipt_of(world: World, target: str) -> Receipt:
    owner = {"a1": "owner_a", "a2": "owner_a", "b1": "owner_b"}[target]
    assert _issue(world, owner, target).status_code == 201
    return Receipt.objects.get(payment=getattr(world, target).payment)


@pytest.mark.parametrize(
    ("attacker", "victim"),
    [
        ("teacher_a1", "a2"),
        ("teacher_a1", "b1"),
        ("owner_a", "b1"),
        ("teacher_b1", "a1"),
        ("owner_b", "a2"),
    ],
)
def test_staff_cannot_issue_receipts_outside_their_scope(world, attacker, victim):
    assert _issue(world, attacker, victim).status_code == 404
    assert not Receipt.objects.exists()


@pytest.mark.parametrize(("who", "target"), [("parent_a", "a1"), ("student_a2", "a2")])
def test_families_cannot_issue_receipts_even_for_their_own_child(world, who, target):
    assert _issue(world, who, target).status_code == 403
    assert not Receipt.objects.exists()


def test_anonymous_cannot_issue_or_read(world):
    receipt = _receipt_of(world, "a1")

    anon = APIClient()
    assert anon.post(f"/api/v1/payments/{world.a1.payment.pk}/receipt/").status_code == 401
    assert anon.get("/api/v1/receipts/").status_code == 401
    assert anon.get(f"/api/v1/receipts/{receipt.pk}/pdf/").status_code == 401


def test_a_parent_lists_and_downloads_only_their_own_childs_receipts(world):
    mine = _receipt_of(world, "a1")
    _receipt_of(world, "a2")  # a sibling family in the same studio
    _receipt_of(world, "b1")  # another studio
    client = client_for(world.users["parent_a"])

    rows = client.get("/api/v1/receipts/").data["results"]

    assert [r["id"] for r in rows] == [mine.pk]
    assert client.get(f"/api/v1/receipts/{mine.pk}/pdf/").status_code == 200
    for other in Receipt.objects.exclude(pk=mine.pk):
        assert client.get(f"/api/v1/receipts/{other.pk}/pdf/").status_code == 404


def test_another_families_parent_gets_404_on_a_childs_receipt(world):
    receipt = _receipt_of(world, "a1")

    assert (
        client_for(world.users["parent_b"]).get(f"/api/v1/receipts/{receipt.pk}/pdf/").status_code
        == 404
    )
    assert client_for(world.users["parent_b"]).get("/api/v1/receipts/").data["results"] == []


def test_an_adult_student_sees_their_own_receipt_only(world):
    own = _receipt_of(world, "a2")
    _receipt_of(world, "a1")

    rows = client_for(world.users["student_a2"]).get("/api/v1/receipts/").data["results"]

    assert [r["id"] for r in rows] == [own.pk]


def test_staff_lists_follow_their_scope(world):
    for target in ("a1", "a2", "b1"):
        _receipt_of(world, target)

    def ids(who):
        return {
            r["payment"]
            for r in client_for(world.users[who]).get("/api/v1/receipts/").data["results"]
        }

    assert ids("teacher_a1") == {world.a1.payment.pk}
    assert ids("owner_a") == {world.a1.payment.pk, world.a2.payment.pk}
    assert ids("owner_b") == {world.b1.payment.pk}
    assert (
        client_for(world.users["teacher_a1"])
        .get("/api/v1/receipts/", {"student": world.a2.student.pk})
        .data["results"]
        == []
    )


def test_after_an_erasure_the_receipt_keeps_amount_date_and_number_with_an_anonymised_name(world):
    from apps.privacy.services import anonymise_student

    receipt = _receipt_of(world, "a1")
    number = receipt.number
    anonymise_student(world.a1.student)

    row = client_for(world.users["owner_a"]).get("/api/v1/receipts/").data["results"][0]
    pdf = client_for(world.users["owner_a"]).get(f"/api/v1/receipts/{receipt.pk}/pdf/")

    assert row["number"] == number and row["amount"] == "50.00" and row["date"]
    assert "cancellato" in row["student_name"] and "Student" not in row["student_name"]
    assert pdf.status_code == 200 and len(pdf.content) > 500


def test_a_student_of_another_studio_with_no_receipts_sees_an_empty_list():
    student = StudentFactory()
    assert client_for(student.teacher.user).get("/api/v1/receipts/").data["results"] == []
