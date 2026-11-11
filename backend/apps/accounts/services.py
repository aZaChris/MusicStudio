"""Account lifecycle: sign-up, confirmation, sessions (ADR-018, ADR-028).

Only refresh tokens are revocable. Access tokens stay valid until they expire (15 minutes
by default): checking them against the blacklist would cost a query on every request.

Anonymous entry points (register, resend confirmation, password reset) must behave the
same whether or not an address is registered: same response, same work on the request
path (a password hash is computed in both branches), emails sent later by a task.
"""

from datetime import datetime, timedelta

from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework_simplejwt.exceptions import TokenBackendError, TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.state import token_backend
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken, Token

from apps.audit import services as audit
from apps.studios.services import create_solo_teacher

from . import tokens
from .models import User

INVALID = "Token is invalid or expired."


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _send_later(kind: str, user_id: int) -> None:
    """Queue an account email once the transaction commits (the row must exist)."""
    from .tasks import send_account_email

    transaction.on_commit(lambda: send_account_email.delay(kind, user_id))


def check_new_password(password: str, **user_fields: str) -> None:
    """Django's validators, with the user's own attributes (similarity check)."""
    try:
        validate_password(password, user=User(**user_fields))
    except ValidationError as error:
        raise ValidationError({"password": error.messages}) from error


@transaction.atomic
def register_owner(
    *,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    studio_name: str,
    language: str = User.Language.IT,
) -> None:
    """Create an unconfirmed studio owner and their studio, or tell the existing owner.

    Returns nothing on purpose: the caller must answer the same in both cases.
    """
    email = normalize_email(email)
    # Validate before looking the address up: a "weak password" error must not depend on
    # whether the account exists.
    check_new_password(password, email=email, first_name=first_name, last_name=last_name)
    existing = User.objects.filter(email__iexact=email).first()
    if existing is not None:
        make_password(password)  # same hashing cost as the other branch
        _send_later("duplicate_signup", existing.pk)
        return
    user = User(
        email=email,
        username=email,
        first_name=first_name,
        last_name=last_name,
        role=User.Role.STUDIO_OWNER,
        preferred_language=language,
        email_verified=False,
        terms_accepted_at=timezone.now(),
    )
    user.set_password(password)
    user.save()
    teacher = create_solo_teacher(user, studio_name=studio_name)
    audit.record(audit.Action.REGISTRATION, actor=user, target=user, studio_id=teacher.studio_id)
    _send_later("confirm_email", user.pk)


def confirm_email(uid: str, token: str) -> User:
    user = tokens.user_for_confirm_token(uid, token)
    if user is None:
        raise ValidationError({"token": "invalid_or_expired"})
    user.email_verified = True
    user.save(update_fields=["email_verified"])
    audit.record(audit.Action.EMAIL_CONFIRM, actor=user, target=user, studio_id=_studio_id(user))
    return user


def resend_confirmation(email: str) -> None:
    user = User.objects.filter(email__iexact=normalize_email(email), is_active=True).first()
    if user is not None and not user.email_verified:
        _send_later("confirm_email", user.pk)


def request_password_reset(email: str) -> None:
    """Uniform: the caller answers the same whatever happens here (research R3)."""
    user = User.objects.filter(email__iexact=normalize_email(email), is_active=True).first()
    if user is not None and user.has_usable_password():
        _send_later("password_reset", user.pk)


@transaction.atomic
def _set_new_password(user: User, password: str, action: str) -> None:
    check_new_password(
        password, email=user.email, first_name=user.first_name, last_name=user.last_name
    )
    user.set_password(password)
    # A new password also clears a lock: the owner of the mailbox proved who they are.
    user.failed_logins = 0
    user.lock_level = 0
    user.locked_until = None
    user.save(update_fields=["password", "failed_logins", "lock_level", "locked_until"])
    revoke_all_sessions(user)
    audit.record(action, actor=user, target=user, studio_id=_studio_id(user))
    _send_later("password_changed", user.pk)


def reset_password(uid: str, token: str, new_password: str) -> None:
    user = tokens.user_for_reset_token(uid, token)
    if user is None:
        raise ValidationError({"token": "invalid_or_expired"})
    _set_new_password(user, new_password, audit.Action.PASSWORD_RESET)


