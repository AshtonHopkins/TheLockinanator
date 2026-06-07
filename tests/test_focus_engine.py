"""Tests for the FocusEngine: it aggregates detector signals into a single
distracted/focused verdict, drives the FocusMeter, and tracks session stats.
"""

import pytest

from thelockinanator.detectors.base import DetectionSignal
from thelockinanator.focus_engine import FocusEngine
from thelockinanator.focus_meter import FocusMeter


def make_engine(**meter_overrides):
    cfg = {
        "max_level": 100.0,
        "grace_seconds": 2.0,
        "drain_seconds": 10.0,
        "drain_exponent": 2.0,
        "refill_seconds": 120.0,
        "reset_level": 50.0,
        "punish_cooldown_seconds": 5.0,
    }
    cfg.update(meter_overrides)
    return FocusEngine(FocusMeter(cfg))


def sig(source, distracted):
    return DetectionSignal(source=source, distracted=distracted)


# --- aggregation ----------------------------------------------------------

def test_no_signals_is_focused():
    result = make_engine().update([], dt=1.0)
    assert result.distracted is False


def test_any_distracted_source_makes_the_tick_distracted():
    result = make_engine().update([sig("look_away", False), sig("phone_use", True)], dt=1.0)
    assert result.distracted is True


def test_all_focused_sources_is_focused():
    result = make_engine().update([sig("look_away", False), sig("phone_use", False)], dt=1.0)
    assert result.distracted is False


def test_active_sources_lists_only_distracting_detectors():
    result = make_engine().update(
        [sig("look_away", True), sig("phone_use", False), sig("absence", True)], dt=1.0
    )
    assert set(result.active_sources) == {"look_away", "absence"}


# --- driving the meter ----------------------------------------------------

def test_sustained_distraction_drives_meter_to_punishment():
    engine = make_engine(grace_seconds=0.0)
    result = engine.update([sig("phone_use", True)], dt=10.0)
    assert result.punished is True
    assert result.level == pytest.approx(50.0)


def test_focus_refills_the_meter():
    engine = make_engine(grace_seconds=0.0)
    engine.update([sig("phone_use", True)], dt=10.0)        # punished -> level 50
    result = engine.update([], dt=30.0)                     # focus refills
    assert result.level == pytest.approx(75.0)


# --- stats ----------------------------------------------------------------

def test_tracks_focus_percentage():
    engine = make_engine()
    engine.update([], dt=30.0)                       # 30s focused
    engine.update([sig("look_away", True)], dt=10.0)  # 10s distracted
    assert engine.stats.focus_pct == pytest.approx(75.0)  # 30 / 40


def test_focus_percentage_is_full_before_any_time_elapses():
    assert make_engine().stats.focus_pct == 100.0


def test_counts_each_distraction_episode_once():
    engine = make_engine()
    engine.update([sig("look_away", True)], dt=1.0)   # episode begins
    engine.update([sig("look_away", True)], dt=1.0)   # same episode continues
    engine.update([], dt=1.0)                          # refocus
    engine.update([sig("phone_use", True)], dt=1.0)    # new episode
    assert engine.stats.distraction_episodes == 2


def test_counts_punishments():
    engine = make_engine(grace_seconds=0.0)
    engine.update([sig("phone_use", True)], dt=10.0)  # punish #1
    engine.update([sig("phone_use", True)], dt=3.0)   # suppressed (cooldown)
    engine.update([sig("phone_use", True)], dt=3.0)   # punish #2 after cooldown
    assert engine.stats.punishments == 2


def test_reset_clears_stats_and_refills_meter():
    engine = make_engine()
    engine.update([sig("look_away", True)], dt=5.0)
    engine.reset()
    assert engine.stats.distraction_episodes == 0
    assert engine.stats.focus_pct == 100.0
    assert engine.update([], dt=0.0).level == 100.0
