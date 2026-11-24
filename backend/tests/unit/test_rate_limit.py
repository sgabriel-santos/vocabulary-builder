from app.core.rate_limit import InMemoryRateLimiter


class _FakeTime:
    def __init__(self) -> None:
        self.value = 1000.0

    def __call__(self) -> float:
        return self.value


def test_rate_limiter_blocks_after_limit() -> None:
    limiter = InMemoryRateLimiter(3, 60, time_func=_FakeTime())

    assert [limiter.hit("1.2.3.4") for _ in range(4)] == [True, True, True, False]
    # Chaves são independentes.
    assert limiter.hit("5.6.7.8")


def test_rate_limiter_releases_after_window() -> None:
    fake_time = _FakeTime()
    limiter = InMemoryRateLimiter(2, 60, time_func=fake_time)
    limiter.hit("ip")
    limiter.hit("ip")
    assert not limiter.hit("ip")

    fake_time.value += 59.9
    assert not limiter.hit("ip")

    fake_time.value += 0.1
    assert limiter.hit("ip")
