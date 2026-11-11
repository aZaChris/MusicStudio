"""Account emails (confirmation, reset, notices, invitations) in the recipient's language.

Bodies are plain-text templates in `accounts/templates/accounts/emails/<kind>_<lang>.txt`.
Logs name the kind and the user id only, never the address or the link (constitution X).
"""

import logging
from typing import Any

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

SUBJECTS: dict[str, dict[str, str]] = {
    "confirm_email": {
        "en": "Confirm your email — MusicStudio",
        "it": "Conferma il tuo indirizzo email — MusicStudio",
    },
    "duplicate_signup": {
        "en": "Someone tried to sign up with your email — MusicStudio",
        "it": "Qualcuno ha provato a registrarsi con la tua email — MusicStudio",
    },
    "password_reset": {
        "en": "Reset your password — MusicStudio",
        "it": "Reimposta la password — MusicStudio",
    },
    "password_changed": {
        "en": "Your password was changed — MusicStudio",
        "it": "La tua password è stata cambiata — MusicStudio",
    },
    "invitation": {
        "en": "You are invited to MusicStudio",
        "it": "Sei stato invitato su MusicStudio",
    },
    "parent_left": {
        "en": "A parent closed their account — MusicStudio",
        "it": "Un genitore ha chiuso il suo account — MusicStudio",
    },
}


def link(path: str, **params: str) -> str:
    """Absolute portal URL for `path` with query parameters."""
    from urllib.parse import urlencode

    query = f"?{urlencode(params)}" if params else ""
    return f"{settings.FRONTEND_URL.rstrip('/')}{path}{query}"


def send(kind: str, *, to: str, language: str, context: dict[str, Any], log_id: Any) -> None:
    lang = language if language in ("en", "it") else "en"
    body = render_to_string(f"accounts/emails/{kind}_{lang}.txt", context)
    send_mail(subject=SUBJECTS[kind][lang], message=body, from_email=None, recipient_list=[to])
    logger.info("account email sent", extra={"kind": kind, "ref": log_id})
