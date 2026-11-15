"""Link monouso per conferma email e reset password, senza una tabella di token (ADR-028).

- Reset: il PasswordResetTokenGenerator di Django. L'HMAC copre l'hash della password e
  l'ultimo accesso, quindi il link muore appena la password cambia (anche per un reset più
  recente) e dopo `PASSWORD_RESET_TIMEOUT`.
- Conferma: un valore firmato su (id utente, email, email_verified), valido
  `EMAIL_CONFIRM_MAX_AGE_SECONDS`. Muore quando l'indirizzo è confermato o cambiato.

I link portano `uid` (id utente in base64) e `token`; solo il backend sa verificarli.
Spiegazione: docs/learning/concetti/account-e-token-monouso.md.
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
    # Un uid malformato non è un errore: si risponde come per un utente inesistente.
    try:
        pk = int(force_str(urlsafe_base64_decode(uid)))
    except (TypeError, ValueError, OverflowError):
        return None
    return User.objects.filter(pk=pk).first()


def make_confirm_token(user: User) -> str:
    return signing.dumps([user.pk, user.email, user.email_verified], salt=_CONFIRM_SALT)


def user_for_confirm_token(uid: str, token: str) -> User | None:
    """L'utente non confermato per cui è fatto il link, o None (errato, scaduto o già usato)."""
    user = _user_from_uid(uid)
    if user is None:
        return None
    try:
        payload = signing.loads(
            token, salt=_CONFIRM_SALT, max_age=settings.EMAIL_CONFIRM_MAX_AGE_SECONDS
        )
    except signing.BadSignature:  # include SignatureExpired
        return None
    # Il valore firmato include lo stato di conferma: dopo la conferma (o un cambio di email) il
    # contenuto non coincide più e il link non vale, senza salvare nulla nel database.
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
