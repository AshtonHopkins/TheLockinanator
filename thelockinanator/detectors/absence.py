"""Absence detector: flags when no face is visible in frame."""

from __future__ import annotations

from typing import Any

from .analysis import FrameAnalysis
from .base import DetectionSignal, Detector


class AbsenceDetector(Detector):
    name = "absence"

    def __init__(self, cfg: dict[str, Any]) -> None:
        self._cfg = cfg

    def process(self, analysis: FrameAnalysis) -> DetectionSignal:
        absent = not analysis.face_present
        return DetectionSignal(self.name, absent, "no face" if absent else "")
