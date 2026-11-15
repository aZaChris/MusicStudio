"""TOTP (RFC 6238) con la sola libreria standard (ADR-029).

Sei cifre, passi di 30 secondi, HMAC-SHA1: la combinazione che ogni app di autenticazione
supporta. La verifica accetta il passo precedente, quello corrente e il successivo (scarto
dell'orologio) e rifiuta un passo già usato: un codice visto da sopra la spalla non si può
riutilizzare. Spiegazione: docs/learning/concetti/mfa-totp.md.
"""

import base64
import hmac
import secrets
import struct
import time
from urllib.parse import quote

STEP_SECONDS = 30
DIGITS = 6
WINDOW = 1


def new_secret() -> str:
    """160 bit casuali, in base32 (il formato che le app di autenticazione si aspettano)."""
    return base64.b32encode(secrets.token_bytes(20)).decode()


def code_at(secret: str, step: int, digits: int = DIGITS, algo: str = "sha1") -> str:
    # HOTP dell'RFC 4226 applicato al numero del passo: HMAC, troncamento dinamico, modulo 10^cifre.
    key = base64.b32decode(secret, casefold=True)
    digest = hmac.new(key, struct.pack(">Q", step), algo).digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(number % 10**digits).zfill(digits)


def current_step(now: float | None = None) -> int:
    return int((time.time() if now is None else now) // STEP_SECONDS)


def verify(secret: str, code: str, last_used_step: int = 0, now: float | None = None) -> int | None:
    """Restituisce il passo che corrisponde (da salvare come `last_used_step`) oppure None."""
    code = code.strip().replace(" ", "")
    if len(code) != DIGITS or not code.isdigit():
        return None
    step_now = current_step(now)
    for step in range(step_now - WINDOW, step_now + WINDOW + 1):
        # `step > last_used_step` è la difesa dal replay; compare_digest evita attacchi sui tempi.
        if step > last_used_step and hmac.compare_digest(code_at(secret, step), code):
            return step
    return None


def otpauth_uri(secret: str, account: str, issuer: str = "MusicStudio") -> str:
    label = quote(f"{issuer}:{account}")
    return (
        f"otpauth://totp/{label}?secret={secret}&issuer={quote(issuer)}"
        f"&algorithm=SHA1&digits={DIGITS}&period={STEP_SECONDS}"
    )
