"""Tests for config loading, saving, and default merging."""

import json

from thelockinanator import config


def test_defaults_include_core_meter_timings():
    defaults = config.default_config()
    meter = defaults["focus_meter"]
    # The two numbers the user specified explicitly.
    assert meter["drain_seconds"] == 10.0   # full -> empty under sustained distraction
    assert meter["refill_seconds"] == 120.0  # empty -> full under sustained focus


def test_defaults_include_break_rules():
    session = config.default_config()["session"]
    assert session["break_duration_seconds"] == 300.0   # 5 minutes
    assert session["break_interval_seconds"] == 3600.0  # one per hour


def test_load_missing_path_returns_defaults(tmp_path):
    loaded = config.load_config(tmp_path / "does_not_exist.json")
    assert loaded == config.default_config()


def test_user_overrides_are_deep_merged(tmp_path):
    path = tmp_path / "user.json"
    path.write_text(json.dumps({"focus_meter": {"drain_seconds": 4.0}}))

    loaded = config.load_config(path)

    # Overridden value wins...
    assert loaded["focus_meter"]["drain_seconds"] == 4.0
    # ...but sibling defaults survive the partial override.
    assert loaded["focus_meter"]["refill_seconds"] == 120.0


def test_save_then_load_round_trips(tmp_path):
    path = tmp_path / "user.json"
    data = config.default_config()
    data["audio"]["volume"] = 0.3

    config.save_config(path, data)
    reloaded = config.load_config(path)

    assert reloaded["audio"]["volume"] == 0.3


def test_defaults_are_not_mutated_by_caller():
    a = config.default_config()
    a["focus_meter"]["drain_seconds"] = 999.0
    b = config.default_config()
    assert b["focus_meter"]["drain_seconds"] == 10.0
