"""Query budgets for the main endpoints (Constitution III, audit G2).

Each endpoint is measured with 1 and with 25 rows: the count must be identical (no N+1)
and equal to the pinned budget. If you add a field that needs data from another table,
this test tells you to add a select_related/prefetch/annotation to the selector.
"""

from collections.abc import Callable

import pytest
from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.common.factories import (
    LessonFactory,
    PackageFactory,
    ParentAccountFactory,
    StudentFactory,
    TeacherFactory,
    link_parent_to_student,
)
from apps.common.tests.helpers import client_for, make_studio_owner
from apps.payments.models import Payment
from apps.studios.models import Teacher

pytestmark = pytest.mark.django_db


def _seed_student(teacher: Teacher) -> None:
    student = StudentFactory(teacher=teacher)
    package = PackageFactory(student=student, total_lessons=8, lessons_remaining=1)
    LessonFactory(student=student, package=package)
    Payment.objects.create(student=student, amount="10", date="2026-01-01", method="cash")


def _count(user, url: str) -> int:
    client = client_for(user)  # fresh user per request, as with real token auth
    cache.clear()  # measure the computation, not the dashboard cache (ADR-017)
    with CaptureQueriesContext(connection) as ctx:
        res = client.get(url)
    assert res.status_code == 200, res.data
    return len(ctx)


# Budgets for a teacher. With JWT auth add 1 query (loading the user from the token).
# The first query is always request.user.teacher, needed for tenant scoping.
TEACHER_BUDGETS = {
    "/api/v1/students/": 4,  # teacher, count, students+payment subquery, active packages
    "/api/v1/lessons/": 3,  # teacher, count, lessons+student
    "/api/v1/packages/": 3,  # teacher, count, packages
    "/api/v1/payments/": 3,  # teacher, count, payments+student
    "/api/v1/dashboard/": 6,  # teacher, week, upcoming, pending, active, low-package
}


@pytest.mark.parametrize(("url", "budget"), TEACHER_BUDGETS.items())
def test_num_queries_constant_for_teacher(url: str, budget: int):
    teacher = TeacherFactory()

    _seed_student(teacher)
    with_one = _count(teacher.user, url)
    for _ in range(24):
        _seed_student(teacher)
    with_many = _count(teacher.user, url)

    assert with_one == with_many == budget


def test_num_queries_constant_for_studio_teachers():
    owner = make_studio_owner()
    measure: Callable[[], int] = lambda: _count(owner.user, "/api/v1/studio/teachers/")  # noqa: E731

    with_one = measure()
    for _ in range(9):
        TeacherFactory(studio=owner.studio)

    assert with_one == measure() == 3  # teacher, count, teachers+user


def test_num_queries_constant_for_parent_roster():
    parent = ParentAccountFactory()
    teacher = TeacherFactory()

    def add_child() -> None:
        _seed_student(teacher)
        link_parent_to_student(parent, teacher.students.order_by("-id").first())

    add_child()
    with_one = _count(parent.user, "/api/v1/students/")
    for _ in range(4):
        add_child()

    assert with_one == _count(parent.user, "/api/v1/students/") == 4


def test_payments_list_budget_holds_with_reversed_entries():
    # Phase 8: `reversed`, `reversal_id` and `reversal_of` come from the same query
    # (select_related("reversal")), so reversals must not add queries per row.
    from apps.common.factories import PaymentFactory, make_reversal

    teacher = TeacherFactory()

    def seed_with_reversal() -> None:
        student = StudentFactory(teacher=teacher)
        make_reversal(PaymentFactory(student=student), recorded_by=teacher.user)
        PaymentFactory(student=student)

    seed_with_reversal()
    with_one = _count(teacher.user, "/api/v1/payments/")
    for _ in range(14):
        seed_with_reversal()
    with_many = _count(teacher.user, "/api/v1/payments/")

    assert with_one == with_many == 3  # same as without reversals


