"""The focus engine: aggregates per-frame detector signals into one
distracted/focused verdict, advances the :class:`FocusMeter`, and accumulates
the session statistics shown in the UI and saved at the end of a session.

Kept free of any camera or audio I/O so it can be driven entirely from tests
with hand-made signals and explicit ``dt`` values.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .detectors.base import DetectionSignal
from .focus_meter import FocusMeter


@dataclass(frozen=True)
class EngineUpdate:
    """Outcome of one engine tick."""

    level: float
    distracted: bool
    punished: bool
    active_sources: tuple[str, ...]


@dataclass(frozen=True)
class SessionStats:
    focused_seconds: float
    distracted_seconds: float
    distraction_episodes: int
    punishments: int

    @property
    def focus_pct(self) -> float:
        total = self.focused_seconds + self.distracted_seconds
        if total <= 0:
            return 100.0
        return 100.0 * self.focused_seconds / total


class FocusEngine:
    def __init__(self, meter: FocusMeter) -> None:
        self._meter = meter
        self.reset()

    @property
    def level(self) -> float:
        return self._meter.level

    @property
    def stats(self) -> SessionStats:
        return SessionStats(
            focused_seconds=self._focused_seconds,
            distracted_seconds=self._distracted_seconds,
            distraction_episodes=self._distraction_episodes,
            punishments=self._punishments,
        )

    def reset(self) -> None:
        """Start a fresh session: clear stats and refill the meter."""
        self._meter.reset()
        self._focused_seconds = 0.0
        self._distracted_seconds = 0.0
        self._distraction_episodes = 0
        self._punishments = 0
        self._was_distracted = False

    def update(self, signals: Iterable[DetectionSignal], dt: float) -> EngineUpdate:
        active = tuple(s.source for s in signals if s.distracted)
        distracted = len(active) > 0

        # Count a new episode only on the transition into distraction.
        if distracted and not self._was_distracted:
            self._distraction_episodes += 1
        self._was_distracted = distracted

        if distracted:
            self._distracted_seconds += dt
        else:
            self._focused_seconds += dt

        meter_result = self._meter.update(distracted=distracted, dt=dt)
        if meter_result.punished:
            self._punishments += 1

        return EngineUpdate(
            level=meter_result.level,
            distracted=distracted,
            punished=meter_result.punished,
            active_sources=active,
        )
