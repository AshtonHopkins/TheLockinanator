"""Phone-use detector (heuristic).

Without a dedicated object detector, phone use is inferred from posture: a hand
is visible AND either the head is tilted down (looking at a phone in hand) or a
hand is raised close to the face (phone to face). Noisy by nature - tunable via
config and intended as a "good enough" MVP signal.
"""

from __future__ import annotations

import math
from typing import Any

from .analysis import FrameAnalysis, Hand
from .base import DetectionSignal, Detector


def hand_near_point(hand: Hand, point: tuple[float, float], radius: float) -> bool:
    """True if any landmark of ``hand`` is within ``radius`` of ``point``."""
    px, py = point
    return any(math.hypot(x - px, y - py) <= radius for (x, y) in hand)


class PhoneUseDetector(Detector):
    name = "phone_use"

    def __init__(self, cfg: dict[str, Any]) -> None:
        self._pitch_deg = float(cfg["phone_pitch_deg"])
        self._radius = float(cfg.get("phone_hand_radius", 0.20))

    def process(self, analysis: FrameAnalysis) -> DetectionSignal:
        if not analysis.hands:
            return DetectionSignal(self.name, False)

        looking_down = analysis.pitch is not None and analysis.pitch > self._pitch_deg
        near_face = analysis.face_center is not None and any(
            hand_near_point(hand, analysis.face_center, self._radius)
            for hand in analysis.hands
        )

        if looking_down:
            return DetectionSignal(self.name, True, "phone in hand")
        if near_face:
            return DetectionSignal(self.name, True, "phone to face")
        return DetectionSignal(self.name, False)
