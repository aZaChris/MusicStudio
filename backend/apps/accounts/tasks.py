"""Task Celery dell'account: email e pulizia dei token scaduti (ADR-016)."""

from typing import Any

from celery import shared_task
from django.conf import settings

from . import emails, services, tokens
from .models import User

# Gli errori SMTP temporanei si ritentano; una email persa l'utente la può recuperare (nuovo
# invio, nuovo reset), quindi tre tentativi bastano.
_RETRY = {"autoretry_for": (OSError,), "retry_backoff": True, "max_retries": 3}


@shared_task
def purge_expired_tokens() -> int:
    """Ogni giorno: tiene le tabelle di revoca limitate alla durata dei refresh token."""
    return services.purge_expired_tokens()


@shared_task(**_RETRY)
def send_account_email(kind: str, user_id: int) -> None:
    """Invia la email `kind` a un utente.

    I link si creano qui, fuori dal percorso della richiesta, così il tempo di risposta HTTP non
    rivela se un account esiste (research R3).
    """
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


@shared_task(**_RETRY)
def send_invitation_email(invitation_id: int, token: str) -> None:
    """Il token in chiaro esiste solo qui e nella email: il database tiene solo il suo hash."""
    from .models import Invitation

    invitation = (
        Invitation.objects.select_related("studio", "invited_by").filter(pk=invitation_id).first()
    )
    if invitation is None or invitation.status != Invitation.Status.PENDING:
        return
    language = getattr(invitation.invited_by, "preferred_language", "it")
    emails.send(
        "invitation",
        to=invitation.email,
        language=language,
        context={
            "studio_name": invitation.studio.name,
            "role": invitation.role,
            "days": settings.INVITATION_DAYS,
            "url": emails.link("/invitations/accept", token=token),
        },
        log_id=invitation_id,
    )
