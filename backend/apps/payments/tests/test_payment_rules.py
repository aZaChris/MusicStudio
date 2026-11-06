import pytest
from django.core.exceptions import ValidationError

from apps.common.factories import PackageFactory, StudentFactory
from apps.payments.models import Payment

pytestmark = pytest.mark.django_db


def test_model_clean_enforces_package_student_rule_for_admin():
    student = StudentFactory()
    payment = Payment(
        student=student,
        package=PackageFactory(),  # another student's package
        amount="1",
        date="2026-01-01",
        method="cash",
    )

    with pytest.raises(ValidationError):
        payment.full_clean()


def test_payment_str():
    payment = Payment.objects.create(
        student=StudentFactory(first_name="Ada", last_name="L"),
        amount="5.00",
        date="2026-01-01",
        method="cash",
    )

    assert str(payment) == "Ada L — 5.00 (pending)"
