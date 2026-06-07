"""Tests for rotation-matrix -> (yaw, pitch, roll) extraction."""

import math

import numpy as np
import pytest

from thelockinanator.detectors.headpose import rotation_matrix_to_euler_deg


def _rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def _ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def _rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def test_identity_is_all_zero():
    yaw, pitch, roll = rotation_matrix_to_euler_deg(np.eye(3))
    assert yaw == pytest.approx(0, abs=1e-4)
    assert pitch == pytest.approx(0, abs=1e-4)
    assert roll == pytest.approx(0, abs=1e-4)


def test_rotation_about_x_is_pitch():
    yaw, pitch, roll = rotation_matrix_to_euler_deg(_rx(math.radians(15)))
    assert pitch == pytest.approx(15, abs=1e-3)
    assert yaw == pytest.approx(0, abs=1e-3)
    assert roll == pytest.approx(0, abs=1e-3)


def test_rotation_about_y_is_yaw():
    yaw, pitch, roll = rotation_matrix_to_euler_deg(_ry(math.radians(20)))
    assert yaw == pytest.approx(20, abs=1e-3)
    assert pitch == pytest.approx(0, abs=1e-3)
    assert roll == pytest.approx(0, abs=1e-3)


def test_rotation_about_z_is_roll():
    yaw, pitch, roll = rotation_matrix_to_euler_deg(_rz(math.radians(10)))
    assert roll == pytest.approx(10, abs=1e-3)
    assert yaw == pytest.approx(0, abs=1e-3)
    assert pitch == pytest.approx(0, abs=1e-3)
