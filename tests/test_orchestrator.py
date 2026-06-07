"""Integration test for the orchestrator's core stepping logic, using a fake
vision pipeline, fake audio, and a fake punishment manager (no camera, no GUI,
deterministic FakeClock)."""

from thelockinanator.app import Orchestrator
from thelockinanator.clock import FakeClock
from thelockinanator.config import default_config
from thelockinanator.detectors.analysis import FrameAnalysis
from thelockinanator.stats import StatsStore

FOCUSED = FrameAnalysis(640, 480, face_present=True, yaw=0.0, pitch=0.0, roll=0.0,
                        face_center=(0.5, 0.5), hands=())
LOOKING_AWAY = FrameAnalysis(640, 480, face_present=True, yaw=40.0, pitch=0.0, roll=0.0,
                             face_center=(0.5, 0.5), hands=())
ABSENT = FrameAnalysis(640, 480, face_present=False)


class FakeVision:
    def __init__(self, analysis=FOCUSED):
        self.analysis = analysis

    def analyze(self, frame):
        return self.analysis


class FakeManager:
    def __init__(self):
        self.triggers = 0

    def trigger(self):
        self.triggers += 1
        return "audio_alarm"


class FakePlayer:
    def play(self, *a, **k):
        pass

    def stop(self):
        pass


def make_orch(tmp_path, vision=None, manager=None, clock=None):
    vision = vision or FakeVision()
    manager = manager or FakeManager()
    clock = clock or FakeClock(start=1000.0)
    orch = Orchestrator(
        default_config(), clock=clock, vision=vision, player=FakePlayer(),
        punishments=manager, stats=StatsStore(tmp_path / "stats.sqlite3"),
    )
    return orch, clock, vision, manager


def test_focused_session_keeps_meter_full(tmp_path):
    orch, _clock, _vision, manager = make_orch(tmp_path)
    orch.start_session()
    for _ in range(10):
        orch.process_frame(frame=None, dt=1.0)
    snap = orch.snapshot()
    assert snap.running is True
    assert snap.level == 100.0
    assert manager.triggers == 0


def test_sustained_distraction_triggers_one_punishment(tmp_path):
    vision = FakeVision(LOOKING_AWAY)
    orch, _clock, _vision, manager = make_orch(tmp_path, vision=vision)
    orch.start_session()
    orch.process_frame(frame=None, dt=2.0)          # consume grace
    result = orch.process_frame(frame=None, dt=10.0)  # drain to empty -> punish
    assert result.punished is True
    assert manager.triggers == 1
    assert orch.snapshot().punishments == 1
    assert orch.snapshot().active_sources == ("look_away",)


def test_absence_autoburns_break_when_available(tmp_path):
    vision = FakeVision(FOCUSED)
    clock = FakeClock(start=1000.0)
    orch, _clock, _vision, _manager = make_orch(tmp_path, vision=vision, clock=clock)
    orch.start_session()
    clock.advance(3600.0)            # a break unlocks
    vision.analysis = ABSENT
    orch.process_frame(frame=None, dt=6.0)  # absence beyond 5s grace -> auto-burn
    assert orch.snapshot().on_break is True


def test_stop_records_a_session_row(tmp_path):
    stats = StatsStore(tmp_path / "stats.sqlite3")
    clock = FakeClock(start=1000.0)
    orch = Orchestrator(default_config(), clock=clock, vision=FakeVision(),
                        player=FakePlayer(), punishments=FakeManager(), stats=stats)
    orch.start_session()
    clock.advance(120.0)
    orch.process_frame(frame=None, dt=1.0)
    orch.stop_session()
    assert stats.summary().total_sessions == 1
    assert orch.snapshot().running is False
