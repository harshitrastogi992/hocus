from __future__ import annotations


class HoldTimer:
    """Tracks how long a gesture has been held.

    Short detection dropouts up to ``grace`` seconds do not reset the count. After a
    completed hold, or after ``disarm()``, the gesture must be released before it can
    count again, so a pose still held when an effect ends cannot retrigger it.
    """

    def __init__(self, seconds: float, grace: float = 0.15) -> None:
        self.seconds = seconds
        self.grace = grace
        self.armed = True
        self.started: float | None = None
        self.last_seen = float("-inf")

    def disarm(self) -> None:
        self.armed = False
        self.started = None

    def update(self, active: bool, now: float) -> float | None:
        """Return hold progress in (0, 1], 1.0 exactly once per completed hold, else None."""
        if active:
            self.last_seen = now
        elif now - self.last_seen > self.grace:
            self.armed = True
            self.started = None
            return None
        elif self.started is None:
            return None
        if not self.armed:
            return None
        if self.started is None:
            self.started = now
        progress = (now - self.started) / self.seconds if self.seconds > 0 else 1.0
        if progress >= 1.0:
            self.disarm()
            return 1.0
        return max(progress, 1e-3)
