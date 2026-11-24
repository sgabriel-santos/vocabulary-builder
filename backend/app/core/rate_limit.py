"""Rate limiter em memória por chave (janela deslizante).

Suficiente para um único processo da API (single-user, um container).
"""

import time
from collections import deque
from collections.abc import Callable


class InMemoryRateLimiter:
    def __init__(
        self,
        limit: int,
        window_seconds: int,
        time_func: Callable[[], float] = time.monotonic,
    ) -> None:
        self._limit = limit
        self._window = window_seconds
        self._time = time_func
        self._hits: dict[str, deque[float]] = {}

    def hit(self, key: str) -> bool:
        """Registra uma tentativa; retorna False se o limite da janela já foi atingido."""
        now = self._time()
        hits = self._hits.setdefault(key, deque())
        while hits and hits[0] <= now - self._window:
            hits.popleft()
        if len(hits) >= self._limit:
            return False
        hits.append(now)
        return True
