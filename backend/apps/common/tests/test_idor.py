"""Object-level authorization (OWASP API1, BOLA/IDOR) on every tenant endpoint.

For every (attacker, victim) pair below the attacker must not read, list, change, delete or
reference the victim's objects. Reads answer 404 (constitution I: out of scope looks like
"does not exist"); writes answer 403 or 404 and leave the database unchanged.
`test_idor_coverage.py` fails the build when an endpoint is missing from ROUTES.
"""

from datetime import date, timedelta

import pytest
from django.forms.models import model_to_dict

from apps.common.tests.helpers import client_for
from apps.common.tests.idor_world import Holdings, World, build_world
from apps.studios.models import Teacher

pytestmark = [pytest.mark.django_db, pytest.mark.idor]

# (attacker, victim holdings): same studio other teacher, other studio, other family, self vs other.
PAIRS = [
    ("teacher_a1", "a2"),
    ("teacher_a1", "b1"),
    ("teacher_a2", "a1"),
    ("owner_a", "b1"),
    ("teacher_b1", "a1"),
    ("owner_b", "a2"),
    ("parent_a", "a2"),
    ("parent_a", "b1"),
    ("parent_b", "a1"),
    ("student_a2", "a1"),
    ("student_a2", "b1"),
]

# Detail routes, as `(method, path template, kind, body)`. Covered routes are listed in
# ROUTES for the coverage guard.
READS = [
    ("get", "/api/v1/students/{student}/"),
    ("get", "/api/v1/students/{student}/lessons/"),
    ("get", "/api/v1/lessons/{lesson}/"),
    ("get", "/api/v1/packages/{package}/"),
    ("get", "/api/v1/payments/{payment}/"),
]
WRITES = [
    ("patch", "/api/v1/students/{student}/", "student", {"first_name": "Pwned"}),
    (
        "put",
        "/api/v1/students/{student}/",
        "student",
        {"first_name": "P", "last_name": "W", "instrument": "x"},
    ),
    ("delete", "/api/v1/students/{student}/", "student", None),
    ("post", "/api/v1/students/{student}/reassign/", "student", {"teacher": "{own_teacher}"}),
    ("patch", "/api/v1/lessons/{lesson}/", "lesson", {"notes": "pwned"}),
    (
        "put",
        "/api/v1/lessons/{lesson}/",
        "lesson",
        {"student": "{student}", "start_time": "2030-01-01T10:00:00Z"},
    ),
    ("delete", "/api/v1/lessons/{lesson}/", "lesson", None),
    ("post", "/api/v1/lessons/{lesson}/cancel/", "lesson", {"status": "cancelled"}),
    ("post", "/api/v1/lessons/{lesson}/complete/", "lesson", {"note": "pwned"}),
    ("patch", "/api/v1/packages/{package}/", "package", {"price": "1.00"}),
    (
        "put",
        "/api/v1/packages/{package}/",
        "package",
        {
            "student": "{student}",
            "total_lessons": 1,
            "price": "1.00",
            "purchase_date": "2030-01-01",
        },
    ),
    ("delete", "/api/v1/packages/{package}/", "package", None),
    ("post", "/api/v1/packages/{package}/checkout/", "package", None),
    ("patch", "/api/v1/payments/{payment}/", "payment", {"amount": "0.01"}),
    (
        "put",
        "/api/v1/payments/{payment}/",
        "payment",
        {"student": "{student}", "amount": "0.01", "date": "2030-01-01", "method": "cash"},
    ),
    ("delete", "/api/v1/payments/{payment}/", "payment", None),
]
LISTS = [
    "/api/v1/students/",
    "/api/v1/lessons/",
    "/api/v1/lessons/upcoming/",
    "/api/v1/packages/",
    "/api/v1/payments/",
]

# Every tenant route under /api/v1/ is exercised above or in the tests below.
ROUTES = {
    "students/",
    "students/<pk>/",
    "students/<pk>/lessons/",
    "students/<pk>/reassign/",
    "lessons/",
    "lessons/upcoming/",
    "lessons/<pk>/",
    "lessons/<pk>/cancel/",
    "lessons/<pk>/complete/",
    "packages/",
    "packages/<pk>/",
    "packages/<pk>/checkout/",
    "payments/",
    "payments/<pk>/",
    "dashboard/",
    "studio/",
    "studio/teachers/",
}


@pytest.fixture
def world() -> World:
    return build_world()


def _victim(world: World, name: str) -> Holdings:
    holdings = getattr(world, name)
    assert holdings is not None
    return holdings


def _fill(value, ids: dict[str, int]):  # type: ignore[no-untyped-def]
    if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
        return ids[value[1:-1]]
    return value


def _snapshot(holdings: Holdings) -> dict[str, dict]:
    snap = {}
    for kind in ("student", "lesson", "package", "payment"):
        obj = getattr(holdings, kind)
        fresh = type(obj).objects.filter(pk=obj.pk).first()
        snap[kind] = model_to_dict(fresh) if fresh else {}
    return snap


@pytest.mark.parametrize(("attacker", "victim"), PAIRS)
@pytest.mark.parametrize(("method", "path"), READS)
def test_cannot_read_other_tenants_objects(world, attacker, victim, method, path):
    target = _victim(world, victim)

    res = getattr(client_for(world.users[attacker]), method)(path.format(**target.ids()))

    assert res.status_code == 404


