from app.security import tokens

SECRET = "s" * 40


def test_issue_and_verify() -> None:
    token, session = tokens.issue(SECRET, ttl_seconds=60, now=1_000)
    assert session.expires_at == 1_060
    assert tokens.verify(token, SECRET, now=1_030) == session


def test_expired_token_is_rejected() -> None:
    token, _ = tokens.issue(SECRET, ttl_seconds=60, now=1_000)
    assert tokens.verify(token, SECRET, now=1_060) is None


def test_other_secret_is_rejected() -> None:
    token, _ = tokens.issue(SECRET, ttl_seconds=60, now=1_000)
    assert tokens.verify(token, "t" * 40, now=1_001) is None


def test_tampered_payload_is_rejected() -> None:
    token, _ = tokens.issue(SECRET, ttl_seconds=60, now=1_000)
    _, signature = token.split(".")
    forged_payload, _ = tokens.issue(SECRET, ttl_seconds=10**9, now=1_000)
    assert tokens.verify(f"{forged_payload.split('.')[0]}.{signature}", SECRET, now=1_001) is None


def test_garbage_is_rejected() -> None:
    for junk in ["", "abc", "a.b", "a.b.c", "!!!.???"]:
        assert tokens.verify(junk, SECRET) is None
