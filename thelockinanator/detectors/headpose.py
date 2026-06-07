"""Head-pose helpers: extract (yaw, pitch, roll) from a rotation matrix.

MediaPipe's Face Landmarker can emit a facial transformation matrix; its 3x3
rotation part feeds this function. The decomposition assumes R = Rz @ Ry @ Rx
and maps rotation about Y -> yaw, X -> pitch, Z -> roll, returned in degrees.
"""

from __future__ import annotations

import math

import numpy as np


def rotation_matrix_to_euler_deg(matrix) -> tuple[float, float, float]:
    """Return ``(yaw, pitch, roll)`` in degrees from a 3x3 rotation matrix."""
    r = np.asarray(matrix, dtype=float)
    sy = math.hypot(r[0, 0], r[1, 0])
    if sy > 1e-6:
        pitch = math.atan2(r[2, 1], r[2, 2])   # about X
        yaw = math.atan2(-r[2, 0], sy)         # about Y
        roll = math.atan2(r[1, 0], r[0, 0])    # about Z
    else:  # gimbal lock
        pitch = math.atan2(-r[1, 2], r[1, 1])
        yaw = math.atan2(-r[2, 0], sy)
        roll = 0.0
    return math.degrees(yaw), math.degrees(pitch), math.degrees(roll)
