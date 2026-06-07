"""Detector plugin interface and the signal type detectors emit.

A ``Detector`` looks at a single webcam frame and reports whether it currently
sees a distraction. The orchestrator runs every enabled detector each frame and
hands the resulting signals to the ``FocusEngine``. New detectors (app/website
monitoring, etc.) only need to implement this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DetectionSignal:
    """One detector's verdict for one frame."""

    source: str           # detector name, e.g. "look_away"
    distracted: bool      # True if this detector currently flags distraction
    detail: str = ""      # optional human-readable note for preview/toast


class Detector(ABC):
    """Base class for all distraction detectors."""

    #: Short stable identifier used in signals, stats, and the preview overlay.
    name: str = "detector"

    @abstractmethod
    def process(self, frame: Any) -> DetectionSignal:
        """Inspect ``frame`` (a webcam image) and return this detector's verdict."""
        raise NotImplementedError

    def close(self) -> None:
        """Release any underlying resources (models, etc.). Optional."""
