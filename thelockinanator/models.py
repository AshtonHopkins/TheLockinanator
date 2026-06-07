"""Download and cache MediaPipe task models on first use.

Models are fetched from Google's public MediaPipe model storage into
``assets/models/`` and reused thereafter. They are deliberately git-ignored so
the repo stays small.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parent / "assets" / "models"

_URLS = {
    "face_landmarker.task": (
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
        "face_landmarker/float16/1/face_landmarker.task"
    ),
    "hand_landmarker.task": (
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
        "hand_landmarker/float16/1/hand_landmarker.task"
    ),
}


def ensure_model(name: str) -> Path:
    """Return the local path to ``name``, downloading it if not yet cached."""
    if name not in _URLS:
        raise KeyError(f"unknown model: {name}")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    path = MODELS_DIR / name
    if not path.exists():
        tmp = path.with_suffix(path.suffix + ".part")
        urllib.request.urlretrieve(_URLS[name], tmp)
        tmp.replace(path)  # atomic: never leave a half-written model behind
    return path
