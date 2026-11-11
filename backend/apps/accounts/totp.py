"""TOTP (RFC 6238) with the standard library only (ADR-029).

Six digits, 30-second steps, HMAC-SHA1: the combination every authenticator app supports.
Verification accepts the previous, current and next step (clock drift) and refuses a step
that was already used, so a code seen over a shoulder cannot be replayed.
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
    """160 random bits, base32 (the format authenticator apps expect)."""
    return base64.b32encode(secrets.token_bytes(20)).decode()


def code_at(secret: str, step: int, digits: int = DIGITS, algo: str = "sha1") -> str:
    key = base64.b32decode(secret, casefold=True)
    digest = hmac.new(key, struct.pack(">Q", step), algo).digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(number % 10**digits).zfill(digits)


def current_step(now: float | None = None) -> int:
    return int((time.time() if now is None else now) // STEP_SECONDS)


def verify(secret: str, code: str, last_used_step: int = 0, now: float | None = None) -> int | None:
    """Return the matching step (store it as `last_used_step`) or None."""
    code = code.strip().replace(" ", "")
    if len(code) != DIGITS or not code.isdigit():
        return None
    step_now = current_step(now)
    for step in range(step_now - WINDOW, step_now + WINDOW + 1):
        if step > last_used_step and hmac.compare_digest(code_at(secret, step), code):
            return step
    return None


def otpauth_uri(secret: str, account: str, issuer: str = "MusicStudio") -> str:
    label = quote(f"{issuer}:{account}")
    return (
        f"otpauth://totp/{label}?secret={secret}&issuer={quote(issuer)}"
        f"&algorithm=SHA1&digits={DIGITS}&period={STEP_SECONDS}"
    )
