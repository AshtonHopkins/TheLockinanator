"""Tests for the FocusMeter: accelerating drain, linear refill, grace window,
punishment trigger, reset-to-half, and cooldown.

The meter is driven by explicit ``dt`` values so timing is fully deterministic
without a real clock or camera.
"""

import pytest

from thelockinanator.focus_meter import FocusMeter


def make_meter(**overrides):
    cfg = {
        "max_level": 100.0,
        "grace_seconds": 2.0,
        "drain_seconds": 10.0,     # full -> empty under sustained distraction
        "drain_exponent": 2.0,     # >1 => accelerating drain
        "refill_seconds": 120.0,   # empty -> full under sustained focus
        "reset_level": 50.0,       # level after a punishment fires
        "punish_cooldown_seconds": 5.0,
    }
    cfg.update(overrides)
    return FocusMeter(cfg)


# --- starting state -------------------------------------------------------

def test_starts_full():
    assert make_meter().level == 100.0


# --- grace / dwell tolerance ---------------------------------------------

def test_brief_glance_within_grace_does_not_drain():
    m = make_meter()
    result = m.update(distracted=True, dt=1.5)  # under the 2.0s grace
    assert result.level == 100.0
    assert result.punished is False


def test_glances_reset_grace_between_them():
    m = make_meter()
    m.update(distracted=True, dt=1.5)    # glance 1 (within grace)
    m.update(distracted=False, dt=0.1)   # refocus resets the grace window
    result = m.update(distracted=True, dt=1.5)  # glance 2 (within fresh grace)
    assert result.level == 100.0


# --- drain ----------------------------------------------------------------

def test_sustained_distraction_empties_after_drain_window():
    m = make_meter()
    m.update(distracted=True, dt=2.0)            # consume grace, no drain yet
    result = m.update(distracted=True, dt=10.0)  # the full drain window bottoms it out
    # Bottoming out fires the punishment and resets to the reset level in the
    # same tick, so the reported level is the reset level (not 0).
    assert result.punished is True
    assert result.level == pytest.approx(50.0)


def test_drain_accelerates_so_first_half_removes_less_than_half():
    m = make_meter()
    m.update(distracted=True, dt=2.0)           # grace
    result = m.update(distracted=True, dt=5.0)  # half the drain window
    # Accelerating (exp=2): level = 100 * (1 - (5/10)^2) = 75, not 50.
    assert result.level == pytest.approx(75.0)
    assert result.punished is False


def test_partial_meter_empties_faster_than_linear():
    m = make_meter(grace_seconds=0.0)
    first = m.update(distracted=True, dt=10.0)   # bottom out -> resets to 50
    assert first.punished is True
    assert m.level == pytest.approx(50.0)
    # From 50, the accelerating curve empties in ~2.93s, well under the 5s a
    # linear half-meter would need. 3s of distraction bottoms it out.
    result = m.update(distracted=True, dt=3.0)
    assert result.level == 0.0


# --- refill ---------------------------------------------------------------

def test_refill_is_linear():
    m = make_meter(grace_seconds=0.0)
    m.update(distracted=True, dt=10.0)              # punished -> level 50
    result = m.update(distracted=False, dt=30.0)    # 30s of focus
    # rate = 100/120 per second -> +25 over 30s
    assert result.level == pytest.approx(75.0)


def test_refill_caps_at_full():
    m = make_meter(grace_seconds=0.0)
    m.update(distracted=True, dt=10.0)              # -> 50
    result = m.update(distracted=False, dt=600.0)   # far more than needed
    assert result.level == 100.0


# --- punishment, reset, cooldown -----------------------------------------

def test_punishment_resets_to_reset_level():
    m = make_meter(grace_seconds=0.0)
    result = m.update(distracted=True, dt=10.0)
    assert result.punished is True
    assert m.level == pytest.approx(50.0)


def test_cooldown_suppresses_immediate_second_punishment():
    m = make_meter(grace_seconds=0.0)
    m.update(distracted=True, dt=10.0)            # punish #1 -> 50, cooldown 5s
    result = m.update(distracted=True, dt=3.0)    # empties again but within cooldown
    assert result.level == 0.0
    assert result.punished is False


def test_punishment_fires_again_after_cooldown_elapses():
    m = make_meter(grace_seconds=0.0)
    m.update(distracted=True, dt=10.0)            # punish #1, cooldown 5s
    m.update(distracted=True, dt=3.0)             # level 0, cooldown -> 2, suppressed
    result = m.update(distracted=True, dt=3.0)    # cooldown -> 0 then empty -> punish #2
    assert result.punished is True
    assert m.level == pytest.approx(50.0)


# --- misc -----------------------------------------------------------------

def test_reset_restores_full():
    m = make_meter()
    m.update(distracted=True, dt=2.0)
    m.update(distracted=True, dt=4.0)   # drained below full
    assert m.level < 100.0
    m.reset()
    assert m.level == 100.0


def test_level_never_exceeds_max_or_drops_below_zero():
    m = make_meter(grace_seconds=0.0)
    over = m.update(distracted=False, dt=10_000.0)
    assert over.level == 100.0
    under = m.update(distracted=True, dt=10_000.0)
    assert under.level >= 0.0


def test_negative_dt_is_rejected():
    with pytest.raises(ValueError):
        make_meter().update(distracted=False, dt=-1.0)
