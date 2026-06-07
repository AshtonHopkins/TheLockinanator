"""Tests for the SQLite session stats store (uses a temp DB file)."""

from thelockinanator.stats import StatsStore


def make_store(tmp_path):
    return StatsStore(tmp_path / "stats.sqlite3")


def test_new_store_has_no_sessions(tmp_path):
    store = make_store(tmp_path)
    assert store.recent() == []
    assert store.summary().total_sessions == 0


def test_record_and_read_back(tmp_path):
    store = make_store(tmp_path)
    rid = store.record_session(
        started_at="2026-06-07T10:00:00", ended_at="2026-06-07T10:50:00",
        duration_seconds=3000.0, focus_pct=82.0,
        distraction_episodes=4, punishments=1,
    )
    assert rid == 1
    rows = store.recent()
    assert len(rows) == 1
    row = rows[0]
    assert row.duration_seconds == 3000.0
    assert row.focus_pct == 82.0
    assert row.distraction_episodes == 4
    assert row.punishments == 1


def test_recent_returns_newest_first_and_respects_limit(tmp_path):
    store = make_store(tmp_path)
    for i in range(5):
        store.record_session(
            started_at=f"t{i}", ended_at=f"t{i}", duration_seconds=float(i),
            focus_pct=50.0, distraction_episodes=0, punishments=0,
        )
    rows = store.recent(limit=2)
    assert len(rows) == 2
    assert rows[0].duration_seconds == 4.0   # newest first
    assert rows[1].duration_seconds == 3.0


def test_summary_aggregates(tmp_path):
    store = make_store(tmp_path)
    store.record_session(started_at="a", ended_at="a", duration_seconds=600.0,
                         focus_pct=80.0, distraction_episodes=2, punishments=1)
    store.record_session(started_at="b", ended_at="b", duration_seconds=600.0,
                         focus_pct=60.0, distraction_episodes=3, punishments=2)
    summary = store.summary()
    assert summary.total_sessions == 2
    assert summary.avg_focus_pct == 70.0   # (80 + 60) / 2
    assert summary.total_punishments == 3


def test_store_persists_across_instances(tmp_path):
    path = tmp_path / "stats.sqlite3"
    StatsStore(path).record_session(started_at="a", ended_at="a", duration_seconds=1.0,
                                    focus_pct=100.0, distraction_episodes=0, punishments=0)
    assert StatsStore(path).summary().total_sessions == 1
