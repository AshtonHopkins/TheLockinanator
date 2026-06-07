"""Optional OpenCV debug-preview window.

Shows the webcam feed with detection overlays (head pose, hands, status, meter)
so thresholds can be tuned during setup. Off by default. All cv2 window calls
must happen on the capture thread that drives it.
"""

from __future__ import annotations

import numpy as np

from .detectors.analysis import FrameAnalysis

_WINDOW = "Lockinanator Preview"
_GREEN = (90, 210, 90)
_RED = (60, 60, 230)
_WHITE = (245, 245, 245)


class PreviewWindow:
    def __init__(self) -> None:
        import cv2

        self._cv2 = cv2
        self._open = False

    def show(self, frame: np.ndarray, analysis: FrameAnalysis, level: float,
             distracted: bool) -> None:
        cv2 = self._cv2
        img = frame.copy()
        h, w = img.shape[:2]

        color = _RED if distracted else _GREEN
        status = "DISTRACTED" if distracted else "LOCKED IN"
        cv2.putText(img, status, (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

        if analysis.face_present and analysis.yaw is not None:
            cv2.putText(
                img, f"yaw {analysis.yaw:+.0f}  pitch {analysis.pitch:+.0f}",
                (12, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, _WHITE, 1,
            )
        else:
            cv2.putText(img, "no face", (12, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, _RED, 2)

        for hand in analysis.hands:
            for (nx, ny) in hand:
                cv2.circle(img, (int(nx * w), int(ny * h)), 3, (255, 180, 0), -1)

        # Meter bar along the bottom.
        bar_w = int((w - 24) * max(0.0, min(1.0, level / 100.0)))
        cv2.rectangle(img, (12, h - 28), (w - 12, h - 12), (60, 60, 70), -1)
        cv2.rectangle(img, (12, h - 28), (12 + bar_w, h - 12), color, -1)

        cv2.imshow(_WINDOW, img)
        cv2.waitKey(1)
        self._open = True

    def close(self) -> None:
        if self._open:
            try:
                self._cv2.destroyWindow(_WINDOW)
            except Exception:
                pass
            self._open = False
