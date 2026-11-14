from app.security.throttle import LoginThrottle


def test_blocks_after_max_failures_then_recovers() -> None:
    t = LoginThrottle(max_failures=3, window_seconds=100)
    for i in range(3):
        assert t.retry_after("ip", now=i) == 0
        t.record_failure("ip", now=i)
    assert t.retry_after("ip", now=3) == 97
    assert t.retry_after("other-ip", now=3) == 0
    assert t.retry_after("ip", now=101) == 0


def test_reset_clears_failures() -> None:
    t = LoginThrottle(max_failures=1, window_seconds=100)
    t.record_failure("ip", now=0)
    t.reset("ip")
    assert t.retry_after("ip", now=1) == 0