def change_password(user: User, current_password: str, new_password: str) -> None:
    """Signed-in change. Every session ends, including this one: the client signs in again."""
    if not user.check_password(current_password):
        raise ValidationError({"current_password": "Wrong password."})
    _set_new_password(user, new_password, audit.Action.PASSWORD_CHANGE)


def purge_unconfirmed(cutoff: datetime) -> int:
    """Retention: self-registered accounts never confirmed since `cutoff`, with their studio."""
    from apps.studios.models import Studio

    stale = User.objects.filter(email_verified=False, date_joined__lt=cutoff)
    with transaction.atomic():
        studio_ids = list(Studio.objects.filter(owner__user__in=stale).values_list("pk", flat=True))
        _, per_model = stale.delete()  # cascades to the Teacher row; studio.owner -> NULL
        # A studio PROTECTs its students; an unconfirmed owner cannot have added any.
        Studio.objects.filter(pk__in=studio_ids, students__isnull=True).delete()
    return per_model.get("accounts.User", 0)


def _studio_id(user: User) -> int | None:
    from apps.studios.models import Teacher

    return Teacher.objects.filter(user=user).values_list("studio_id", flat=True).first()


def logout(user: User, raw_refresh: str) -> None:
    """Blacklist one refresh token of `user`. Idempotent: a second logout is a no-op.

    A token of another user is refused with the same message as a malformed one, so the
    endpoint cannot be used to learn whether someone else's token is valid.
    """
    try:
        token_backend.decode(raw_refresh, verify=True)  # type: ignore[arg-type]  # signature, expiry
        # verify=False here only skips the blacklist check, so a repeated logout is a no-op.
        token = RefreshToken(raw_refresh, verify=False)  # type: ignore[arg-type]
        Token.verify(token)  # token type and expiry, without the blacklist check
    except (TokenBackendError, TokenError) as exc:
        raise ValidationError({"refresh": INVALID}) from exc
    if str(token.payload.get(api_settings.USER_ID_CLAIM)) != str(user.pk):
        raise ValidationError({"refresh": INVALID})
    token.blacklist()


@transaction.atomic
def revoke_all_sessions(user: User) -> int:
    """Blacklist every unexpired refresh token of `user`; returns how many were revoked."""
    live = OutstandingToken.objects.filter(
        user=user, expires_at__gt=timezone.now(), blacklistedtoken__isnull=True
    )
    tokens = list(live)
    BlacklistedToken.objects.bulk_create([BlacklistedToken(token=t) for t in tokens])
    return len(tokens)


def purge_expired_tokens() -> int:
    """Delete expired outstanding tokens (their blacklist rows cascade)."""
    deleted, _ = OutstandingToken.objects.filter(expires_at__lte=timezone.now()).delete()
    return deleted


# --- Per-account lockout (research R4, ADR-028) -------------------------------------------
LOCK_AFTER_FAILURES = 5
BASE_LOCK = timedelta(minutes=15)
MAX_LOCK = timedelta(hours=24)


def is_locked(user: User) -> bool:
    return user.locked_until is not None and user.locked_until > timezone.now()


def register_login_failure(user: User) -> None:
    """Count a wrong password. The F() update takes the row lock, so parallel attempts
    are counted one by one; the fifth failure locks for 15 min x 2^level (cap 24 h)."""
    with transaction.atomic():
        User.objects.filter(pk=user.pk).update(failed_logins=F("failed_logins") + 1)
        fresh = User.objects.select_for_update().get(pk=user.pk)
        locked = fresh.failed_logins >= LOCK_AFTER_FAILURES
        if locked:
            duration = min(BASE_LOCK * 2**fresh.lock_level, MAX_LOCK)
            fresh.locked_until = timezone.now() + duration
            fresh.lock_level = min(fresh.lock_level + 1, 10)
            fresh.failed_logins = 0
            fresh.save(update_fields=["locked_until", "lock_level", "failed_logins"])
        audit.record(
            "login.locked" if locked else "login.failure",
            actor=fresh,
            outcome=audit.Outcome.DENIED if locked else audit.Outcome.FAILURE,
        )


def register_login_success(user: User) -> None:
    if user.failed_logins or user.lock_level or user.locked_until:
        User.objects.filter(pk=user.pk).update(failed_logins=0, lock_level=0, locked_until=None)
