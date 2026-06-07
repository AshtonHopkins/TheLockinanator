"""Tests for punishment selection and dispatch, using a fake audio player and
fake output-device resolver (no real sound, no pycaw)."""

from thelockinanator.audio_device import resolve_output_kind
from thelockinanator.punishments.audio_alarm import AudioAlarmPunishment
from thelockinanator.punishments.base import PunishmentManager

AUDIO = {
    "volume": 0.8,
    "output_override": None,
    "alarm_sounds": ["assets/sounds/alarm.wav"],
    "fart_sounds": ["assets/sounds/fart.wav"],
}


class FakePlayer:
    def __init__(self):
        self.calls = []

    def play(self, path, volume=1.0, loops=0):
        self.calls.append((path, volume, loops))

    def stop(self):
        self.calls.append(("stop",))


# --- output-device resolution --------------------------------------------

def test_resolve_uses_explicit_override():
    assert resolve_output_kind("speaker", detector=lambda: "headphones") == "speaker"
    assert resolve_output_kind("headphones", detector=lambda: "speaker") == "headphones"


def test_resolve_falls_back_to_detector():
    assert resolve_output_kind(None, detector=lambda: "headphones") == "headphones"


def test_resolve_ignores_invalid_override():
    assert resolve_output_kind("nonsense", detector=lambda: "speaker") == "speaker"


# --- audio punishment -----------------------------------------------------

def test_alarm_sound_on_headphones_at_configured_volume():
    player = FakePlayer()
    pun = AudioAlarmPunishment(AUDIO, player=player, kind_resolver=lambda: "headphones")
    pun.execute()
    path, volume, _loops = player.calls[0]
    assert "alarm" in path
    assert volume == 0.8


def test_fart_sound_on_speaker():
    player = FakePlayer()
    pun = AudioAlarmPunishment(AUDIO, player=player, kind_resolver=lambda: "speaker")
    pun.execute()
    assert "fart" in player.calls[0][0]


# --- manager --------------------------------------------------------------

class _StubPunishment:
    def __init__(self, name, available):
        self.name = name
        self._available = available
        self.ran = False

    def is_available(self):
        return self._available

    def execute(self):
        self.ran = True


def test_manager_runs_first_available_and_reports_its_name():
    unavailable = _StubPunishment("disabled", False)
    available = _StubPunishment("audio_alarm", True)
    manager = PunishmentManager([unavailable, available])
    assert manager.trigger() == "audio_alarm"
    assert available.ran is True
    assert unavailable.ran is False


def test_manager_returns_none_when_nothing_available():
    manager = PunishmentManager([_StubPunishment("disabled", False)])
    assert manager.trigger() is None
