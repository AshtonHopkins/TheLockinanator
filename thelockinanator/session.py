"""Session and break management.

Owns the lifecycle of a focus session (start/stop, elapsed time) and the break
rules: a fixed-length break that becomes available once per rolling interval.
The same ``take_break`` entry point serves both a manual break (tray click) and
an auto-burned break (sustained absence) — only the trigger differs.

State is derived from an injected :class:`~thelockinanator.clock.Clock` on each
access, so there is no internal timer to tick and tests stay deterministic.
"""

from __future__ import annotations

from typing import Any

from .clock import Clock


class SessionManager:
    def __init__(self, cfg: dict[str, Any], clock: Clock) -> None:
        self._break_duration = float(cfg["break_duration_seconds"])
        self._break_interval = float(cfg["break_interval_seconds"])
        self._clock = clock

        self._running = False
        self._start_time = 0.0
        self._stop_time = 0.0
        # Breaks are measured from the later of session start or the last break.
        self._last_break_marker = 0.0
        self._break_start: float | None = None

    # --- lifecycle --------------------------------------------------------

    def start(self) -> None:
        now = self._clock.now()
        self._running = True
        self._start_time = now
        self._last_break_marker = now
        self._break_start = None

    def stop(self) -> None:
        self._stop_time = self._clock.now()
        self._running = False
        self._break_start = None

    @property
    def running(self) -> bool:
        return self._running

    @property
    def elapsed_seconds(self) -> float:
        if self._running:
            return self._clock.now() - self._start_time
        if self._stop_time:
            return self._stop_time - self._start_time
        return 0.0

    # --- breaks -----------------------------------------------------------

    @property
    def on_break(self) -> bool:
        if not self._running or self._break_start is None:
            return False
        return self._clock.now() < self._break_start + self._break_duration

    def break_seconds_remaining(self) -> float:
        if not self.on_break:
            return 0.0
        assert self._break_start is not None
        end = self._break_start + self._break_duration
        return max(0.0, end - self._clock.now())

    def seconds_until_break_available(self) -> float:
        return max(0.0, self._last_break_marker + self._break_interval - self._clock.now())

    def is_break_available(self) -> bool:
        if not self._running or self.on_break:
            return False
        return self.seconds_until_break_available() <= 0.0

    def take_break(self) -> bool:
        """Start a break if one is available. Returns whether it started."""
        if not self.is_break_available():
            return False
        now = self._clock.now()
        self._break_start = now
        self._last_break_marker = now
        return True
