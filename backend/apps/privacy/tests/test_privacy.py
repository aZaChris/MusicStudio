import json

import pytest
from django.core import mail
from django.db import connection
from django.db.models import Sum
from rest_framework.test import APIClient

from apps.accounts.models import Invitation, User
from apps.audit.models import AuditEntry
from apps.common.factories import ParentAccountFactory, link_parent_to_student
from apps.common.tests.helpers import client_for
from apps.common.tests.idor_world import build_world
from apps.lessons.models import Lesson
from apps.payments.models import CheckoutSession, Payment
from apps.privacy import services
from apps.privacy.models import ConsentRecord
from apps.students.models import Student

pytestmark = pytest.mark.django_db
PW = "password123"


@pytest.fixture
def world():
    w = build_world()
    parent = w.users["parent_a"]
    parent.first_name, parent.last_name = "Marta", "Zanotti"
    parent.save()
    Student.objects.filter(pk=w.a1.student.pk).update(first_name="Gioele", last_name="Brambilla")
    return w


def text_hits(needle: str) -> list[str]:
    """Every table.column whose text contains `needle` (case-insensitive)."""
    hits = []
    with connection.cursor() as cur:
        cur.execute(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE table_schema='public' AND data_type IN "
            "('character varying','text','jsonb','json')"
        )
        for table, column in cur.fetchall():
            cur.execute(
                f'SELECT 1 FROM "{table}" WHERE "{column}"::text ILIKE %s LIMIT 1',  # noqa: S608
                [f"%{needle}%"],
            )
            if cur.fetchone():
                hits.append(f"{table}.{column}")
    return hits


# --- export ---------------------------------------------------------------------------------


def test_parent_export_has_all_own_data_and_nothing_of_another_family(
    world, django_assert_max_num_queries
):
    client = client_for(world.users["parent_a"])
    with django_assert_max_num_queries(10):
        res = client.get("/api/v1/privacy/export/")
    assert res.status_code == 200
    assert "attachment" in res["Content-Disposition"]
    data = json.loads(res.content)
    own = world.a1
    (child,) = data["children"]
    assert child["first_name"] == "Gioele"
    assert [x["id"] for x in child["lessons"]] == [own.lesson.pk]
    assert child["lessons"][0]["notes"] == "private note"  # decrypted for the family
    assert [x["id"] for x in child["packages"]] == [own.package.pk]
    assert [x["id"] for x in child["payments"]] == [own.payment.pk]
    assert data["account"]["email"] == world.users["parent_a"].email
    raw = res.content.decode()
    for other in (world.b1, world.a2):
        assert other.student.first_name not in raw
    assert world.users["parent_b"].email not in raw
    assert AuditEntry.objects.filter(action="privacy.export").count() == 1


def test_adult_student_export_is_only_their_own_record(world):
    data = client_for(world.users["student_a2"]).get("/api/v1/privacy/export/").json()
    assert [c["id"] for c in data["children"]] == [world.a2.student.pk]


def test_teachers_and_owners_have_no_family_export(world):
    for name in ("teacher_a1", "owner_a"):
        assert client_for(world.users[name]).get("/api/v1/privacy/export/").status_code == 403
    assert APIClient().get("/api/v1/privacy/export/").status_code == 401


# --- erasure --------------------------------------------------------------------------------


def test_erasure_leaves_no_trace_of_the_person_and_keeps_the_books(world):
    parent = world.users["parent_a"]
    email = parent.email
    totals = Payment.objects.aggregate(t=Sum("amount"))["t"]
    count = Payment.objects.count()
    lessons = Lesson.objects.count()
    assert text_hits("Zanotti") and text_hits("Brambilla")  # sanity: the search finds them

    res = client_for(parent).post("/api/v1/privacy/erase/", {"password": PW})

    assert res.status_code == 202
    for needle in (email, "Zanotti", "Marta", "Gioele", "Brambilla", "private note"):
        assert text_hits(needle) == [], needle
    assert Payment.objects.aggregate(t=Sum("amount"))["t"] == totals
    assert (Payment.objects.count(), Lesson.objects.count()) == (count, lessons)
    child = Student.objects.get(pk=world.a1.student.pk)
    assert child.last_name == f"cancellato #{child.pk}" and child.anonymised_at
    assert not child.is_active
    assert AuditEntry.objects.filter(action="privacy.erase").exists()


def test_cannot_sign_in_after_erasure(world):
    parent = world.users["parent_a"]
    email = parent.email
    client_for(parent).post("/api/v1/privacy/erase/", {"password": PW})
    res = APIClient().post("/api/v1/auth/token/", {"email": email, "password": PW})
    assert res.status_code == 401
    assert User.objects.get(pk=parent.pk).has_usable_password() is False


