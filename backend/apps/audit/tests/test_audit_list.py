import pytest

from apps.audit import services as audit
from apps.audit.models import AuditEntry
from apps.common.tests.helpers import client_for
from apps.common.tests.idor_world import build_world

pytestmark = pytest.mark.django_db
URL = "/api/v1/audit/"


@pytest.fixture
def world():
    w = build_world()
    audit.record("payment.record", actor=w.users["teacher_a1"], studio_id=w.a1.student.studio_id)
    audit.record("payment.record", actor=w.users["teacher_b1"], studio_id=w.b1.student.studio_id)
    audit.record("login.success", actor=w.users["teacher_a1"])  # no studio: shown via the team
    audit.record("login.success", actor=w.users["teacher_b1"])
    audit.record("login.success", actor=w.users["parent_a"])  # parents' sign-ins stay private
    return w


def test_owner_sees_own_studio_and_own_team_sign_ins_only(world):
    res = client_for(world.users["owner_a"]).get(URL)

    assert res.status_code == 200
    rows = res.json()["results"]
    assert sorted(r["action"] for r in rows) == ["login.success", "payment.record"]
    assert {r["actor_email"] for r in rows} == {world.users["teacher_a1"].email}


@pytest.mark.parametrize("who", ["teacher_a1", "parent_a", "student_a2"])
def test_other_roles_are_refused(world, who):
    assert client_for(world.users[who]).get(URL).status_code == 403


def test_filters_by_action_and_date(world):
    client = client_for(world.users["owner_a"])
    only = client.get(URL, {"action": "payment.record"}).json()["results"]
    assert [r["action"] for r in only] == ["payment.record"]
    assert client.get(URL, {"since": "2999-01-01T00:00:00Z"}).json()["results"] == []
    assert len(client.get(URL, {"until": "2999-01-01T00:00:00Z"}).json()["results"]) == 2
    assert client.get(URL, {"action": "nonsense"}).status_code == 400


def test_newest_first_and_paginated(world):
    for _ in range(30):
        audit.record("payment.record", studio_id=world.a1.student.studio_id)
    page = client_for(world.users["owner_a"]).get(URL).json()
    assert page["count"] == 32 and len(page["results"]) == 25
    stamps = [r["created_at"] for r in page["results"]]
    assert stamps == sorted(stamps, reverse=True)


def test_query_budget(world, django_assert_max_num_queries):
    for _ in range(30):
        audit.record("payment.record", studio_id=world.a1.student.studio_id)
    client = client_for(world.users["owner_a"])
    with django_assert_max_num_queries(6):
        client.get(URL)
    assert AuditEntry.objects.count() > 30
