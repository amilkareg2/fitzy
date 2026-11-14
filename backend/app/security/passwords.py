"""Password hashing with scrypt (standard library only).

Hash format: ``scrypt$<n>$<r>$<p>$<salt b64>$<hash b64>``. Only the hash is stored, in the
OWNER_PASSWORD_HASH secret; the password itself never leaves the owner's terminal.

Run this file directly to create a hash without installing anything:
``python3 backend/app/security/passwords.py``
"""

import base64
import hashlib
import hmac
import secrets

_N, _R, _P = 2**14, 8, 1
_DKLEN = 32
_MAXMEM = 64 * 1024 * 1024
MIN_PASSWORD_LENGTH = 12


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def hash_password(password: str) -> str:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"password must be at least {MIN_PASSWORD_LENGTH} characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=_DKLEN, maxmem=_MAXMEM
    )
    return f"scrypt${_N}${_R}${_P}${_b64(salt)}${_b64(digest)}"


def is_valid_hash(encoded: str) -> bool:
    parts = encoded.strip().split("$")
    if len(parts) != 6 or parts[0] != "scrypt":
        return False
    try:
        int(parts[1]), int(parts[2]), int(parts[3])
        base64.b64decode(parts[4], validate=True)
        base64.b64decode(parts[5], validate=True)
    except ValueError:
        return False
    return True


def verify_password(password: str, encoded: str) -> bool:
    """Constant-time check. Returns False (never raises) for a malformed hash."""
    if not is_valid_hash(encoded):
        return False
    _, n, r, p, salt_b64, hash_b64 = encoded.strip().split("$")
    expected = base64.b64decode(hash_b64)
    digest = hashlib.scrypt(
        password.encode(),
        salt=base64.b64decode(salt_b64),
        n=int(n),
        r=int(r),
        p=int(p),
        dklen=len(expected),
        maxmem=_MAXMEM,
    )
    return hmac.compare_digest(digest, expected)


if __name__ == "__main__":  # pragma: no cover - interactive helper
    import getpass
    import sys

    first = getpass.getpass("New Fitzy password: ")
    if getpass.getpass("Repeat it: ") != first:
        sys.exit("Passwords do not match.")
    try:
        print(hash_password(first))
    except ValueError as exc:
        sys.exit(str(exc))