def test_wrong_password_erases_nothing(world):
    res = client_for(world.users["parent_a"]).post("/api/v1/privacy/erase/", {"password": "no"})
    assert res.status_code == 400
    assert Student.objects.get(pk=world.a1.student.pk).first_name == "Gioele"


def test_child_with_two_parents_stays_and_the_teacher_is_told(
    world, django_capture_on_commit_callbacks
):
    other = ParentAccountFactory()
    link_parent_to_student(other, world.a1.student)
    with django_capture_on_commit_callbacks(execute=True):
        res = client_for(world.users["parent_a"]).post("/api/v1/privacy/erase/", {"password": PW})
    assert res.status_code == 202
    child = Student.objects.get(pk=world.a1.student.pk)
    assert child.first_name == "Gioele" and child.anonymised_at is None
    assert list(child.parent_accounts.all()) == [other]
    (message,) = mail.outbox
    assert message.to == [world.users["teacher_a1"].email]
    assert "Gioele" in message.body and "Zanotti" not in message.body


def test_open_checkout_blocks_erasure(world):
    CheckoutSession.objects.create(
        package=world.a1.package, amount="50.00", currency="eur", status="open"
    )
    res = client_for(world.users["parent_a"]).post("/api/v1/privacy/erase/", {"password": PW})
    assert res.status_code == 409
    assert res.json()["code"] == "checkout_open" or "checkout" in json.dumps(res.json())
    assert Student.objects.get(pk=world.a1.student.pk).first_name == "Gioele"


def test_owner_with_students_cannot_erase_but_an_empty_studio_can(world):
    owner = world.users["owner_a"]
    res = client_for(owner).post("/api/v1/privacy/erase/", {"password": PW})
    assert res.status_code == 409
    Student.objects.filter(studio=owner.teacher.studio).delete()
    assert client_for(owner).post("/api/v1/privacy/erase/", {"password": PW}).status_code == 202


def test_erasure_removes_invitations_sent_to_the_address(world):
    parent = world.users["parent_a"]
    Invitation.objects.create(
        studio=world.a1.student.studio,
        invited_by=world.users["owner_a"],
        email=parent.email,
        role="parent",
        token_hash="x" * 64,
        expires_at=parent.date_joined,
    )
    client_for(parent).post("/api/v1/privacy/erase/", {"password": PW})
    assert not Invitation.objects.exists()


def test_adult_student_erasure_anonymises_their_record(world):
    res = client_for(world.users["student_a2"]).post("/api/v1/privacy/erase/", {"password": PW})
    assert res.status_code == 202
    student = Student.objects.get(pk=world.a2.student.pk)
    assert student.anonymised_at and student.user is None
    assert Payment.objects.filter(student=student).exists()


# --- consents -------------------------------------------------------------------------------


def test_consents_listed_and_withdrawal_erases_the_child(world):
    parent = world.users["parent_a"]
    consent = services.give_consent(parent.parent_account, [world.a1.student])
    client = client_for(parent)

    listed = client.get("/api/v1/privacy/consents/").json()
    assert [c["id"] for c in listed] == [consent.pk]
    assert listed[0]["children"][0]["name"] == "Gioele Brambilla"

    assert (
        client.post(
            f"/api/v1/privacy/consents/{consent.pk}/withdraw/", {"password": "x"}
        ).status_code
        == 400
    )
    res = client.post(f"/api/v1/privacy/consents/{consent.pk}/withdraw/", {"password": PW})
    assert res.status_code == 202
    assert ConsentRecord.objects.get(pk=consent.pk).withdrawn_at
    assert Student.objects.get(pk=world.a1.student.pk).anonymised_at
    assert AuditEntry.objects.filter(action="consent.withdraw").exists()
    # a second withdrawal has nothing left to act on
    assert (
        client.post(
            f"/api/v1/privacy/consents/{consent.pk}/withdraw/", {"password": PW}
        ).status_code
        == 404
    )


def test_another_parent_cannot_see_or_withdraw_my_consent(world):
    consent = services.give_consent(world.users["parent_a"].parent_account, [world.a1.student])
    other = client_for(world.users["parent_b"])
    assert other.get("/api/v1/privacy/consents/").json() == []
    res = other.post(f"/api/v1/privacy/consents/{consent.pk}/withdraw/", {"password": PW})
    assert res.status_code == 404
    assert Student.objects.get(pk=world.a1.student.pk).anonymised_at is None
