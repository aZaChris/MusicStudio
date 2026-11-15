"""Reversing, editing and deleting respect the tenant (US1, FR-032, Principle I).

The shared IDOR suite uses pending payments; here every target is *paid*, so a bug that
let an attacker through would really create a reversal.
"""

import pytest

from apps.common.tests.helpers import client_for
from apps.common.tests.idor_world import World, build_world
from apps.payments.models import Payment

pytestmark = pytest.mark.django_db


@pytest.fixture
def world() -> World:
    world = build_world()
    Payment.objects.update(status=Payment.Status.PAID)
    return world


def _reverse(world: World, who: str, target: str):
    payment = getattr(world, target).payment
    return client_for(world.users[who]).post(
        f"/api/v1/payments/{payment.pk}/reverse/", {"reason": "x"}, format="json"
    )


@pytest.mark.parametrize(
    ("attacker", "victim"),
    [
        ("teacher_a1", "a2"),  # colleague of the same studio
        ("teacher_a1", "b1"),
        ("teacher_a2", "a1"),
        ("owner_a", "b1"),  # owner of another studio
        ("teacher_b1", "a1"),
        ("owner_b", "a2"),
    ],
)
def test_staff_of_another_scope_gets_404_and_nothing_is_created(world, attacker, victim):
    res = _reverse(world, attacker, victim)

    assert res.status_code == 404
    assert not Payment.objects.filter(status=Payment.Status.REVERSAL).exists()


@pytest.mark.parametrize("who", ["parent_a", "student_a2"])
def test_parents_and_adult_students_get_403(world, who):
    victim = "a1" if who == "parent_a" else "a2"  # their own family's payment

    res = _reverse(world, who, victim)

    assert res.status_code == 403
    assert not Payment.objects.filter(status=Payment.Status.REVERSAL).exists()


def test_anonymous_gets_401(world):
    from rest_framework.test import APIClient

    res = APIClient().post(
        f"/api/v1/payments/{world.a1.payment.pk}/reverse/", {"reason": "x"}, format="json"
    )
    assert res.status_code == 401


@pytest.mark.parametrize(
    ("who", "target"),
    [("owner_a", "a1"), ("owner_a", "a2"), ("teacher_a1", "a1"), ("teacher_b1", "b1")],
)
def test_the_right_people_can_reverse(world, who, target):
    # Positive control: the cases above fail because of scope, not because reverse is broken.
    assert _reverse(world, who, target).status_code == 201


@pytest.mark.parametrize(
    ("attacker", "victim"), [("teacher_a1", "a2"), ("owner_b", "a1"), ("teacher_b1", "a1")]
)
def test_paid_entries_of_others_cannot_be_edited_or_deleted_either(world, attacker, victim):
    payment = getattr(world, victim).payment
    client = client_for(world.users[attacker])
    before = Payment.objects.values().get(pk=payment.pk)

    assert client.patch(f"/api/v1/payments/{payment.pk}/", {"amount": "1"}).status_code == 404
    assert client.delete(f"/api/v1/payments/{payment.pk}/").status_code == 404
    assert Payment.objects.values().get(pk=payment.pk) == before


def test_the_reason_of_a_reversal_is_not_visible_to_another_studio(world):
    assert _reverse(world, "teacher_a1", "a1").status_code == 201

    rows = client_for(world.users["teacher_b1"]).get("/api/v1/payments/").data["results"]

    assert all(row["status"] != "reversal" for row in rows)
    assert "x" not in {row.get("reason") for row in rows}
