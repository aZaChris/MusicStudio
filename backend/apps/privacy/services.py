"""Consent, export and erasure (constitution X, ADR-032).

Erasure is anonymisation in place: what the studio must keep (payment and lesson amounts and
dates) stays, with the names and free text removed, so the studio's books still add up.
"""

import uuid
from collections.abc import Iterable
from datetime import datetime, timedelta
from functools import partial

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

from apps.accounts import services as account_services
from apps.accounts.models import Invitation, MfaDevice, User
from apps.audit import services as audit
from apps.common.exceptions import DomainConflict
from apps.lessons.models import Lesson
from apps.payments.models import CheckoutSession, Payment
from apps.students.models import ParentAccount, ParentStudentLink, Student

from . import selectors
from .models import ConsentRecord


def give_consent(parent: ParentAccount, students: Iterable[Student]) -> ConsentRecord:
    students = list(students)
    record = ConsentRecord.objects.create(
        parent=parent, notice_version=settings.PRIVACY_NOTICE_VERSION
    )
    record.students.set(students)
    for studio_id in {s.studio_id for s in students}:
        audit.record(
            audit.Action.CONSENT_GIVE,
            actor=parent.user,
            target=record,
            studio_id=studio_id,
            metadata={"notice_version": settings.PRIVACY_NOTICE_VERSION},
        )
    return record


class CheckoutOpen(DomainConflict):
    code = "checkout_open"


class StudioNotEmpty(DomainConflict):
    code = "studio_not_empty"


def anonymise_student(student: Student) -> None:
    """Replace a child's personal data; lessons, packages and payments keep their amounts."""
    student.first_name = "Allievo"
    student.last_name = f"cancellato #{student.pk}"
    student.instrument = ""
    student.is_active = False
    student.user = None
    student.anonymised_at = timezone.now()
    student.save()
    Lesson.objects.filter(student=student).update(notes="")


def _check_password(user: User, password: str) -> None:
    if not user.check_password(password):
        raise ValidationError({"password": "Wrong password."})


def _release_children(user: User, children: list[Student]) -> list[Student]:
    """Unlink `user` from `children`; anonymise those no other parent is linked to.
    Returns the children that stay because another parent remains."""
    parent = ParentAccount.objects.filter(user=user).first()
    kept: list[Student] = []
    for child in children:
        others = ParentStudentLink.objects.filter(student=child)
        if parent is not None:
            others = others.exclude(parent=parent)
        if others.exists():
            kept.append(child)
        else:
            anonymise_student(child)
    if parent is not None:
        ParentStudentLink.objects.filter(parent=parent, student__in=children).delete()
    return kept


def _notify_teachers(kept: list[Student]) -> None:
    from .tasks import notify_parent_left

    for child in kept:
        transaction.on_commit(partial(notify_parent_left.delay, child.pk))


@transaction.atomic
def erase_account(user: User, password: str) -> None:
    """Close the account and erase or anonymise what hangs off it (parent, adult student)."""
    _check_password(user, password)
    if user.role == User.Role.STUDIO_OWNER:
        from apps.studios.models import Teacher

        if (
            Student.objects.filter(studio__teachers__user=user).exists()
            and Teacher.objects.filter(user=user, is_owner=True).exists()
        ):
            raise StudioNotEmpty("The studio still has students.")
    children = list(selectors.students_of(user))
    if CheckoutSession.objects.filter(
        package__student__in=children, status=CheckoutSession.Status.OPEN
    ).exists():
        raise CheckoutOpen("An online payment is still pending.")
    studio_ids = {c.studio_id for c in children}
    old_email = user.email
    kept = _release_children(user, children)
    if user.role == User.Role.STUDENT:
        # The adult student's own record goes with their account.
        for child in children:
            anonymise_student(child)
    ConsentRecord.objects.filter(parent__user=user).delete()
    Invitation.objects.filter(email__iexact=old_email).delete()
    Invitation.objects.filter(accepted_by=user).delete()
    MfaDevice.objects.filter(user=user).delete()
    account_services.revoke_all_sessions(user)
    OutstandingToken.objects.filter(user=user).delete()
    ParentAccount.objects.filter(user=user).delete()
    marker = uuid.uuid4().hex
    user.first_name = ""
    user.last_name = ""
    user.email = f"erased-{marker}@invalid"
    user.username = f"erased-{marker}"
    user.is_active = False
    user.set_unusable_password()
    user.save()
    ids: list[int | None] = list(studio_ids) or [None]
    for studio_id in ids:
        audit.record(audit.Action.PRIVACY_ERASE, actor=user, target=user, studio_id=studio_id)
    _notify_teachers(kept)


@transaction.atomic
def withdraw_consent(user: User, consent_id: int, password: str) -> None:
    """Withdrawing consent erases the affected children from the parent's side: the parent
    is unlinked, and a child with no other parent is anonymised."""
    _check_password(user, password)
    consent = ConsentRecord.objects.filter(
        pk=consent_id, parent__user=user, withdrawn_at__isnull=True
    ).first()
    if consent is None:
        raise Http404
    children = list(consent.students.all())
    if CheckoutSession.objects.filter(
        package__student__in=children, status=CheckoutSession.Status.OPEN
    ).exists():
        raise CheckoutOpen("An online payment is still pending.")
    kept = _release_children(user, children)
    consent.withdrawn_at = timezone.now()
    consent.save(update_fields=["withdrawn_at"])
    for studio_id in {c.studio_id for c in children}:
        audit.record(
            audit.Action.CONSENT_WITHDRAW,
            actor=user,
            target=consent,
            studio_id=studio_id,
        )
    _notify_teachers(kept)


# --- Retention (ADR-032) ------------------------------------------------------------------
ARCHIVED_STUDENT = timedelta(days=730)  # 24 months after the last activity
PAYMENTS = timedelta(days=3650)  # 10 years, the accounting retention to be confirmed
AUDIT = timedelta(days=365)
UNCONFIRMED_SIGNUP = timedelta(days=7)


def run_retention(now: datetime | None = None) -> dict[str, int]:
    """Daily clean-up of data past its retention period; returns how many rows each rule hit.
    Safe to run twice: every rule only touches rows that are still past the limit."""
    now = now or timezone.now()
    cutoff = now - ARCHIVED_STUDENT
    stale = Student.objects.filter(
        is_active=False, anonymised_at__isnull=True, updated_at__lt=cutoff
    ).exclude(lessons__start_time__gte=cutoff)
    students = list(stale.distinct())
    for student in students:
        anonymise_student(student)
    payments, _ = Payment.objects.filter(date__lt=(now - PAYMENTS).date()).delete()
    return {
        "students_anonymised": len(students),
        "payments_deleted": payments,
        "audit_deleted": audit.purge_older_than(now - AUDIT),
        "signups_deleted": account_services.purge_unconfirmed(now - UNCONFIRMED_SIGNUP),
    }
