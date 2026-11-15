"""A busy month still answers: the summary and the list hold their query budget at volume.

SC-003 (2,000 entries in under 3 s) and SC-004 (a year of 5,000 in under 10 s) are timing
goals measured once by hand with `seed_loadtest` and written down in the phase notes; CI does
not assert wall-clock time, which would be flaky on shared runners. What CI can assert is that
a large period keeps the query count constant and returns the right totals.
"""

import datetime

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.common.factories import StudentFactory
from apps.common.tests.helpers import client_for
from apps.payments.models import Payment

pytestmark = pytest.mark.django_db

ENTRIES = 2000


def test_a_month_of_two_thousand_entries_is_one_aggregate_and_right():
    student = StudentFactory()
    start = datetime.date(2026, 11, 1)
    methods = [m for m, _ in Payment.Method.choices]
    Payment.objects.bulk_create(
        [
            Payment(
                student=student,
                amount="10.00",
                date=start + datetime.timedelta(days=i % 30),
                method=methods[i % 4],
                status=Payment.Status.PAID,
            )
            for i in range(ENTRIES)
        ]
    )
    client = client_for(student.teacher.user)

    with CaptureQueriesContext(connection) as ctx:
        res = client.get(
            "/api/v1/payments/register/summary/",
            {"date_from": "2026-11-01", "date_to": "2026-11-30"},
        )

    assert res.status_code == 200 and len(ctx) == 2  # teacher + one aggregate
    assert res.data["counts"]["paid"] == ENTRIES
    assert res.data["totals"]["received"] == f"{ENTRIES * 10}.00"
    assert {line["received"] for line in res.data["by_method"]} == {"5000.00"}

    export = client.get(
        "/api/v1/payments/register/export/csv/",
        {"date_from": "2026-11-01", "date_to": "2026-11-30"},
    )
    assert export.content.count(b"\r\n") == ENTRIES + 1  # header + one row each