@pytest.mark.parametrize(("attacker", "victim"), PAIRS)
@pytest.mark.parametrize(("method", "path", "kind", "body"), WRITES)
def test_cannot_change_other_tenants_objects(world, attacker, victim, method, path, kind, body):
    target = _victim(world, victim)
    user = world.users[attacker]
    own_teacher = Teacher.objects.filter(user=user).values_list("pk", flat=True).first()
    ids = {**target.ids(), "own_teacher": own_teacher or 0}
    before = _snapshot(target)

    payload = {k: _fill(v, ids) for k, v in (body or {}).items()}
    res = getattr(client_for(user), method)(path.format(**ids), payload)

    assert res.status_code in (403, 404), res.data
    assert _snapshot(target) == before


@pytest.mark.parametrize(("attacker", "victim"), PAIRS)
@pytest.mark.parametrize("path", LISTS)
def test_lists_never_show_other_tenants_objects(world, attacker, victim, path):
    target = _victim(world, victim)
    client = client_for(world.users[attacker])

    rows = client.get(path).data
    rows = rows["results"] if isinstance(rows, dict) else rows
    filtered = client.get(path, {"student": target.student.pk}).data
    filtered = filtered["results"] if isinstance(filtered, dict) else filtered

    key = "id" if path == "/api/v1/students/" else "student"
    assert target.student.pk not in {row[key] for row in [*rows, *filtered]}


# Writes that reference someone else's object from a request on your own side.
@pytest.mark.parametrize(
    ("attacker", "victim"), [p for p in PAIRS if p[0].startswith(("teacher", "owner"))]
)
@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("/api/v1/lessons/", {"student": "{student}", "start_time": "2031-03-03T10:00:00Z"}),
        ("/api/v1/packages/", {"student": "{student}", "total_lessons": 4, "price": "40.00"}),
        ("/api/v1/payments/", {"student": "{student}", "amount": "40.00", "method": "cash"}),
    ],
)
def test_cannot_create_objects_for_other_tenants_students(world, attacker, victim, path, body):
    target = _victim(world, victim)
    model = {"lessons": "lesson", "packages": "package", "payments": "payment"}[path.split("/")[3]]
    kind = type(getattr(target, model))
    count = kind.objects.filter(student=target.student).count()
    payload = {k: _fill(v, target.ids()) for k, v in body.items()}
    payload.setdefault("date", date.today().isoformat())
    payload.setdefault("purchase_date", date.today().isoformat())

    res = client_for(world.users[attacker]).post(path, payload)

    assert res.status_code == 400
    assert "student" in res.data
    assert kind.objects.filter(student=target.student).count() == count


def test_cannot_attach_own_lesson_to_another_studios_package(world):
    own = _victim(world, "a1")
    foreign = _victim(world, "b1")

    res = client_for(world.users["teacher_a1"]).post(
        "/api/v1/lessons/",
        {
            "student": own.student.pk,
            "package": foreign.package.pk,
            "start_time": (own.lesson.start_time + timedelta(days=3)).isoformat(),
        },
    )

    assert res.status_code == 400 and "package" in res.data


def test_owner_cannot_reassign_to_another_studios_teacher(world):
    own = _victim(world, "a1")
    teacher_b1 = Teacher.objects.get(user=world.users["teacher_b1"])

    res = client_for(world.users["owner_a"]).post(
        f"/api/v1/students/{own.student.pk}/reassign/", {"teacher": teacher_b1.pk}
    )

    assert res.status_code == 400
    own.student.refresh_from_db()
    assert own.student.teacher.user == world.users["teacher_a1"]


@pytest.mark.parametrize(
    ("owner", "foreign"), [("owner_a", "teacher_b1"), ("owner_b", "teacher_a1")]
)
def test_studio_views_show_only_own_studio(world, owner, foreign):
    client = client_for(world.users[owner])

    teachers = client.get("/api/v1/studio/teachers/").data
    teachers = teachers["results"] if isinstance(teachers, dict) else teachers
    studio = client.get("/api/v1/studio/").data

    foreign_teacher = Teacher.objects.get(user=world.users[foreign])
    assert foreign_teacher.pk not in {t["id"] for t in teachers}
    assert studio["id"] != foreign_teacher.studio_id


@pytest.mark.parametrize("user", ["teacher_a1", "parent_a", "student_a2"])
def test_studio_views_are_owner_only(world, user):
    client = client_for(world.users[user])

    assert client.get("/api/v1/studio/").status_code == 403
    assert client.get("/api/v1/studio/teachers/").status_code == 403


@pytest.mark.parametrize(("attacker", "victim"), PAIRS)
def test_dashboard_mentions_no_other_tenants_student(world, attacker, victim):
    target = _victim(world, victim)
    target.package.lessons_remaining = 1  # would show up as "low package" if visible
    target.package.save(update_fields=["lessons_remaining"])

    res = client_for(world.users[attacker]).get("/api/v1/dashboard/")

    assert res.status_code in (200, 403)
    assert target.student.full_name not in str(res.data)


# Control: the same requests succeed for the rightful users, so a 404 above means "denied",
# not "the world was built wrong".
@pytest.mark.parametrize(
    ("user", "holdings"),
    [
        ("teacher_a1", "a1"),
        ("owner_a", "a1"),
        ("owner_a", "a2"),
        ("parent_a", "a1"),
        ("student_a2", "a2"),
        ("teacher_b1", "b1"),
    ],
)
@pytest.mark.parametrize(("method", "path"), READS)
def test_rightful_users_can_read(world, user, holdings, method, path):
    target = _victim(world, holdings)

    res = getattr(client_for(world.users[user]), method)(path.format(**target.ids()))

    assert res.status_code == 200


def test_rightful_teacher_can_write():
    world = build_world()
    own = _victim(world, "a1")

    res = client_for(world.users["teacher_a1"]).patch(
        f"/api/v1/lessons/{own.lesson.pk}/", {"notes": "ok"}
    )

    assert res.status_code == 200
