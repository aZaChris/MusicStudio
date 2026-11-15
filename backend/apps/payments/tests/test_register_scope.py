"""Who sees which register: own students, whole studio, nothing for families (FR-013, FR-032)."""

import csv
import datetime
import io

import pytest
from rest_framework.test import APIClient

from apps.common.tests.helpers import client_for
from apps.common.tests.idor_world import World, build_world
from apps.payments.models import Payment

pytestmark = pytest.mark.django_db

TODAY = datetime.date.today().isoformat()
PERIOD = {"date_from": TODAY, "date_to": TODAY}
ROUTES = [
    "/api/v1/payments/register/summary/",
    "/api/v1/payments/register/export/csv/",
    "/api/v1/payments/register/export/pdf/",
]


@pytest.fixture
def world() -> World:
    world = build_world()
    Payment.objects.update(status=Payment.Status.PAID, date=TODAY)
    return world


def _summary(world: World, who: str):
    return client_for(world.users[who]).get(ROUTES[0], PERIOD).data


@pytest.mark.parametrize(
    ("who", "paid", "received"),
    [
        ("teacher_a1", 1, "50.00"),  # only their own student
        ("teacher_a2", 1, "50.00"),
        ("owner_a", 2, "100.00"),  # the whole studio A (a1 + a2), never B
        ("teacher_b1", 1, "50.00"),
        ("owner_b", 1, "50.00"),
    ],
)
def test_each_role_sees_only_its_scope_in_the_totals(world, who, paid, received):
    data = _summary(world, who)

    assert data["counts"]["paid"] == paid
    assert data["totals"]["received"] == received


def test_a_studio_with_no_entries_sees_zero_not_other_studios_money(world):
    Payment.objects.filter(student__studio=world.b1.student.studio).delete()

    data = _summary(world, "owner_b")

    assert data["totals"]["received"] == "0.00" and data["counts"]["paid"] == 0


@pytest.mark.parametrize("who", ["parent_a", "parent_b", "student_a2"])
@pytest.mark.parametrize("route", ROUTES)
def test_families_get_403_on_the_register_and_both_exports(world, who, route):
    res = client_for(world.users[who]).get(route, PERIOD)

    assert res.status_code == 403


@pytest.mark.parametrize("route", ROUTES)
def test_anonymous_gets_401(world, route):
    assert APIClient().get(route, PERIOD).status_code == 401


def test_the_csv_holds_exactly_the_callers_scope(world):
    res = client_for(world.users["teacher_a1"]).get(ROUTES[1], PERIOD)
    rows = list(csv.DictReader(io.StringIO(res.content.decode("utf-8-sig")), delimiter=";"))

    assert [row["student"] for row in rows] == [world.a1.student.full_name]

    owner = client_for(world.users["owner_a"]).get(ROUTES[1], PERIOD)
    names = {
        row["student"]
        for row in csv.DictReader(io.StringIO(owner.content.decode("utf-8-sig")), delimiter=";")
    }
    assert names == {world.a1.student.full_name, world.a2.student.full_name}
    assert world.b1.student.full_name not in names
