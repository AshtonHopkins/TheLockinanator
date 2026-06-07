"""Device-aware audio punishment: blast an alarm into headphones, or play fart
sounds out of a speaker. The output kind and the sound files are configurable.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any, Callable

from .base import Punishment

_PKG = Path(__file__).resolve().parent.parent  # thelockinanator/


def _resolve(path: str) -> str:
    p = Path(path)
    return str(p if p.is_absolute() else _PKG / path)


class AudioAlarmPunishment(Punishment):
    name = "audio_alarm"

    def __init__(
        self,
        cfg: dict[str, Any],
        player: Any,
        kind_resolver: Callable[[], str],
    ) -> None:
        self._cfg = cfg
        self._player = player
        self._resolve_kind = kind_resolver

    def is_available(self) -> bool:
        return bool(self._cfg.get("alarm_sounds") or self._cfg.get("fart_sounds"))

    def execute(self) -> None:
        kind = self._resolve_kind()
        if kind == "headphones":
            sounds = self._cfg.get("alarm_sounds") or []
            loops = int(self._cfg.get("alarm_loops", 0))
        else:
            sounds = self._cfg.get("fart_sounds") or []
            loops = 0
        if not sounds:
            return
        path = _resolve(random.choice(sounds))
        self._player.play(path, volume=float(self._cfg.get("volume", 1.0)), loops=loops)
