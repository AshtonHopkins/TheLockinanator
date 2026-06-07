"""Tests for the pure detector decision logic, driven by synthetic
FrameAnalysis values (no camera, no MediaPipe)."""

from thelockinanator.detectors.absence import AbsenceDetector
from thelockinanator.detectors.analysis import FrameAnalysis
from thelockinanator.detectors.look_away import LookAwayDetector
from thelockinanator.detectors.phone_use import PhoneUseDetector

CFG = {
    "look_away_yaw_deg": 25.0,
    "look_away_pitch_deg": 20.0,
    "phone_pitch_deg": 18.0,
    "phone_hand_radius": 0.20,
}


def analysis(**kw) -> FrameAnalysis:
    base = dict(frame_w=640, frame_h=480, face_present=True,
                yaw=0.0, pitch=0.0, roll=0.0, face_center=(0.5, 0.5), hands=())
    base.update(kw)
    return FrameAnalysis(**base)


# --- absence --------------------------------------------------------------

def test_absence_flags_missing_face():
    assert AbsenceDetector(CFG).process(analysis(face_present=False)).distracted is True


def test_absence_quiet_when_face_present():
    assert AbsenceDetector(CFG).process(analysis(face_present=True)).distracted is False


# --- look away ------------------------------------------------------------

def test_look_away_quiet_when_facing_screen():
    assert LookAwayDetector(CFG).process(analysis(yaw=5.0, pitch=5.0)).distracted is False


def test_look_away_flags_large_yaw_either_direction():
    det = LookAwayDetector(CFG)
    assert det.process(analysis(yaw=30.0)).distracted is True
    assert det.process(analysis(yaw=-30.0)).distracted is True


def test_look_away_flags_looking_down():
    assert LookAwayDetector(CFG).process(analysis(pitch=25.0)).distracted is True


def test_look_away_defers_to_absence_when_no_face():
    # No face -> look-away stays quiet (absence owns that case).
    assert LookAwayDetector(CFG).process(analysis(face_present=False)).distracted is False


# --- phone use ------------------------------------------------------------

def test_phone_quiet_without_hands():
    # Looking down but no hand visible -> not a phone (look-away covers it).
    assert PhoneUseDetector(CFG).process(analysis(pitch=30.0, hands=())).distracted is False


def test_phone_flags_hand_visible_while_looking_down():
    a = analysis(pitch=25.0, hands=(((0.5, 0.8),),))
    assert PhoneUseDetector(CFG).process(a).distracted is True


def test_phone_flags_hand_raised_near_face():
    # Hand near the face center (phone-to-face), head not tilted down.
    a = analysis(pitch=0.0, face_center=(0.5, 0.5), hands=(((0.55, 0.55),),))
    assert PhoneUseDetector(CFG).process(a).distracted is True


def test_phone_quiet_when_hand_far_and_upright():
    a = analysis(pitch=0.0, face_center=(0.5, 0.5), hands=(((0.1, 0.9),),))
    assert PhoneUseDetector(CFG).process(a).distracted is False
