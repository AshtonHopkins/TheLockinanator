"""The per-frame vision result that detectors consume.

``FrameAnalysis`` is a plain, MediaPipe-free dataclass: the vision pipeline runs
the heavy models once per frame and fills one of these, and every detector is a
pure function of it. That keeps detectors trivially unit-testable with synthetic
analyses and keeps the engine import chain free of MediaPipe.

All coordinates are normalized to ``[0, 1]`` (fraction of frame width/height).
Head angles are in degrees with the convention: yaw +right, pitch +down,
roll +clockwise. Any angle may be ``None`` when no face is detected.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# A hand is a tuple of (x, y) normalized landmark points.
Hand = tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class FrameAnalysis:
    frame_w: int
    frame_h: int
    face_present: bool
    yaw: float | None = None
    pitch: float | None = None
    roll: float | None = None
    face_center: tuple[float, float] | None = None
    hands: tuple[Hand, ...] = field(default_factory=tuple)
