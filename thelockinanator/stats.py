"""SQLite-backed session statistics.

Each finished session is logged as one row; the GUI shows an end-of-session
summary and history can be reviewed over time. Stdlib only.
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class SessionRecord:
    id: int
    started_at: str
    ended_at: str
    duration_seconds: float
    focus_pct: float
    distraction_episodes: int
    punishments: int


@dataclass(frozen=True)
class SummaryStats:
    total_sessions: int
    avg_focus_pct: float
    total_punishments: int


class StatsStore:
    def __init__(self, db_path: str | os.PathLike[str]) -> None:
        self._path = os.fspath(db_path)
        parent = os.path.dirname(self._path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    ended_at TEXT NOT NULL,
                    duration_seconds REAL NOT NULL,
                    focus_pct REAL NOT NULL,
                    distraction_episodes INTEGER NOT NULL,
                    punishments INTEGER NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        return conn

    def record_session(
        self,
        started_at: str,
        ended_at: str,
        duration_seconds: float,
        focus_pct: float,
        distraction_episodes: int,
        punishments: int,
    ) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO sessions (started_at, ended_at, duration_seconds,
                                      focus_pct, distraction_episodes, punishments)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (started_at, ended_at, duration_seconds, focus_pct,
                 distraction_episodes, punishments),
            )
            return int(cur.lastrowid)

    def recent(self, limit: int = 10) -> list[SessionRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM sessions ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            SessionRecord(
                id=r["id"], started_at=r["started_at"], ended_at=r["ended_at"],
                duration_seconds=r["duration_seconds"], focus_pct=r["focus_pct"],
                distraction_episodes=r["distraction_episodes"], punishments=r["punishments"],
            )
            for r in rows
        ]

    def summary(self) -> SummaryStats:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS n,
                       COALESCE(AVG(focus_pct), 0.0) AS avg_focus,
                       COALESCE(SUM(punishments), 0) AS total_punishments
                FROM sessions
                """
            ).fetchone()
        return SummaryStats(
            total_sessions=int(row["n"]),
            avg_focus_pct=float(row["avg_focus"]),
            total_punishments=int(row["total_punishments"]),
        )
