import base64

import pytest

from apps.accounts import totp

# RFC 6238 appendix B, SHA-1 seed "12345678901234567890", 8 digits.
SEED = base64.b32encode(b"12345678901234567890").decode()
VECTORS = [
    (59, "94287082"),
    (1111111109, "07081804"),
    (1111111111, "14050471"),
    (1234567890, "89005924"),
    (2000000000, "69279037"),
    (20000000000, "65353130"),
]


@pytest.mark.parametrize(("when", "expected"), VECTORS)
def test_rfc6238_vectors(when, expected):
    assert totp.code_at(SEED, when // 30, digits=8) == expected


def test_verify_accepts_drift_and_refuses_replay_and_junk():
    now = 1234567890
    code = totp.code_at(SEED, now // 30)
    step = totp.verify(SEED, code, now=now)
    assert step == now // 30
    assert totp.verify(SEED, code, last_used_step=step, now=now) is None  # replay
    assert totp.verify(SEED, code, now=now + 30) == step  # one step late
    assert totp.verify(SEED, code, now=now + 120) is None  # too old
    assert totp.verify(SEED, "12345", now=now) is None
    assert totp.verify(SEED, "abcdef", now=now) is None


def test_secret_and_uri():
    secret = totp.new_secret()
    assert len(base64.b32decode(secret)) == 20
    uri = totp.otpauth_uri(secret, "a@b.it")
    assert uri.startswith("otpauth://totp/MusicStudio%3Aa%40b.it?secret=")
    assert "period=30" in uri
