"""Write use-cases for payments: manual records and online checkout (Stripe)."""

import datetime
import logging
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit import services as audit
from apps.common.exceptions import DomainConflict
from apps.packages.models import Package
from apps.students.models import Student

from . import gateway
from .models import CheckoutSession, Payment, WebhookEvent


def ensure_package_matches_student(student: Student, package: Package | None) -> None:
    """The one place that enforces "a payment's package belongs to the payment's student"."""
    if package is not None and package.student_id != student.pk:
        raise ValidationError(
            {"package": "Package must belong to the same student as the payment."}
        )


def _record_audit(payment: Payment, actor: Any) -> None:
    audit.record(
        audit.Action.PAYMENT_RECORD,
        actor=actor,
        target=payment,
        studio_id=payment.student.studio_id,
        metadata={"method": payment.method, "amount": str(payment.amount)},
    )


def create_payment(
    *, student: Student, package: Package | None = None, actor: Any = None, **fields: Any
) -> Payment:
    """Record a payment by hand. `actor` is the signed-in user (None for the system)."""
    ensure_package_matches_student(student, package)
    payment = Payment.objects.create(student=student, package=package, **fields)
    _record_audit(payment, actor)
    return payment


# The only allowed status changes. "paid" is final: money records must not silently go back.
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    Payment.Status.PENDING: frozenset({Payment.Status.PAID, Payment.Status.OVERDUE}),
    Payment.Status.OVERDUE: frozenset({Payment.Status.PAID}),
    Payment.Status.PAID: frozenset(),
}


def ensure_transition_allowed(current: str, target: str) -> None:
    if target != current and target not in ALLOWED_TRANSITIONS[current]:
        raise ValidationError({"status": f"Cannot change status from {current} to {target}."})


def update_payment(payment: Payment, **changes: Any) -> Payment:
    if "status" in changes:
        ensure_transition_allowed(payment.status, changes["status"])
    for field, value in changes.items():
        setattr(payment, field, value)
    ensure_package_matches_student(payment.student, payment.package)
    payment.save()
    return payment


# --- Online payments (phase 3, ADR-013/014) ---------------------------------------------

logger = logging.getLogger(__name__)


class PackageAlreadyPaid(DomainConflict):
    code = "package_already_paid"


def package_is_paid(package: Package) -> bool:
    return Payment.objects.filter(package=package, status=Payment.Status.PAID).exists()


def _cents(amount: Decimal) -> int:
    return int((amount * 100).quantize(Decimal("1")))


def start_checkout(package: Package, *, user: Any) -> CheckoutSession:
    """Return an open checkout attempt for `package`, creating one if needed.

    The package row is locked for the whole operation, Stripe call included: a double
    click waits for the first request and then reuses its attempt instead of opening a
    second payment page. The Stripe call carries an idempotency key, so the SDK's own
    network retries cannot create duplicate sessions either. If Stripe fails, the
    transaction rolls back and no attempt is stored.
    """
    if package_is_paid(package):
        raise PackageAlreadyPaid("This package is already paid.")
    with transaction.atomic():
        # Lock and re-read: the price charged is the one in the database right now.
        package = Package.objects.select_for_update().select_related("student").get(pk=package.pk)
        reusable = (
            CheckoutSession.objects.filter(
                package=package,
                status=CheckoutSession.Status.OPEN,
                stripe_session_id__isnull=False,
                expires_at__gt=timezone.now() + datetime.timedelta(minutes=1),
            )
            .order_by("-created_at")
            .first()
        )
        if reusable is not None:
            return reusable

        checkout = CheckoutSession.objects.create(
            package=package,
            created_by=user if getattr(user, "is_authenticated", False) else None,
            amount=package.price,
            currency=settings.STRIPE_CURRENCY,
        )
        info = gateway.create_checkout_session(
            checkout_id=str(checkout.id),
            amount_cents=_cents(package.price),
            currency=checkout.currency,
            description=f"{package.total_lessons} lessons — {package.student.full_name}",
            expires_at=timezone.now() + datetime.timedelta(minutes=settings.CHECKOUT_TTL_MINUTES),
            idempotency_key=f"checkout-{checkout.id}",
            customer_email=getattr(user, "email", None)
            if getattr(user, "role", "") == "parent"
            else None,
        )
        checkout.stripe_session_id = info.id
        checkout.url = info.url
        checkout.expires_at = info.expires_at
        checkout.save(update_fields=["stripe_session_id", "url", "expires_at", "updated_at"])
        return checkout


