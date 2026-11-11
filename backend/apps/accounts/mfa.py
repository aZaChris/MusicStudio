"""Second factor for owners and teachers (ADR-029, research R5).

Sign-in with MFA on is two steps: the password gives a signed `mfa_token` (5 minutes),
then the token plus a TOTP or recovery code gives the JWT pair. A wrong code counts
against the account lockout like a wrong password.
"""

import hashlib
import secrets

from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit import services as audit

from . import services, totp
from .models import MfaDevice, RecoveryCode, User

RECOVERY_CODES = 10
MFA_TOKEN_MAX_AGE = 300
_SALT = "accounts.mfa-login"
ELIGIBLE_ROLES = (User.Role.TEACHER, User.Role.STUDIO_OWNER)


def is_eligible(user: User) -> bool:
    return user.role in ELIGIBLE_ROLES


def is_enabled(user: User) -> bool:
    return MfaDevice.objects.filter(user=user, confirmed_at__isnull=False).exists()


def status(user: User) -> dict[str, int | bool]:
    left = RecoveryCode.objects.filter(
        device__user=user, device__confirmed_at__isnull=False, used_at__isnull=True
    ).count()
    return {"enabled": is_enabled(user), "recovery_codes_left": left}


def begin_setup(user: User) -> tuple[str, str]:
    """Create (or replace an unconfirmed) device; returns the secret and the otpauth URI."""
    if is_enabled(user):
        raise ValidationError({"detail": "mfa_already_enabled"})
    secret = totp.new_secret()
    MfaDevice.objects.update_or_create(user=user, defaults={"secret": secret, "last_used_step": 0})
    return secret, totp.otpauth_uri(secret, user.email)


def _new_recovery_codes(device: MfaDevice) -> list[str]:
    device.recovery_codes.all().delete()
    codes = [f"{secrets.token_hex(3)}-{secrets.token_hex(2)}" for _ in range(RECOVERY_CODES)]
    RecoveryCode.objects.bulk_create(
        RecoveryCode(device=device, code_hash=_hash(code)) for code in codes
    )
    return codes


def _hash(code: str) -> str:
    return hashlib.sha256(_clean_recovery(code).encode()).hexdigest()


def _clean_recovery(code: str) -> str:
    return code.strip().lower().replace(" ", "")


@transaction.atomic
def confirm_setup(user: User, code: str) -> list[str]:
    device = MfaDevice.objects.select_for_update().filter(user=user).first()
    if device is None or device.confirmed_at is not None:
        raise ValidationError({"code": "no_pending_setup"})
    step = totp.verify(device.secret, code)
    if step is None:
        raise ValidationError({"code": "invalid_code"})
    device.confirmed_at = timezone.now()
    device.last_used_step = step
    device.save(update_fields=["confirmed_at", "last_used_step"])
    audit.record(audit.Action.MFA_ENABLE, actor=user, target=user)
    return _new_recovery_codes(device)


@transaction.atomic
def check_second_factor(user: User, code: str) -> bool:
    """True if `code` is a fresh TOTP code or an unused recovery code (which it consumes)."""
    device = (
        MfaDevice.objects.select_for_update().filter(user=user, confirmed_at__isnull=False).first()
    )
    if device is None:
        return False
    step = totp.verify(device.secret, code, device.last_used_step)
    if step is not None:
        device.last_used_step = step
        device.save(update_fields=["last_used_step"])
        return True
    recovery = device.recovery_codes.filter(code_hash=_hash(code), used_at__isnull=True).first()
    if recovery is None:
        return False
    recovery.used_at = timezone.now()
    recovery.save(update_fields=["used_at"])
    audit.record(audit.Action.MFA_RECOVERY_USED, actor=user, target=user)
    return True


def _require_password_and_code(user: User, password: str, code: str) -> None:
    if not user.check_password(password):
        raise ValidationError({"password": "Wrong password."})
    if not check_second_factor(user, code):
        raise ValidationError({"code": "invalid_code"})


@transaction.atomic
def disable(user: User, password: str, code: str) -> None:
    _require_password_and_code(user, password, code)
    MfaDevice.objects.filter(user=user).delete()
    audit.record(audit.Action.MFA_DISABLE, actor=user, target=user)


@transaction.atomic
def regenerate_recovery_codes(user: User, password: str, code: str) -> list[str]:
    _require_password_and_code(user, password, code)
    device = MfaDevice.objects.get(user=user)
    return _new_recovery_codes(device)


def make_login_token(user: User) -> str:
    return signing.dumps(user.pk, salt=_SALT)


def user_from_login_token(token: str) -> User | None:
    try:
        pk = signing.loads(token, salt=_SALT, max_age=MFA_TOKEN_MAX_AGE)
    except signing.BadSignature:
        return None
    return User.objects.filter(pk=pk, is_active=True).first()


def complete_login(token: str, code: str) -> User | None:
    """Second step of sign-in: the user if token and code are good, else None."""
    user = user_from_login_token(token)
    if user is None or services.is_locked(user):
        return None
    if not check_second_factor(user, code):
        services.register_login_failure(user)
        return None
    services.register_login_success(user)
    audit.record(audit.Action.LOGIN_SUCCESS, actor=user)
    return user
