"""Single-use links for email confirmation and password reset, without a token table (ADR-028).

- Reset: Django's PasswordResetTokenGenerator. The HMAC covers the password hash and the
  last login, so the link dies as soon as the password changes (including by a newer reset)
  and after `PASSWORD_RESET_TIMEOUT`.
- Confirmation: a signed value over (user id, email, email_verified), valid
  `EMAIL_CONFIRM_MAX_AGE_SECONDS`. It dies once the address is confirmed or changed.

Links carry `uid` (base64 user id) and `token`; only the backend can check them.
"""

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from .models import User

_CONFIRM_SALT = "accounts.confirm-email"


def encode_uid(user: User) -> str:
    return urlsafe_base64_encode(force_bytes(user.pk))


def _user_from_uid(uid: str) -> User | None:
    try:
        pk = int(force_str(urlsafe_base64_decode(uid)))
    except (TypeError, ValueError, OverflowError):
        return None
    return User.objects.filter(pk=pk).first()


def make_confirm_token(user: User) -> str:
    return signing.dumps([user.pk, user.email, user.email_verified], salt=_CONFIRM_SALT)


def user_for_confirm_token(uid: str, token: str) -> User | None:
    """The unconfirmed user the link was made for, or None (bad, expired or already used)."""
    user = _user_from_uid(uid)
    if user is None:
        return None
    try:
        payload = signing.loads(
            token, salt=_CONFIRM_SALT, max_age=settings.EMAIL_CONFIRM_MAX_AGE_SECONDS
        )
    except signing.BadSignature:  # includes SignatureExpired
        return None
    if payload != [user.pk, user.email, user.email_verified] or user.email_verified:
        return None
    return user


def make_reset_token(user: User) -> str:
    return default_token_generator.make_token(user)


def user_for_reset_token(uid: str, token: str) -> User | None:
    user = _user_from_uid(uid)
    if user is None or not user.is_active or not default_token_generator.check_token(user, token):
        return None
    return user
