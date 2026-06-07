"""Audio playback abstraction.

The :class:`AudioPlayer` protocol lets punishments be tested with a fake; the
pygame-backed implementation is the real thing. Initialization is lazy and
defensive so a machine with no audio device doesn't crash the app.
"""

from __future__ import annotations

from typing import Protocol


class AudioPlayer(Protocol):
    def play(self, path: str, volume: float = 1.0, loops: int = 0) -> None: ...
    def stop(self) -> None: ...


class PygameAudioPlayer:
    """Plays sounds via pygame's mixer. ``loops`` is *extra* repeats after the
    first play (pygame's convention)."""

    def __init__(self) -> None:
        import pygame

        self._pygame = pygame
        self._ok = False
        try:
            pygame.mixer.init()
            self._ok = True
        except Exception:
            self._ok = False

    def play(self, path: str, volume: float = 1.0, loops: int = 0) -> None:
        if not self._ok:
            return
        try:
            sound = self._pygame.mixer.Sound(path)
            sound.set_volume(max(0.0, min(1.0, volume)))
            sound.play(loops=loops)
        except Exception:
            pass

    def stop(self) -> None:
        if self._ok:
            try:
                self._pygame.mixer.stop()
            except Exception:
                pass
