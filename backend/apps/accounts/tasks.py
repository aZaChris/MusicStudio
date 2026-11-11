from typing import Any

from celery import shared_task

from . import emails, services, tokens
from .models import User

# Transient SMTP errors are retried; a lost email is recoverable by the user (resend, new
# reset), so three tries are enough.
_RETRY = {"autoretry_for": (OSError,), "retry_backoff": True, "max_retries": 3}


@shared_task
def purge_expired_tokens() -> int:
    """Daily: keep the revocation tables bounded by the refresh-token lifetime."""
    return services.purge_expired_tokens()


@shared_task(**_RETRY)
def send_account_email(kind: str, user_id: int) -> None:
    """Email `kind` to a user. Links are made here, off the request path, so the HTTP
    response time does not reveal whether an account exists (research R3)."""
    user = User.objects.filter(pk=user_id).first()
    if user is None:
        return
    context: dict[str, Any] = {"first_name": user.first_name}
    if kind == "confirm_email":
        context["url"] = emails.link(
            "/confirm-email", uid=tokens.encode_uid(user), token=tokens.make_confirm_token(user)
        )
    elif kind == "password_reset":
        context["url"] = emails.link(
            "/reset-password", uid=tokens.encode_uid(user), token=tokens.make_reset_token(user)
        )
    else:
        context["login_url"] = emails.link("/login")
        context["reset_url"] = emails.link("/forgot-password")
    emails.send(
        kind, to=user.email, language=user.preferred_language, context=context, log_id=user_id
    )
