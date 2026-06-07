"""The focus-meter bar, drawn directly on a Tk canvas.

A horizontal bar whose fill width tracks the meter level and whose colour shifts
green -> yellow -> red as focus drains. Kept as canvas items (not a separate
widget) so the silly background art can sit behind it.
"""

from __future__ import annotations

import tkinter as tk


def _lerp(a: int, b: int, t: float) -> int:
    return int(round(a + (b - a) * t))


def level_color(fraction: float) -> str:
    """Green (full) -> yellow (half) -> red (empty) as a #rrggbb string."""
    fraction = max(0.0, min(1.0, fraction))
    green = (60, 200, 90)
    yellow = (240, 200, 40)
    red = (220, 60, 50)
    if fraction >= 0.5:
        t = (fraction - 0.5) / 0.5
        lo, hi = yellow, green
    else:
        t = fraction / 0.5
        lo, hi = red, yellow
    r = _lerp(lo[0], hi[0], t)
    g = _lerp(lo[1], hi[1], t)
    b = _lerp(lo[2], hi[2], t)
    return f"#{r:02x}{g:02x}{b:02x}"


class MeterWidget:
    def __init__(self, canvas: tk.Canvas, x: int, y: int, width: int, height: int) -> None:
        self._canvas = canvas
        self._x, self._y = x, y
        self._w, self._h = width, height

        self._track = canvas.create_rectangle(
            x, y, x + width, y + height, fill="#1e1e24", outline="#000000", width=3,
        )
        self._fill = canvas.create_rectangle(
            x + 3, y + 3, x + 3, y + height - 3, fill=level_color(1.0), width=0,
        )
        self._label = canvas.create_text(
            x + width // 2, y + height // 2,
            text="100%", fill="#ffffff",
            font=("Consolas", max(12, height // 3), "bold"),
        )

    def set_level(self, level: float, max_level: float) -> None:
        fraction = 0.0 if max_level <= 0 else max(0.0, min(1.0, level / max_level))
        inner_w = self._w - 6
        self._canvas.coords(
            self._fill,
            self._x + 3, self._y + 3,
            self._x + 3 + inner_w * fraction, self._y + self._h - 3,
        )
        self._canvas.itemconfigure(self._fill, fill=level_color(fraction))
        self._canvas.itemconfigure(self._label, text=f"{level:.0f}%")
        # Keep the label readable on top of the fill.
        self._canvas.tag_raise(self._label)
