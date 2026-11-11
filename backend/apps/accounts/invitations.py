"""Invitations: owners invite teachers; owners and teachers invite parents and adult
students (US3, research R2). Accepting creates the account with a password the invited
person chooses, and for parents records consent for their children.
"""

import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.audit import services as audit
from apps.common.scoping import students_visible_to
from apps.common.tenancy import TenantContext, resolve_tenant
from apps.students.models import ParentAccount, ParentStudentLink, Student
from apps.studios.models import Teacher

from .models import Invitation, User
from .services import check_new_password, normalize_email

Role = Invitation.Role


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def invitations_visible_to(ctx: TenantContext) -> QuerySet[Invitation]:
    """Owners see their studio's invitations; teachers see the ones they sent."""
    qs = Invitation.objects.prefetch_related("students")
    if ctx.is_owner and ctx.studio_id is not None:
        return qs.filter(studio_id=ctx.studio_id)
    if ctx.is_teacher:
        return qs.filter(invited_by_id=ctx.user_id)
    return qs.none()


def _allowed_roles(ctx: TenantContext) -> set[str]:
    if ctx.is_owner:
        return {Role.TEACHER, Role.PARENT, Role.STUDENT}
    if ctx.is_teacher:
        return {Role.PARENT, Role.STUDENT}
    return set()


def _check_students(ctx: TenantContext, role: str, student_ids: list[int]) -> list[Student]:
    if role == Role.TEACHER:
        if student_ids:
            raise ValidationError({"student_ids": "A teacher invitation has no students."})
        return []
    visible = list(students_visible_to(ctx).filter(pk__in=student_ids, is_active=True))
    if not student_ids or len(visible) != len(set(student_ids)):
        # Same message for "not yours" and "does not exist" (constitution I).
        raise ValidationError({"student_ids": "One or more students do not exist."})
    if role == Role.STUDENT:
        if len(visible) != 1:
            raise ValidationError({"student_ids": "A student invitation is for one student."})
        if not visible[0].is_adult:
            raise ValidationError({"student_ids": "Minors are invited through a parent."})
        if visible[0].user_id is not None:
            raise ValidationError({"student_ids": "This student already has an account."})
    return visible


@transaction.atomic
def create_invitation(
    ctx: TenantContext, inviter: User, *, email: str, role: str, student_ids: list[int]
) -> Invitation:
    if role not in _allowed_roles(ctx):
        raise PermissionDenied("You cannot send this kind of invitation.")
    students = _check_students(ctx, role, student_ids)
    studio_id = ctx.studio_id
    if studio_id is None:  # owners and teachers always belong to a studio
        raise PermissionDenied("You cannot send this kind of invitation.")
    email = normalize_email(email)
    # A new invitation replaces a pending one for the same person and role.
    Invitation.objects.filter(
        studio_id=studio_id, email=email, role=role, status=Invitation.Status.PENDING
    ).update(status=Invitation.Status.REVOKED)
    token = secrets.token_urlsafe(32)
    invitation = Invitation.objects.create(
        studio_id=studio_id,
        invited_by=inviter,
        email=email,
        role=role,
        token_hash=_hash(token),
        expires_at=timezone.now() + timedelta(days=settings.INVITATION_DAYS),
    )
    invitation.students.set(students)
    audit.record(
        audit.Action.INVITATION_SEND,
        actor=inviter,
        target=invitation,
        studio_id=studio_id,
        metadata={"role": role},
    )
    from .tasks import send_invitation_email

    transaction.on_commit(lambda: send_invitation_email.delay(invitation.pk, token))
    return invitation


def revoke_invitation(inviter: User, invitation: Invitation) -> None:
    if invitation.status != Invitation.Status.PENDING:
        raise ValidationError({"status": "Only a pending invitation can be revoked."})
    invitation.status = Invitation.Status.REVOKED
    invitation.save(update_fields=["status"])
    audit.record(
        audit.Action.INVITATION_REVOKE,
        actor=inviter,
        target=invitation,
        studio_id=invitation.studio_id,
    )


def _inviter_still_allowed(invitation: Invitation) -> bool:
    """The inviter may have left or lost the students since sending (FR-007)."""
    inviter = invitation.invited_by
    if inviter is None or not inviter.is_active:
        return False
    ctx = resolve_tenant(inviter)
    if ctx.studio_id != invitation.studio_id or invitation.role not in _allowed_roles(ctx):
        return False
    wanted = {s.pk for s in invitation.students.all()}
    visible = set(students_visible_to(ctx).filter(pk__in=wanted).values_list("pk", flat=True))
    return visible == wanted


def lookup(token: str) -> Invitation | None:
    """The live invitation for this token, or None (unknown, used, revoked, expired)."""
    invitation = (
        Invitation.objects.select_related("studio", "invited_by")
        .prefetch_related("students")
        .filter(token_hash=_hash(token), status=Invitation.Status.PENDING)
        .first()
    )
    if invitation is None or invitation.expires_at <= timezone.now():
        return None
    if not _inviter_still_allowed(invitation):
        return None
    return invitation


@transaction.atomic
def accept_invitation(
    token: str,
    *,
    signed_in: User | None,
    password: str = "",
    first_name: str = "",
    last_name: str = "",
    consent: bool = False,
) -> User:
    invitation = lookup(token)
    if invitation is None:
        raise ValidationError({"token": "invalid_or_expired"})
    invitation = Invitation.objects.select_for_update().get(pk=invitation.pk)
    if invitation.status != Invitation.Status.PENDING:
        raise ValidationError({"token": "invalid_or_expired"})
    students = list(invitation.students.all())
    if invitation.role == Role.PARENT and not consent:
        raise ValidationError({"consent": "Consent is required to see your children's data."})

    user = User.objects.filter(email__iexact=invitation.email).first()
    if user is not None:
        # Only a parent can join with an existing account, and only when signed in as it.
        if invitation.role != Role.PARENT or user.role != User.Role.PARENT or signed_in != user:
            raise ValidationError(
                {"token": "This address already has an account: sign in as it first."}
            )
    else:
        check_new_password(
            password, email=invitation.email, first_name=first_name, last_name=last_name
        )
        user = User(
            email=invitation.email,
            username=invitation.email,
            first_name=first_name,
            last_name=last_name,
            role=invitation.role,
            preferred_language=getattr(invitation.invited_by, "preferred_language", "it"),
            email_verified=True,  # the link reached this mailbox
            terms_accepted_at=timezone.now(),
        )
        user.set_password(password)
        user.save()

    if invitation.role == Role.TEACHER:
        Teacher.objects.create(user=user, studio_id=invitation.studio_id)
        audit.record(
            audit.Action.ROLE_CHANGE,
            actor=invitation.invited_by,
            target=user,
            studio_id=invitation.studio_id,
            metadata={"role": "teacher"},
        )
    elif invitation.role == Role.PARENT:
        parent, _ = ParentAccount.objects.get_or_create(user=user)
        for student in students:
            ParentStudentLink.objects.get_or_create(parent=parent, student=student)
        from apps.privacy.services import give_consent

        give_consent(parent, students)
    else:
        student = students[0]
        Student.objects.filter(pk=student.pk, user__isnull=True).update(user=user)

    invitation.status = Invitation.Status.ACCEPTED
    invitation.accepted_by = user
    invitation.save(update_fields=["status", "accepted_by"])
    audit.record(
        audit.Action.INVITATION_ACCEPT,
        actor=user,
        target=invitation,
        studio_id=invitation.studio_id,
        metadata={"role": invitation.role},
    )
    return user
