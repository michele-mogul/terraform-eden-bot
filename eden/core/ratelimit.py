"""Per-user cooldown, so one member cannot flood the group."""

import time


class Cooldown:
    def __init__(self, seconds: float, clock=time.monotonic) -> None:
        self.seconds = seconds
        self.clock = clock
        self._last: dict[tuple[int, int], float] = {}

    def hit(self, chat_id: int, user_id: int) -> float:
        """0 when the user may run a command now (and records it), else the seconds left."""
        now = self.clock()
        key = (chat_id, user_id)
        left = self.seconds - (now - self._last.get(key, float("-inf")))
        if left > 0:
            return left
        self._last[key] = now
        return 0.0