def record_webhook_event(event: dict[str, Any]) -> tuple[WebhookEvent, bool]:
    """Store a verified event once; schedule processing only for the first delivery."""
    from .tasks import process_webhook_event  # tasks import services: avoid a cycle

    with transaction.atomic():
        stored, created = WebhookEvent.objects.get_or_create(
            stripe_event_id=event["id"],
            defaults={"type": event.get("type", ""), "payload": event},
        )
        if created:
            # After commit: the worker must be able to read the row it is told to process.
            transaction.on_commit(lambda: process_webhook_event.delay(stored.pk))
    return stored, created


FULFIL_EVENTS = {"checkout.session.completed", "checkout.session.async_payment_succeeded"}
HANDLED_EVENTS = FULFIL_EVENTS | {
    "checkout.session.async_payment_failed",
    "checkout.session.expired",
}


def process_webhook_event(event_pk: int) -> bool:
    """Apply a stored event exactly once. Safe to call any number of times."""
    with transaction.atomic():
        event = WebhookEvent.objects.select_for_update().get(pk=event_pk)
        if event.processed_at is not None:
            return False
        event.attempts += 1
        if event.type in HANDLED_EVENTS:
            session = gateway.SessionInfo.from_dict(event.payload["data"]["object"])
            _apply_to_checkout(session, failed=event.type.endswith("async_payment_failed"))
        event.processed_at = timezone.now()
        event.save(update_fields=["processed_at", "attempts"])
        return True


def _apply_to_checkout(session: gateway.SessionInfo, *, failed: bool = False) -> None:
    checkout = (
        CheckoutSession.objects.select_for_update()
        .select_related("package__student")
        .filter(stripe_session_id=session.id)
        .first()
    )
    if checkout is None:
        logger.warning("Stripe session %s matches no checkout attempt; ignored", session.id)
        return
    apply_session_state(checkout, session, failed=failed)


def apply_session_state(
    checkout: CheckoutSession, session: gateway.SessionInfo, *, failed: bool = False
) -> None:
    """Move a (locked) checkout attempt to the state Stripe reports. Idempotent.

    Fulfil only when the money is there: with delayed payment methods (e.g. SEPA debit)
    the session completes as `unpaid` and the result arrives later.
    """
    if checkout.status != CheckoutSession.Status.OPEN:
        return  # terminal states never change; replays are no-ops
    if session.status == "complete" and session.payment_status in ("paid", "no_payment_required"):
        _fulfil(checkout, session)
    elif failed:
        checkout.status = CheckoutSession.Status.FAILED
        checkout.save(update_fields=["status", "updated_at"])
    elif session.status == "expired":
        checkout.status = CheckoutSession.Status.EXPIRED
        checkout.save(update_fields=["status", "updated_at"])


def _fulfil(checkout: CheckoutSession, session: gateway.SessionInfo) -> None:
    package = checkout.package
    if package_is_paid(package):
        # Paid by hand meanwhile: the money was still taken, so record it and warn.
        logger.warning("Package %s was already paid; recording online payment too", package.pk)
    amount = (
        Decimal(session.amount_total) / 100 if session.amount_total is not None else checkout.amount
    )
    payment = Payment.objects.create(
        student=package.student,
        package=package,
        amount=amount,  # what Stripe actually charged, even if the price changed since
        date=timezone.localdate(),
        method=Payment.Method.CARD,
        status=Payment.Status.PAID,
        checkout=checkout,
    )
    _record_audit(payment, None)
    checkout.status = CheckoutSession.Status.COMPLETED
    checkout.save(update_fields=["status", "updated_at"])


def reconcile_open_checkouts(limit: int = 100) -> int:
    """Safety net for lost webhooks: ask Stripe about open attempts past their expiry."""
    stale = CheckoutSession.objects.filter(
        status=CheckoutSession.Status.OPEN,
        stripe_session_id__isnull=False,
        expires_at__lt=timezone.now(),
    ).values_list("pk", "stripe_session_id")[:limit]
    resolved = 0
    for pk, session_id in stale:
        if session_id is None:  # excluded by the filter; keeps the type checker honest
            continue
        session = gateway.retrieve_checkout_session(session_id)
        with transaction.atomic():
            checkout = (
                CheckoutSession.objects.select_for_update()
                .select_related("package__student")
                .get(pk=pk)
            )
            apply_session_state(checkout, session)
            resolved += checkout.status != CheckoutSession.Status.OPEN
    return resolved
