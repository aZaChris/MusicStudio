"""Instructions never cross studios, and bank details never leak into logs, audit or Sentry
(FR-022, FR-023, FR-032, SC-006, SC-008)."""

import logging
from unittest import mock

import pytest
from rest_framework.test import APIClient

from apps.audit.models import AuditEntry
from apps.common import sentry
from apps.common.factories import (
    PackageFactory,
    ParentAccountFactory,
    StudentFactory,
    TeacherFactory,
    link_parent_to_student,
)
from apps.common.tests.helpers import client_for, make_studio_owner
from apps.payments.models import PaymentInstructions

pytestmark = pytest.mark.django_db

URL = "/api/v1/payment-instructions/"
OPEN = "/api/v1/payment-instructions/open/"
IBAN_A = "IT60X0542811101000000123456"
IBAN_B = "DE89370400440532013000"


def _studio(iban: str, holder: str):
    owner = make_studio_owner()
    res = client_for(owner.user).put(URL, {"iban": iban, "account_holder": holder}, format="json")
    assert res.status_code == 200
    return owner


def test_another_studios_owner_and_teacher_only_ever_see_their_own():
    a = _studio(IBAN_A, "Studio A")
    b = _studio(IBAN_B, "Studio B")
    b_teacher = TeacherFactory(studio=b.studio)

    assert client_for(b.user).get(URL).data["iban"] == IBAN_B
    assert client_for(b_teacher.user).get(URL).data["iban"] == IBAN_B
    # A studio with nothing saved sees an empty set, never someone else's.
    empty = make_studio_owner()
    assert client_for(empty.user).get(URL).data["iban"] == ""
    assert PaymentInstructions.objects.get(studio=a.studio).iban == IBAN_A


def test_saving_in_one_studio_never_touches_another():
    a = _studio(IBAN_A, "Studio A")
    b = _studio(IBAN_B, "Studio B")

    client_for(b.user).put(URL, {"note": "only B"}, format="json")
    client_for(b.user).put(URL, {}, format="json")  # B clears its own

    assert PaymentInstructions.objects.get(studio=a.studio).iban == IBAN_A
    assert not PaymentInstructions.objects.filter(studio=b.studio).exists()


def test_a_parent_of_another_studio_gets_nothing_of_studio_a():
    a = _studio(IBAN_A, "Studio A")
    b = _studio(IBAN_B, "Studio B")
    child_b = StudentFactory(teacher=b)
    PackageFactory(student=child_b)
    parent_b = ParentAccountFactory()
    link_parent_to_student(parent_b, child_b)
    child_a = StudentFactory(teacher=a)  # studio A also has an open package, for another family
    PackageFactory(student=child_a)

    rows = client_for(parent_b.user).get(OPEN).data

    assert [r["iban"] for r in rows] == [IBAN_B]
    assert IBAN_A not in str(rows)


def test_anonymous_requests_are_refused():
    _studio(IBAN_A, "Studio A")

    assert APIClient().get(URL).status_code == 401
    assert APIClient().get(OPEN).status_code == 401
    assert APIClient().put(URL, {"iban": IBAN_A}, format="json").status_code == 401


def test_an_iban_in_a_failing_request_never_reaches_logs_audit_or_sentry(caplog):
    owner = make_studio_owner()
    caplog.set_level(logging.DEBUG)

    # 1. A request refused by validation (bad checksum), and a request that crashes the server.
    bad = IBAN_A[:-1] + "7"
    client = client_for(owner.user)
    assert (
        client.put(URL, {"iban": bad, "account_holder": "Mario"}, format="json").status_code == 400
    )
    crashing = APIClient(raise_request_exception=False)  # a 500 response, not a raised error
    crashing.force_authenticate(user=owner.user)
    with mock.patch(
        "apps.payments.instruction_views.services.save_instructions",
        side_effect=RuntimeError("boom"),
    ):
        res = crashing.put(URL, {"iban": IBAN_A, "account_holder": "Mario"}, format="json")
    assert res.status_code == 500

    # 2. Logs, audit entries: no IBAN, no holder.
    logged = " ".join(record.getMessage() for record in caplog.records)
    assert IBAN_A not in logged and bad not in logged and "Mario" not in logged
    assert not AuditEntry.objects.filter(action="instructions.change").exists()

    # 3. The event Sentry would send for that request has no body.
    event = sentry.before_send(
        {
            "request": {
                "url": "https://api.example.com/api/v1/payment-instructions/",
                "data": {"iban": IBAN_A, "account_holder": "Mario"},
                "headers": {},
            }
        },
        {},
    )
    assert "data" not in event["request"]
