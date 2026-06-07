"""Look-away detector: flags when the head is turned or tilted away from the
screen, based on yaw/pitch from head pose. Defers the no-face case to the
absence detector so a single distraction isn't double-counted.
"""

from __future__ import annotations

from typing import Any

from .analysis import FrameAnalysis
from .base import DetectionSignal, Detector


class LookAwayDetector(Detector):
    name = "look_away"

    def __init__(self, cfg: dict[str, Any]) -> None:
        self._yaw_deg = float(cfg["look_away_yaw_deg"])
        self._pitch_deg = float(cfg["look_away_pitch_deg"])

    def process(self, analysis: FrameAnalysis) -> DetectionSignal:
        if not analysis.face_present or analysis.yaw is None or analysis.pitch is None:
            return DetectionSignal(self.name, False)
        if abs(analysis.yaw) > self._yaw_deg:
            return DetectionSignal(self.name, True, "turned away")
        if analysis.pitch > self._pitch_deg:
            return DetectionSignal(self.name, True, "looking down")
        return DetectionSignal(self.name, False)
