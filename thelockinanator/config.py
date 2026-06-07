"""Configuration: built-in defaults, JSON load/save, and deep-merge of user
overrides on top of defaults.

The defaults are the single source of truth for tunable knobs. A user config
file only needs to specify the keys it wants to change; everything else falls
back to the defaults via a recursive merge.
"""

from __future__ import annotations

import copy
import json
import os
from typing import Any


def default_config() -> dict[str, Any]:
    """Return a fresh copy of the built-in default configuration."""
    return copy.deepcopy(_DEFAULTS)


def load_config(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Return defaults deep-merged with the user JSON at ``path``.

    A missing file yields the plain defaults.
    """
    merged = default_config()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            user = json.load(fh)
    except FileNotFoundError:
        return merged
    return _deep_merge(merged, user)


def save_config(path: str | os.PathLike[str], data: dict[str, Any]) -> None:
    """Write ``data`` to ``path`` as pretty JSON, creating parent dirs."""
    parent = os.path.dirname(os.fspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def _deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge ``overrides`` into ``base`` in place; return ``base``.

    Nested dicts merge key-by-key; any non-dict value replaces wholesale.
    """
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


_DEFAULTS: dict[str, Any] = {
    "focus_meter": {
        "max_level": 100.0,
        "grace_seconds": 2.0,          # brief glances cost nothing
        "drain_seconds": 10.0,         # full -> empty under sustained distraction
        "drain_exponent": 2.0,         # >1 makes the drain accelerate
        "refill_seconds": 120.0,       # empty -> full under sustained focus
        "reset_level": 50.0,           # meter level after a punishment fires
        "punish_cooldown_seconds": 5.0,
    },
    "session": {
        "break_duration_seconds": 300.0,    # 5-minute break
        "break_interval_seconds": 3600.0,   # one break per rolling hour
        "absence_grace_seconds": 5.0,       # tolerated before absence acts
    },
    "detection": {
        "fps": 12,
        "look_away_yaw_deg": 25.0,
        "look_away_pitch_deg": 20.0,
        "phone_pitch_deg": 18.0,
        "phone_hand_radius": 0.20,   # normalized distance from face center
        "absence_frames": 8,
    },
    "audio": {
        "volume": 1.0,
        "output_override": None,            # None=auto, "headphones", or "speaker"
        "alarm_loops": 3,                   # extra repeats for the headphone alarm
        "alarm_sounds": ["assets/sounds/alarm.wav"],
        "fart_sounds": ["assets/sounds/fart.wav"],
    },
    "hotkeys": {
        "take_break": "ctrl+alt+b",
        "stop": "ctrl+alt+s",
    },
    "ui": {
        "show_preview": False,
        "hide_on_start": True,
    },
}
