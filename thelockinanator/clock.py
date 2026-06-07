"""Injectable time source.

Time-based logic (the focus meter, session/break timers) takes a ``Clock`` so it
can be driven deterministically from tests with ``FakeClock`` instead of real
wall-clock sleeps.
"""

from __future__ import annotations

import time
from typing import Protocol


class Clock(Protocol):
    """A monotonic seconds source."""

    def now(self) -> float:
        """Return a monotonically increasing time in seconds."""
        ...


class RealClock:
    """Production clock backed by ``time.monotonic``."""

    def now(self) -> float:
        return time.monotonic()


class FakeClock:
    """Test clock whose time only moves when ``advance`` is called."""

    def __init__(self, start: float = 0.0) -> None:
        self._t = float(start)

    def now(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("cannot advance time backwards")
        self._t += float(seconds)
