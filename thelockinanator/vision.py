"""MediaPipe vision pipeline: runs Face + Hand landmarkers on a frame and
distills the result into a pure :class:`FrameAnalysis` the detectors consume.

This is the one place that touches MediaPipe and OpenCV; everything downstream
works off the plain analysis dataclass.
"""

from __future__ import annotations

from typing import Any

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python import vision as mp_vision

from . import models
from .detectors.analysis import FrameAnalysis
from .detectors.headpose import rotation_matrix_to_euler_deg


class VisionPipeline:
    def __init__(self, cfg: dict[str, Any] | None = None) -> None:
        face_model = models.ensure_model("face_landmarker.task")
        hand_model = models.ensure_model("hand_landmarker.task")

        self._face = mp_vision.FaceLandmarker.create_from_options(
            mp_vision.FaceLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=str(face_model)),
                running_mode=mp_vision.RunningMode.IMAGE,
                num_faces=1,
                output_facial_transformation_matrixes=True,
            )
        )
        self._hand = mp_vision.HandLandmarker.create_from_options(
            mp_vision.HandLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=str(hand_model)),
                running_mode=mp_vision.RunningMode.IMAGE,
                num_hands=2,
            )
        )

    def analyze(self, frame_bgr: np.ndarray) -> FrameAnalysis:
        h, w = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        face_res = self._face.detect(image)
        hand_res = self._hand.detect(image)

        face_present = bool(face_res.face_landmarks)
        yaw = pitch = roll = None
        face_center = None
        if face_present:
            matrixes = getattr(face_res, "facial_transformation_matrixes", None)
            if matrixes:
                mat = np.asarray(matrixes[0], dtype=float).reshape(4, 4)
                yaw, pitch, roll = rotation_matrix_to_euler_deg(mat[:3, :3])
            landmarks = face_res.face_landmarks[0]
            face_center = (
                sum(p.x for p in landmarks) / len(landmarks),
                sum(p.y for p in landmarks) / len(landmarks),
            )

        hands = tuple(
            tuple((p.x, p.y) for p in hand)
            for hand in (hand_res.hand_landmarks or [])
        )

        return FrameAnalysis(
            frame_w=w, frame_h=h, face_present=face_present,
            yaw=yaw, pitch=pitch, roll=roll,
            face_center=face_center, hands=hands,
        )

    def close(self) -> None:
        self._face.close()
        self._hand.close()
