"""Ciclo di vita dell'account: registrazione, conferma, sessioni (ADR-018, ADR-028).

Solo i refresh token sono revocabili. I token di accesso restano validi fino alla scadenza (15
minuti di default): controllarli contro la lista nera costerebbe una query a ogni richiesta.
Spiegazione: docs/learning/concetti/revoca-token-jwt.md.

I punti di ingresso anonimi (registrazione, nuovo invio della conferma, reset password) devono
comportarsi allo stesso modo che l'indirizzo sia registrato o no: stessa risposta, stesso lavoro
sul percorso della richiesta (l'hash di una password si calcola in entrambi i rami), email
inviate dopo da un task. Spiegazione: docs/learning/concetti/account-e-token-monouso.md.
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
    """Mette in coda una email dell'account a transazione conclusa (la riga deve esistere)."""
    from .tasks import send_account_email

    transaction.on_commit(lambda: send_account_email.delay(kind, user_id))


def check_new_password(password: str, **user_fields: str) -> None:
    """I validatori di Django, con gli attributi dell'utente (controllo di somiglianza)."""
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
    """Crea un titolare non confermato e il suo studio, oppure avvisa il titolare già esistente.

    Non restituisce nulla di proposito: chi chiama deve rispondere allo stesso modo nei due casi.
    """
    email = normalize_email(email)
    # Si valida prima di cercare l'indirizzo: un errore "password debole" non deve dipendere
    # dall'esistenza dell'account.
    check_new_password(password, email=email, first_name=first_name, last_name=last_name)
    existing = User.objects.filter(email__iexact=email).first()
    if existing is not None:
        make_password(password)  # stesso costo di hashing dell'altro ramo
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
    """Uniforme: chi chiama risponde allo stesso modo qualunque cosa succeda qui (research R3)."""
    user = User.objects.filter(email__iexact=normalize_email(email), is_active=True).first()
    if user is not None and user.has_usable_password():
        _send_later("password_reset", user.pk)


@transaction.atomic
def _set_new_password(user: User, password: str, action: str) -> None:
    check_new_password(
        password, email=user.email, first_name=user.first_name, last_name=user.last_name
    )
    user.set_password(password)
    # Una nuova password toglie anche il blocco: chi controlla la casella email ha provato chi è.
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
    """Cambio da utente connesso. Tutte le sessioni finiscono, anche questa: si rifà l'accesso."""
    if not user.check_password(current_password):
        raise ValidationError({"current_password": "Wrong password."})
    _set_new_password(user, new_password, audit.Action.PASSWORD_CHANGE)


def purge_unconfirmed(cutoff: datetime) -> int:
    """Conservazione: account auto-registrati mai confermati da `cutoff`, con il loro studio."""
    from apps.studios.models import Studio

    stale = User.objects.filter(email_verified=False, date_joined__lt=cutoff)
    with transaction.atomic():
        studio_ids = list(Studio.objects.filter(owner__user__in=stale).values_list("pk", flat=True))
        _, per_model = stale.delete()  # a cascata sulla riga Teacher; studio.owner -> NULL
        # Uno studio PROTEGGE i suoi studenti; un titolare non confermato non può averne aggiunti.
        Studio.objects.filter(pk__in=studio_ids, students__isnull=True).delete()
    return per_model.get("accounts.User", 0)


def _studio_id(user: User) -> int | None:
    from apps.studios.models import Teacher

    return Teacher.objects.filter(user=user).values_list("studio_id", flat=True).first()


def logout(user: User, raw_refresh: str) -> None:
    """Mette in lista nera un refresh token di `user`. Idempotente: un secondo logout non fa nulla.

    Il token di un altro utente si rifiuta con lo stesso messaggio di uno malformato, così
    l'endpoint non si può usare per scoprire se il token di qualcun altro è valido.
    """
    try:
        token_backend.decode(raw_refresh, verify=True)  # type: ignore[arg-type]  # firma, scadenza
        # verify=False qui salta solo il controllo della lista nera, così un logout ripetuto non fa
        # nulla.
        token = RefreshToken(raw_refresh, verify=False)  # type: ignore[arg-type]
        Token.verify(token)  # tipo del token e scadenza, senza il controllo della lista nera
    except (TokenBackendError, TokenError) as exc:
        raise ValidationError({"refresh": INVALID}) from exc
    if str(token.payload.get(api_settings.USER_ID_CLAIM)) != str(user.pk):
        raise ValidationError({"refresh": INVALID})
    token.blacklist()


@transaction.atomic
def revoke_all_sessions(user: User) -> int:
    """Mette in lista nera ogni refresh token non scaduto di `user`; restituisce quanti."""
    live = OutstandingToken.objects.filter(
        user=user, expires_at__gt=timezone.now(), blacklistedtoken__isnull=True
    )
    tokens = list(live)
    BlacklistedToken.objects.bulk_create([BlacklistedToken(token=t) for t in tokens])
    return len(tokens)


def purge_expired_tokens() -> int:
    """Cancella i token emessi scaduti (le righe della lista nera seguono a cascata)."""
    deleted, _ = OutstandingToken.objects.filter(expires_at__lte=timezone.now()).delete()
    return deleted


# --- Blocco per singolo account (research R4, ADR-028) ------------------------------------
LOCK_AFTER_FAILURES = 5
BASE_LOCK = timedelta(minutes=15)
MAX_LOCK = timedelta(hours=24)


def is_locked(user: User) -> bool:
    return user.locked_until is not None and user.locked_until > timezone.now()


def register_login_failure(user: User) -> None:
    """Conta una password sbagliata.

    L'update con F() prende il lock sulla riga, quindi i tentativi in parallelo si contano uno per
    volta; il quinto errore blocca per 15 min x 2^livello (massimo 24 ore).
    """
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
