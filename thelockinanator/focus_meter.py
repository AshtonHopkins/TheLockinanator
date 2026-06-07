"""The focus meter: the core scoring mechanic.

Behavior (all knobs come from the ``focus_meter`` config section):

* Level lives in ``[0, max_level]`` and starts full.
* Looking away / using a phone is "distraction". A short **grace** window means
  brief glances cost nothing; the grace timer resets the moment you refocus.
* Past grace, the meter **drains** on an accelerating curve calibrated so a full
  meter empties after ``drain_seconds`` of continuous distraction. Because the
  curve is accelerating, a partially-full meter empties proportionally faster.
* While focused, the meter **refills** linearly, full after ``refill_seconds``.
* Hitting zero fires a **punishment**, after which the meter resets to
  ``reset_level`` and a **cooldown** suppresses further punishments briefly.

The meter is advanced by explicit ``dt`` (seconds since the last tick), which
keeps it a pure state machine — no clock, no I/O — and trivially testable. The
caller simply skips ticks while a break is active to "freeze" it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MeterUpdate:
    """Outcome of a single tick."""

    level: float
    punished: bool


class FocusMeter:
    def __init__(self, cfg: dict[str, Any]) -> None:
        self._max = float(cfg["max_level"])
        self._grace = float(cfg["grace_seconds"])
        self._drain_seconds = float(cfg["drain_seconds"])
        self._exponent = float(cfg["drain_exponent"])
        self._refill_seconds = float(cfg["refill_seconds"])
        self._reset_level = float(cfg["reset_level"])
        self._cooldown_seconds = float(cfg["punish_cooldown_seconds"])
        self.reset()

    @property
    def level(self) -> float:
        return self._level

    def reset(self) -> None:
        """Restore a full meter and clear all timers (e.g. at session start)."""
        self._level = self._max
        self._distraction_time = 0.0
        self._cooldown_remaining = 0.0

    def update(self, distracted: bool, dt: float) -> MeterUpdate:
        if dt < 0:
            raise ValueError("dt cannot be negative")

        if self._cooldown_remaining > 0:
            self._cooldown_remaining = max(0.0, self._cooldown_remaining - dt)

        punished = False
        if distracted:
            self._distraction_time += dt
            over_grace = self._distraction_time - self._grace
            if over_grace > 0:
                # Only the portion of this tick that lies past grace drains.
                self._drain(min(dt, over_grace))
                if self._level <= 0.0:
                    self._level = 0.0
                    if self._cooldown_remaining <= 0.0:
                        punished = True
                        self._level = self._reset_level
                        self._cooldown_remaining = self._cooldown_seconds
        else:
            self._distraction_time = 0.0
            self._refill(dt)

        return MeterUpdate(level=self._level, punished=punished)

    # --- internals --------------------------------------------------------

    def _drain(self, seconds: float) -> None:
        """Advance along the accelerating drain curve by ``seconds``.

        The curve is ``level = max * (1 - (u/T)^p)`` where ``u`` is elapsed
        drain time and ``T = drain_seconds``. We invert the current level to its
        position ``u`` on the curve, step forward, and recompute — so a
        partially-drained meter continues from where it already is.
        """
        drained_fraction = max(0.0, 1.0 - self._level / self._max)
        u = self._drain_seconds * (drained_fraction ** (1.0 / self._exponent))
        u += seconds
        self._level = self._max * (1.0 - (u / self._drain_seconds) ** self._exponent)
        self._level = max(0.0, min(self._max, self._level))

    def _refill(self, seconds: float) -> None:
        rate = self._max / self._refill_seconds
        self._level = min(self._max, self._level + rate * seconds)
