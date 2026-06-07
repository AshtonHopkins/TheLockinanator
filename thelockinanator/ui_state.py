"""The immutable snapshot the GUI renders each tick.

The orchestrator computes a ``UiState`` from the engine/session/meter under a
lock; the GUI only ever reads one. Keeping it a plain dataclass (no logic, no
references back into live objects) means the window never touches engine
internals from the main thread.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class UiState:
    running: bool = False
    on_break: bool = False
    level: float = 100.0           # focus meter, 0..max_level
    max_level: float = 100.0
    elapsed_seconds: float = 0.0
    break_remaining: float = 0.0   # seconds left on an active break
    next_break_in: float = 0.0     # seconds until a break unlocks
    break_available: bool = False
    focus_pct: float = 100.0
    distraction_episodes: int = 0
    punishments: int = 0
    active_sources: tuple[str, ...] = field(default_factory=tuple)
    status_text: str = "Idle"
