"""Invitations and parental consent (US3)."""

import re
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Invitation, User
from apps.audit.models import AuditEntry
from apps.common.factories import (
    ParentAccountFactory,
    StudentFactory,
    TeacherFactory,
    UserFactory,
    link_parent_to_student,
)
from apps.common.tests.helpers import client_for, make_studio_owner
from apps.privacy.models import ConsentRecord
from apps.studios.models import Teacher

pytestmark = pytest.mark.django_db

PASSWORD = "Pianoforte-Verde-31"


def _invite(client, capture, **body):  # type: ignore[no-untyped-def]
    with capture(execute=True):
        return client.post("/api/v1/invitations/", body, format="json")


def _token() -> str:
    url = re.search(r"http\S+/invitations/accept\S+", mail.outbox[-1].body).group(0)
    return parse_qs(urlparse(url).query)["token"][0]


def _accept(client=None, **body):  # type: ignore[no-untyped-def]
    payload = {"password": PASSWORD, "accept_terms": True, "first_name": "Ada", **body}
    return (client or APIClient()).post("/api/v1/invitations/accept/", payload)


def test_owner_invites_a_teacher_who_joins_the_studio(django_capture_on_commit_callbacks):
    owner = make_studio_owner()

    res = _invite(
        client_for(owner.user),
        django_capture_on_commit_callbacks,
        email="Nuovo@Example.com",
        role="teacher",
    )
    token = _token()
    lookup = APIClient().get("/api/v1/invitations/lookup/", {"token": token})
    accepted = _accept(token=token)

    assert res.status_code == 201 and res.data["status"] == "pending"
    assert lookup.data["role"] == "teacher" and lookup.data["existing_account"] is False
    assert accepted.status_code == 201 and "access" in accepted.data
    user = User.objects.get(email="nuovo@example.com")
    assert user.email_verified and user.role == "teacher"
    assert Teacher.objects.get(user=user).studio_id == owner.studio_id
    assert Invitation.objects.get().status == "accepted"
    assert AuditEntry.objects.filter(action="invitation.accept", actor=user).exists()
    assert _accept(token=token).status_code == 400  # single use


def test_teacher_invites_parent_and_consent_is_recorded(django_capture_on_commit_callbacks):
    teacher = TeacherFactory()
    child = StudentFactory(teacher=teacher)

    _invite(
        client_for(teacher.user),
        django_capture_on_commit_callbacks,
        email="mamma@example.com",
        role="parent",
        student_ids=[child.pk],
    )
    token = _token()
    without_consent = _accept(token=token)
    accepted = _accept(token=token, consent=True)

    assert without_consent.status_code == 400 and "consent" in without_consent.data
    assert accepted.status_code == 201
    parent = User.objects.get(email="mamma@example.com").parent_account
    assert list(parent.students.all()) == [child]
    consent = ConsentRecord.objects.get(parent=parent)
    assert list(consent.students.all()) == [child] and consent.notice_version


@pytest.mark.parametrize("role", ["teacher"])
def test_teacher_cannot_invite_teachers(role, django_capture_on_commit_callbacks):
    teacher = TeacherFactory()

    res = _invite(
        client_for(teacher.user),
        django_capture_on_commit_callbacks,
        email="x@example.com",
        role=role,
    )

    assert res.status_code == 403


def test_parent_cannot_invite(django_capture_on_commit_callbacks):
    parent = ParentAccountFactory()

    res = _invite(
        client_for(parent.user),
        django_capture_on_commit_callbacks,
        email="x@example.com",
        role="parent",
    )

    assert res.status_code == 403


def test_out_of_scope_student_looks_like_a_missing_one(django_capture_on_commit_callbacks):
    teacher = TeacherFactory()
    foreign = StudentFactory()

    res = _invite(
        client_for(teacher.user),
        django_capture_on_commit_callbacks,
        email="x@example.com",
        role="parent",
        student_ids=[foreign.pk],
    )
    missing = _invite(
        client_for(teacher.user),
        django_capture_on_commit_callbacks,
        email="x@example.com",
        role="parent",
        student_ids=[999_999],
    )

    assert res.status_code == missing.status_code == 400
    assert res.data == missing.data
    assert not Invitation.objects.exists()


def test_minor_cannot_be_invited_as_student_but_adult_can(django_capture_on_commit_callbacks):
    teacher = TeacherFactory()
    minor = StudentFactory(teacher=teacher)
    adult = StudentFactory(teacher=teacher, is_adult=True)
    client = client_for(teacher.user)

    refused = _invite(
        client,
        django_capture_on_commit_callbacks,
        email="kid@example.com",
        role="student",
        student_ids=[minor.pk],
    )
    ok = _invite(
        client,
        django_capture_on_commit_callbacks,
        email="adult@example.com",
        role="student",
        student_ids=[adult.pk],
    )
    accepted = _accept(token=_token())

    assert refused.status_code == 400 and "Minors" in str(refused.data)
    assert ok.status_code == 201 and accepted.status_code == 201
    adult.refresh_from_db()
    assert adult.user.email == "adult@example.com" and adult.user.role == "student"


