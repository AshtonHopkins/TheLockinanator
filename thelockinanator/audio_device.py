"""Best-effort detection of whether the default audio output is headphones or a
speaker, so the punishment can blast an alarm into headphones but play fart
sounds out loud. Always overridable via config, since form-factor detection on
Windows is imperfect.
"""

from __future__ import annotations

from typing import Callable, Literal

OutputKind = Literal["headphones", "speaker"]

_HEADPHONE_HINTS = ("headphone", "headset", "earphone", "earbud", "airpod", "buds")


def detect_output_kind() -> OutputKind:
    """Guess the default render device kind from its name (Windows / pycaw)."""
    try:
        from pycaw.pycaw import AudioUtilities

        device = AudioUtilities.GetSpeakers()
        name = ""
        try:
            name = (device.FriendlyName or "").lower()  # type: ignore[attr-defined]
        except Exception:
            name = ""
        if any(hint in name for hint in _HEADPHONE_HINTS):
            return "headphones"
        return "speaker"
    except Exception:
        return "speaker"


def resolve_output_kind(
    override: str | None,
    detector: Callable[[], OutputKind] = detect_output_kind,
) -> OutputKind:
    """Use a valid config override if given, otherwise fall back to detection."""
    if override in ("headphones", "speaker"):
        return override  # type: ignore[return-value]
    return detector()
