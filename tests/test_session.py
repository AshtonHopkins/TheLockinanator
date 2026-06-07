"""Tests for SessionManager: start/stop, elapsed time, break availability
(one per rolling hour), the 5-minute break freeze, and auto-burn on absence.

Driven by FakeClock so all timing is deterministic.
"""

from thelockinanator.clock import FakeClock
from thelockinanator.session import SessionManager


def make_session(**overrides):
    cfg = {
        "break_duration_seconds": 300.0,    # 5 minutes
        "break_interval_seconds": 3600.0,   # one break per hour
        "absence_grace_seconds": 5.0,
    }
    cfg.update(overrides)
    clock = FakeClock(start=1000.0)
    return SessionManager(cfg, clock), clock


# --- start / stop / elapsed ----------------------------------------------

def test_starts_not_running():
    session, _ = make_session()
    assert session.running is False


def test_start_marks_running():
    session, _ = make_session()
    session.start()
    assert session.running is True


def test_elapsed_tracks_clock_while_running():
    session, clock = make_session()
    session.start()
    clock.advance(42.0)
    assert session.elapsed_seconds == 42.0


def test_stop_freezes_elapsed_and_clears_running():
    session, clock = make_session()
    session.start()
    clock.advance(100.0)
    session.stop()
    clock.advance(50.0)              # time passes after stopping
    assert session.running is False
    assert session.elapsed_seconds == 100.0


# --- break availability (one per rolling hour) ---------------------------

def test_break_not_available_at_session_start():
    session, _ = make_session()
    session.start()
    assert session.is_break_available() is False
    assert session.seconds_until_break_available() == 3600.0


def test_break_becomes_available_after_an_hour():
    session, clock = make_session()
    session.start()
    clock.advance(3600.0)
    assert session.is_break_available() is True
    assert session.seconds_until_break_available() == 0.0


# --- taking a break -------------------------------------------------------

def test_take_break_when_available_starts_a_break():
    session, clock = make_session()
    session.start()
    clock.advance(3600.0)
    assert session.take_break() is True
    assert session.on_break is True
    assert session.break_seconds_remaining() == 300.0


def test_take_break_when_unavailable_fails():
    session, _ = make_session()
    session.start()
    assert session.take_break() is False
    assert session.on_break is False


def test_take_break_when_not_running_fails():
    session, clock = make_session()
    clock.advance(3600.0)
    assert session.take_break() is False


def test_break_ends_automatically_after_its_duration():
    session, clock = make_session()
    session.start()
    clock.advance(3600.0)
    session.take_break()
    clock.advance(300.0)
    assert session.on_break is False
    assert session.break_seconds_remaining() == 0.0


def test_cannot_take_second_break_while_on_break():
    session, clock = make_session()
    session.start()
    clock.advance(3600.0)
    session.take_break()
    clock.advance(60.0)             # still mid-break
    assert session.take_break() is False


def test_next_break_requires_another_full_interval():
    session, clock = make_session()
    session.start()
    clock.advance(3600.0)
    session.take_break()            # first break taken at t+3600
    clock.advance(300.0)            # break ends
    assert session.is_break_available() is False
    clock.advance(3600.0 - 300.0)  # an hour after the break started
    assert session.is_break_available() is True


# --- auto-burn on absence -------------------------------------------------

def test_break_remaining_is_zero_when_not_on_break():
    session, _ = make_session()
    session.start()
    assert session.break_seconds_remaining() == 0.0
