"""Detector plugin interface and the signal type detectors emit.

A ``Detector`` reads a pre-computed :class:`FrameAnalysis` and reports whether it
currently sees a distraction. The orchestrator runs the vision pipeline once per
frame, then hands the analysis to every enabled detector and the resulting
signals to the ``FocusEngine``. New detectors (app/website monitoring, etc.) only
need to implement this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from .analysis import FrameAnalysis


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
    def process(self, analysis: FrameAnalysis) -> DetectionSignal:
        """Inspect the frame analysis and return this detector's verdict."""
        raise NotImplementedError

    def close(self) -> None:
        """Release any underlying resources (models, etc.). Optional."""
