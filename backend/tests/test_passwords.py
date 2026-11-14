import pytest

from app.security.passwords import hash_password, is_valid_hash, verify_password


def test_hash_round_trip() -> None:
    encoded = hash_password("a long enough password")
    assert is_valid_hash(encoded)
    assert verify_password("a long enough password", encoded)
    assert not verify_password("a long enough passworD", encoded)


def test_hashes_are_salted() -> None:
    assert hash_password("a long enough password") != hash_password("a long enough password")


def test_short_password_rejected() -> None:
    with pytest.raises(ValueError, match="at least"):
        hash_password("short")


@pytest.mark.parametrize("bad", ["", "plain-text", "scrypt$1$2$3$!!$!!", "bcrypt$a$b$c$d$e"])
def test_malformed_hash_never_verifies(bad: str) -> None:
    assert not is_valid_hash(bad)
    assert not verify_password("anything at all", bad)