def test_expired_and_revoked_invitations_are_refused(django_capture_on_commit_callbacks):
    owner = make_studio_owner()
    client = client_for(owner.user)
    _invite(client, django_capture_on_commit_callbacks, email="a@example.com", role="teacher")
    expired_token = _token()
    Invitation.objects.update(expires_at=timezone.now() - timedelta(minutes=1))
    res = _invite(client, django_capture_on_commit_callbacks, email="b@example.com", role="teacher")
    revoked_token = _token()

    revoke = client.post(f"/api/v1/invitations/{res.data['id']}/revoke/")

    assert revoke.status_code == 200 and revoke.data["status"] == "revoked"
    assert (
        APIClient().get("/api/v1/invitations/lookup/", {"token": expired_token}).status_code == 404
    )
    assert _accept(token=expired_token).status_code == 400
    assert _accept(token=revoked_token).status_code == 400
    listed = {
        row["email"]: row["status"] for row in client.get("/api/v1/invitations/").data["results"]
    }
    assert listed == {"a@example.com": "expired", "b@example.com": "revoked"}


def test_new_invitation_replaces_the_pending_one(django_capture_on_commit_callbacks):
    owner = make_studio_owner()
    client = client_for(owner.user)
    _invite(client, django_capture_on_commit_callbacks, email="a@example.com", role="teacher")
    first = _token()
    _invite(client, django_capture_on_commit_callbacks, email="a@example.com", role="teacher")

    assert _accept(token=first).status_code == 400
    assert _accept(token=_token()).status_code == 201


def test_invitation_dies_when_the_inviter_loses_the_student(django_capture_on_commit_callbacks):
    teacher = TeacherFactory()
    child = StudentFactory(teacher=teacher)
    _invite(
        client_for(teacher.user),
        django_capture_on_commit_callbacks,
        email="p@example.com",
        role="parent",
        student_ids=[child.pk],
    )
    child.teacher = TeacherFactory(studio=teacher.studio)
    child.save()

    assert _accept(token=_token(), consent=True).status_code == 400


def test_existing_parent_gets_new_links_not_a_second_account(django_capture_on_commit_callbacks):
    teacher = TeacherFactory()
    first, second = StudentFactory(teacher=teacher), StudentFactory(teacher=teacher)
    parent = ParentAccountFactory()
    link_parent_to_student(parent, first)
    _invite(
        client_for(teacher.user),
        django_capture_on_commit_callbacks,
        email=parent.user.email,
        role="parent",
        student_ids=[second.pk],
    )
    token = _token()

    anonymous = _accept(token=token, consent=True)
    signed_in = _accept(client_for(parent.user), token=token, consent=True, password="")

    assert anonymous.status_code == 400
    assert signed_in.status_code == 201, signed_in.data
    assert User.objects.filter(email=parent.user.email).count() == 1
    assert set(parent.students.all()) == {first, second}


def test_existing_non_parent_account_cannot_accept(django_capture_on_commit_callbacks):
    owner = make_studio_owner()
    someone = UserFactory()
    _invite(
        client_for(owner.user),
        django_capture_on_commit_callbacks,
        email=someone.email,
        role="teacher",
    )

    assert _accept(client_for(someone), token=_token()).status_code == 400
    assert not Teacher.objects.filter(user=someone, studio=owner.studio).exists()


def test_teachers_see_only_their_own_invitations(django_capture_on_commit_callbacks):
    owner = make_studio_owner()
    t1, t2 = TeacherFactory(studio=owner.studio), TeacherFactory(studio=owner.studio)
    s1 = StudentFactory(teacher=t1)
    _invite(
        client_for(t1.user),
        django_capture_on_commit_callbacks,
        email="p1@example.com",
        role="parent",
        student_ids=[s1.pk],
    )
    inv = Invitation.objects.get()

    assert client_for(t2.user).get("/api/v1/invitations/").data["count"] == 0
    assert client_for(owner.user).get("/api/v1/invitations/").data["count"] == 1
    assert client_for(t2.user).post(f"/api/v1/invitations/{inv.pk}/revoke/").status_code == 404
    assert (
        make_studio_owner().user
        and client_for(make_studio_owner().user)
        .post(f"/api/v1/invitations/{inv.pk}/revoke/")
        .status_code
        == 404
    )


def test_invitation_list_query_budget(
    django_assert_max_num_queries, django_capture_on_commit_callbacks
):
    owner = make_studio_owner()
    client = client_for(owner.user)
    child = StudentFactory(teacher=owner)
    for i in range(5):
        _invite(
            client,
            django_capture_on_commit_callbacks,
            email=f"p{i}@example.com",
            role="parent",
            student_ids=[child.pk],
        )

    with django_assert_max_num_queries(6):
        res = client_for(owner.user).get("/api/v1/invitations/")

    assert res.data["count"] == 5