def test_register_endpoints_hold_a_constant_query_count():
    # Phase 8: the summary is one aggregate and the CSV rows come from one query, however many
    # entries the period holds (SC-003, no N+1 on the student or the reversal).
    from apps.common.factories import PaymentFactory, make_reversal

    teacher = TeacherFactory()
    period = "?date_from=2020-01-01&date_to=2020-12-31"

    def seed() -> None:
        student = StudentFactory(teacher=teacher)
        make_reversal(PaymentFactory(student=student, date="2020-05-05"), date="2020-06-06")

    seed()
    summary_one = _count(teacher.user, "/api/v1/payments/register/summary/" + period)
    csv_one = _count(teacher.user, "/api/v1/payments/register/export/csv/" + period)
    list_one = _count(teacher.user, "/api/v1/payments/" + period)
    for _ in range(19):
        seed()

    assert summary_one == _count(teacher.user, "/api/v1/payments/register/summary/" + period) == 2
    # teacher, rows, and the audit entry written by the export
    assert csv_one == _count(teacher.user, "/api/v1/payments/register/export/csv/" + period) == 3
    assert list_one == _count(teacher.user, "/api/v1/payments/" + period) == 3


def test_payment_instructions_endpoints_hold_a_constant_query_count():
    # Phase 8: the parent's list is the tenant lookup, one query for the (studio, student) pairs
    # of the open packages and one for the instructions, whether the family has 1 or 15.
    from apps.common.factories import PackageFactory
    from apps.payments.models import PaymentInstructions

    owner = make_studio_owner()
    PaymentInstructions.objects.create(
        studio=owner.studio, account_holder="Studio", iban="IT60X0542811101000000123456"
    )
    parent = ParentAccountFactory()
    student = StudentFactory(teacher=owner)
    link_parent_to_student(parent, student)

    PackageFactory(student=student)
    open_one = _count(parent.user, "/api/v1/payment-instructions/open/")
    owner_read = _count(owner.user, "/api/v1/payment-instructions/")
    for _ in range(14):
        PackageFactory(student=student)

    assert open_one == _count(parent.user, "/api/v1/payment-instructions/open/") == 3
    assert owner_read == _count(owner.user, "/api/v1/payment-instructions/") == 2


def test_receipts_list_and_payments_with_receipts_hold_a_constant_query_count():
    # Phase 8: receipt number, student name and the cancelled flag come from the same query
    # (select_related), so more receipts do not mean more queries.
    from apps.common.factories import PaymentFactory, make_reversal
    from apps.payments.services import issue_receipt

    teacher = TeacherFactory()

    def seed(reverse: bool) -> None:
        student = StudentFactory(teacher=teacher)
        payment = PaymentFactory(student=student)
        issue_receipt(payment, language="it", actor=teacher.user)
        if reverse:
            make_reversal(payment)

    seed(False)
    receipts_one = _count(teacher.user, "/api/v1/receipts/")
    payments_one = _count(teacher.user, "/api/v1/payments/")
    for i in range(19):
        seed(i % 2 == 0)

    assert receipts_one == _count(teacher.user, "/api/v1/receipts/") == 3  # teacher, count, rows
    assert payments_one == _count(teacher.user, "/api/v1/payments/") == 3


def test_payment_account_read_holds_a_constant_query_count(settings):
    # Fase 9: la lettura dello stato è solo database; le voci "da controllare" (al massimo 20)
    # si leggono in una query, qualunque sia il loro numero.
    from apps.common.factories import StudioPaymentAccountFactory
    from apps.payments.models import WebhookEvent

    settings.ONLINE_PAYMENTS_ENABLED = True
    owner = make_studio_owner()
    account = StudioPaymentAccountFactory(studio=owner.studio)

    def attention(n: int) -> None:
        for i in range(n):
            WebhookEvent.objects.create(
                stripe_event_id=f"evt_{WebhookEvent.objects.count()}_{i}",
                type="refund.updated",
                payload={"data": {"object": {"amount": 1500}}},
                stripe_account_id=account.stripe_account_id,
                outcome=WebhookEvent.Outcome.NEEDS_ATTENTION,
                attention_kind="refund_unmatched",
            )

    attention(1)
    one = _count(owner.user, "/api/v1/payment-account/")
    attention(24)

    assert one == _count(owner.user, "/api/v1/payment-account/") == 3
