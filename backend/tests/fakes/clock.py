from datetime import datetime, timedelta


class FakeClock:
    """Relógio controlado pelo teste."""

    def __init__(self, start: datetime) -> None:
        if start.tzinfo is None:
            raise ValueError("FakeClock exige datetime timezone-aware")
        self._now = start

    def now(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> None:
        self._now += delta
