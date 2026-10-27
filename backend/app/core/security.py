"""Password hashing and bearer tokens using only the standard library (scrypt, constant-time comparison)."""
import base64
import hashlib
import hmac
import os
import secrets

_N, _R, _P, _DKLEN = 2 ** 14, 8, 1, 32


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_N, r=_R, p=_P, dklen=_DKLEN)
    return "scrypt${}${}${}${}${}".format(_N, _R, _P, base64.b64encode(salt).decode(), base64.b64encode(dk).decode())


def verify_password(password: str, stored: str | None) -> bool:
    """Always does the same amount of work, even for a missing user, to avoid revealing which usernames exist."""
    try:
        _, n, r, p, salt_b64, dk_b64 = (stored or "").split("$")
        salt, expected = base64.b64decode(salt_b64), base64.b64decode(dk_b64)
        got = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=int(n), r=int(r), p=int(p), dklen=len(expected))
        return hmac.compare_digest(got, expected)
    except (ValueError, TypeError):
        hashlib.scrypt(password.encode("utf-8"), salt=b"\0" * 16, n=_N, r=_R, p=_P, dklen=_DKLEN)  # burn equal time
        return False


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_digest(token: str) -> str:
    """Only this digest is stored, so a leaked database does not leak usable tokens."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
