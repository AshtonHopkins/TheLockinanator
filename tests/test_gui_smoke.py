"""GUI smoke test: the window builds, the art collage places (with the kitten as
a placeholder until Kitten.png exists), and update() renders several states
without error. Skipped automatically where no Tk display is available.

Also covers the two pure helpers in the GUI layer (colour ramp, time format).
"""

import tkinter

import pytest

from thelockinanator.gui.main_window import MainWindow, _fmt_hms
from thelockinanator.gui.meter_widget import level_color
from thelockinanator.ui_state import UiState


def test_fmt_hms_formats_minutes_and_hours():
    assert _fmt_hms(0) == "0:00"
    assert _fmt_hms(65) == "1:05"
    assert _fmt_hms(3661) == "1:01:01"
    assert _fmt_hms(-5) == "0:00"   # clamps


def test_level_color_ramps_red_yellow_green():
    assert level_color(1.0) == "#3cc85a"   # full -> green
    assert level_color(0.5) == "#f0c828"   # half -> yellow
    assert level_color(0.0) == "#dc3c32"   # empty -> red


def test_window_builds_places_art_and_renders_states():
    try:
        win = MainWindow(state_provider=lambda: UiState(), start_hidden=True)
    except tkinter.TclError as exc:
        pytest.skip(f"Tk unavailable in this environment: {exc}")
    try:
        keys = [a.piece.key for a in win._art_refs]
        assert keys == ["eagle", "mushroom", "monster", "tank", "kitten"]
        # All art files are present now, so nothing should render as a placeholder.
        assert [a.piece.key for a in win._art_refs if a.is_placeholder] == []

        win.update(UiState(running=True, level=80.0, focus_pct=80.0))
        win.update(UiState(running=True, level=10.0, active_sources=("phone_use",), focus_pct=30.0))
        win.update(UiState(on_break=True, break_remaining=120.0))
        win.root.update()  # flush one round of Tk events
    finally:
        win.root.destroy()
