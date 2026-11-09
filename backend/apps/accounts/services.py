"""Session lifecycle: logout and revocation of refresh tokens (ADR-018).

Only refresh tokens are revocable. Access tokens stay valid until they expire (15 minutes
by default): checking them against the blacklist would cost a query on every request.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.exceptions import TokenBackendError, TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.state import token_backend
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken, Token

from .models import User

INVALID = "Token is invalid or expired."


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
