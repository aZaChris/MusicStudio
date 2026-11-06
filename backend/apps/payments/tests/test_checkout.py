"""Online checkout of a package (US1, ADR-013)."""

import datetime

import pytest
from django.utils import timezone

from apps.common.factories import (
    PackageFactory,
    ParentAccountFactory,
    StudentFactory,
    link_parent_to_student,
)
from apps.common.tests.helpers import client_for
from apps.payments.models import CheckoutSession, Payment

pytestmark = pytest.mark.django_db


def _checkout(user, package):
    return client_for(user).post(f"/api/v1/packages/{package.id}/checkout/")


def test_parent_gets_a_stripe_link_for_the_package_price(fake_stripe):
    package = PackageFactory(price="120.00")
    parent = ParentAccountFactory()
    link_parent_to_student(parent, package.student)

    res = _checkout(parent.user, package)

    assert res.status_code == 200
    assert res.data["url"].startswith("https://checkout.stripe.com/")
    call = fake_stripe.created[0]
    assert call["amount_cents"] == 12000
    assert call["currency"] == "eur"
    assert call["idempotency_key"] == f"checkout-{res.data['checkout_id']}"
    assert call["customer_email"] == parent.user.email
    assert "payment_method_types" not in call  # dynamic payment methods (Stripe guidance)


def test_repeated_requests_reuse_the_open_attempt(fake_stripe):
    package = PackageFactory()
    user = package.student.teacher.user

    first = _checkout(user, package)
    second = _checkout(user, package)

    assert first.data == second.data
    assert len(fake_stripe.created) == 1
    assert CheckoutSession.objects.count() == 1


def test_expired_attempt_is_replaced(fake_stripe):
    package = PackageFactory()
    user = package.student.teacher.user
    first = _checkout(user, package)
    CheckoutSession.objects.filter(pk=first.data["checkout_id"]).update(
        expires_at=timezone.now() - datetime.timedelta(minutes=1)
    )

    second = _checkout(user, package)

    assert second.data["checkout_id"] != first.data["checkout_id"]
    assert len(fake_stripe.created) == 2


def test_paid_package_cannot_be_checked_out_again(fake_stripe):
    package = PackageFactory()
    Payment.objects.create(
        student=package.student,
        package=package,
        amount="120",
        date="2026-01-01",
        method="cash",
        status="paid",
    )

    res = _checkout(package.student.teacher.user, package)

    assert res.status_code == 409
    assert res.data["code"] == "package_already_paid"
    assert fake_stripe.created == []


def test_package_of_another_family_is_not_found(fake_stripe):
    parent = ParentAccountFactory()
    link_parent_to_student(parent, StudentFactory())

    assert _checkout(parent.user, PackageFactory()).status_code == 404


def test_without_stripe_configuration_checkout_is_unavailable(settings):
    settings.STRIPE_API_KEY = ""
    package = PackageFactory()

    res = _checkout(package.student.teacher.user, package)

    assert res.status_code == 503
    assert res.data["code"] == "payments_unavailable"
    assert CheckoutSession.objects.count() == 0


def test_stripe_failure_leaves_no_attempt_behind(fake_stripe):
    fake_stripe.fail_create = True
    package = PackageFactory()

    res = _checkout(package.student.teacher.user, package)

    assert res.status_code == 503
    assert CheckoutSession.objects.count() == 0


def test_live_keys_are_refused_at_startup():
    """Constitution IV: test mode only. Settings must refuse sk_live_/rk_live_ keys."""
    import os
    import subprocess
    import sys
    from pathlib import Path

    env = {**os.environ, "DJANGO_SECRET_KEY": "x" * 50, "STRIPE_API_KEY": "rk_live_123"}
    result = subprocess.run(
        [sys.executable, "-c", "import config.settings.dev"],
        cwd=Path(__file__).resolve().parents[3],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "test-mode key" in result.stderr
