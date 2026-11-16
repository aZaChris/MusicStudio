"""Chi può pagare online e quando: stati del conto, interruttore, famiglie (US2, fase 9)."""

import pytest

from apps.common.factories import (
    PackageFactory,
    ParentAccountFactory,
    StudentFactory,
    StudioPaymentAccountFactory,
    connected_package,
    link_parent_to_student,
    make_student_account,
)
from apps.common.tests.helpers import client_for
from apps.payments.models import Payment, StudioPaymentAccount

pytestmark = pytest.mark.django_db
STATES = ["in_progress", "information_needed", "restricted", "disconnected"]


def _checkout(user, package):
    return client_for(user).post(f"/api/v1/packages/{package.pk}/checkout/")


def _can_pay(user, package) -> bool:
    return client_for(user).get(f"/api/v1/packages/{package.pk}/").data["can_pay_online"]


@pytest.mark.parametrize("state", STATES)
def test_only_an_active_account_lets_a_package_be_paid_online(fake_stripe, state):
    package = connected_package()
    StudioPaymentAccount.objects.filter(studio=package.student.studio).update(state=state)
    user = package.student.teacher.user

    res = _checkout(user, package)

    assert res.status_code == 409 and res.data["code"] == "online_payments_not_available"
    assert _can_pay(user, package) is False
    assert fake_stripe.created == []


def test_a_studio_with_no_account_cannot_take_online_payments(fake_stripe):
    package = PackageFactory()

    res = _checkout(package.student.teacher.user, package)

    assert res.status_code == 409 and res.data["code"] == "online_payments_not_available"
    assert _can_pay(package.student.teacher.user, package) is False


def test_the_switch_off_turns_everything_off_even_with_an_active_account(fake_stripe, settings):
    package = connected_package()
    settings.ONLINE_PAYMENTS_ENABLED = False

    assert _checkout(package.student.teacher.user, package).status_code == 409
    assert _can_pay(package.student.teacher.user, package) is False


def test_an_active_account_makes_an_open_package_payable_and_a_paid_one_not(fake_stripe):
    package = connected_package()
    user = package.student.teacher.user
    assert _can_pay(user, package) is True

    Payment.objects.create(
        student=package.student, package=package, amount="120", date="2026-11-16",
        method="cash", status="paid",
    )  # fmt: skip

    assert _can_pay(user, package) is False
    assert _checkout(user, package).data["code"] == "package_already_paid"


def test_a_linked_parent_pays_and_a_parent_of_another_family_cannot(fake_stripe):
    package = connected_package()
    mine = ParentAccountFactory()
    link_parent_to_student(mine, package.student)
    stranger = ParentAccountFactory()
    link_parent_to_student(stranger, StudentFactory())

    assert _checkout(mine.user, package).status_code == 200
    assert _checkout(stranger.user, package).status_code == 404
    assert client_for(stranger.user).get(f"/api/v1/packages/{package.pk}/").status_code == 404


def test_an_adult_student_can_pay_their_own_package(fake_stripe):
    package = connected_package()
    adult = make_student_account(package.student)

    assert _can_pay(adult, package) is True
    assert _checkout(adult, package).status_code == 200


def test_each_family_pays_to_the_right_studios_account(fake_stripe):
    parent = ParentAccountFactory()
    first = connected_package()
    second = connected_package()
    link_parent_to_student(parent, first.student)
    link_parent_to_student(parent, second.student)

    _checkout(parent.user, first)
    _checkout(parent.user, second)

    accounts = {call["stripe_account"] for call in fake_stripe.created}
    assert accounts == {
        first.student.studio.payment_account.stripe_account_id,
        second.student.studio.payment_account.stripe_account_id,
    }
    assert len(accounts) == 2


def test_the_account_of_one_studio_never_makes_another_studios_package_payable(fake_stripe):
    StudioPaymentAccountFactory()  # un altro studio, attivo
    package = PackageFactory()  # uno studio senza conto

    assert _can_pay(package.student.teacher.user, package) is False


def test_the_students_list_carries_can_pay_online_on_the_active_package(fake_stripe):
    # Il portale del genitore legge il pacchetto attivo dallo studente: deve portare il flag.
    package = connected_package()
    parent = ParentAccountFactory()
    link_parent_to_student(parent, package.student)

    rows = client_for(parent.user).get("/api/v1/students/").data["results"]

    assert rows[0]["active_package"]["can_pay_online"] is True


def test_the_students_list_says_false_without_an_active_account(fake_stripe):
    package = PackageFactory()
    parent = ParentAccountFactory()
    link_parent_to_student(parent, package.student)

    rows = client_for(parent.user).get("/api/v1/students/").data["results"]

    assert rows[0]["active_package"]["can_pay_online"] is False
