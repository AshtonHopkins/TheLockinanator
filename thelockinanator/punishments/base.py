"""Punishment plugin interface and a manager that dispatches one when the focus
meter bottoms out. New punishments (embarrassing messages, etc.) only implement
``Punishment`` and get added to the manager's list.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable


class Punishment(ABC):
    name: str = "punishment"

    def is_available(self) -> bool:
        """Whether this punishment can run right now (e.g. its sounds exist)."""
        return True

    @abstractmethod
    def execute(self) -> None:
        raise NotImplementedError


class PunishmentManager:
    def __init__(self, punishments: Iterable[Punishment]) -> None:
        self._punishments = list(punishments)

    def trigger(self) -> str | None:
        """Run the first available punishment; return its name, or None."""
        for punishment in self._punishments:
            if punishment.is_available():
                punishment.execute()
                return punishment.name
        return None
