"""Thin webcam wrapper around OpenCV's VideoCapture.

Kept behind a tiny interface (read / release / opened) so the orchestrator can
be driven by a fake frame source in tests.
"""

from __future__ import annotations

import numpy as np


class WebcamCapture:
    def __init__(self, index: int = 0) -> None:
        import cv2

        self._cv2 = cv2
        self._cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)

    def opened(self) -> bool:
        return bool(self._cap.isOpened())

    def read(self) -> np.ndarray | None:
        ok, frame = self._cap.read()
        return frame if ok else None

    def release(self) -> None:
        try:
            self._cap.release()
        except Exception:
            pass
