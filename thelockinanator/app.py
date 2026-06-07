"""The orchestrator: wires detectors -> engine/meter -> punishment, owns the
session, drives a worker thread that processes webcam frames, and feeds an
immutable UiState snapshot to the GUI.

Heavy/IO collaborators (vision pipeline, webcam, audio player, GUI, tray,
preview) are injectable or lazily built, so the core stepping logic
(:meth:`process_frame`) can be exercised in tests with fakes and a FakeClock.
"""

from __future__ import annotations

import datetime as _dt
import threading
import time
from pathlib import Path
from typing import Any

from .audio_device import resolve_output_kind
from .clock import Clock, RealClock
from .detectors.absence import AbsenceDetector
from .detectors.look_away import LookAwayDetector
from .detectors.phone_use import PhoneUseDetector
from .focus_engine import FocusEngine
from .focus_meter import FocusMeter
from .punishments.audio_alarm import AudioAlarmPunishment
from .punishments.base import PunishmentManager
from .session import SessionManager
from .stats import StatsStore
from .ui_state import UiState


def _now_iso() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


def default_db_path() -> Path:
    return Path.home() / ".thelockinanator" / "stats.sqlite3"


class Orchestrator:
    def __init__(
        self,
        config: dict[str, Any],
        *,
        clock: Clock | None = None,
        vision: Any | None = None,
        capture: Any | None = None,
        player: Any | None = None,
        punishments: Any | None = None,
        stats: StatsStore | None = None,
    ) -> None:
        self._cfg = config
        self._clock = clock or RealClock()
        self._lock = threading.RLock()

        self._engine = FocusEngine(FocusMeter(config["focus_meter"]))
        self._session = SessionManager(config["session"], self._clock)
        self._absence_grace = float(config["session"]["absence_grace_seconds"])

        det_cfg = config["detection"]
        self._fps = float(det_cfg.get("fps", 12))
        self._detectors = [
            LookAwayDetector(det_cfg),
            PhoneUseDetector(det_cfg),
            AbsenceDetector(det_cfg),
        ]

        audio_cfg = config["audio"]
        self._player = player if player is not None else _build_default_player()
        if punishments is not None:
            self._punishments = punishments
        else:
            self._punishments = PunishmentManager([
                AudioAlarmPunishment(
                    audio_cfg, self._player,
                    lambda: resolve_output_kind(audio_cfg.get("output_override")),
                )
            ])
        self._stats = stats if stats is not None else StatsStore(default_db_path())

        self._vision = vision
        self._capture = capture
        self._preview = None
        self._preview_enabled = bool(config["ui"].get("show_preview", False))
        self._gui = None
        self._tray = None

        self._absence_time = 0.0
        self._last_active_sources: tuple[str, ...] = ()
        self._last_analysis = None
        self._session_started_iso: str | None = None
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None
        self._snapshot = UiState()
        self._rebuild_snapshot()

    # --- snapshot ---------------------------------------------------------

    def snapshot(self) -> UiState:
        with self._lock:
            return self._snapshot

    def _rebuild_snapshot(self) -> None:
        s = self._session
        stats = self._engine.stats
        self._snapshot = UiState(
            running=s.running,
            on_break=s.on_break,
            level=self._engine.level,
            max_level=float(self._cfg["focus_meter"]["max_level"]),
            elapsed_seconds=s.elapsed_seconds,
            break_remaining=s.break_seconds_remaining(),
            next_break_in=s.seconds_until_break_available(),
            break_available=s.is_break_available(),
            focus_pct=stats.focus_pct,
            distraction_episodes=stats.distraction_episodes,
            punishments=stats.punishments,
            active_sources=self._last_active_sources,
        )

    # --- core step (testable) --------------------------------------------

    def process_frame(self, frame: Any, dt: float):
        analysis = self._vision.analyze(frame)
        self._last_analysis = analysis
        signals = [d.process(analysis) for d in self._detectors]
        result = self._engine.update(signals, dt)
        self._last_active_sources = result.active_sources

        if not analysis.face_present:
            self._absence_time += dt
            if self._absence_time >= self._absence_grace and self._session.is_break_available():
                self._session.take_break()  # auto-burn
        else:
            self._absence_time = 0.0

        if result.punished:
            self._punishments.trigger()
            if self._gui is not None:
                self._gui.request_toast("Focus meter empty - get back to it.")

        self._rebuild_snapshot()
        return result

    # --- session control --------------------------------------------------

    def start_session(self) -> None:
        with self._lock:
            self._engine.reset()
            self._absence_time = 0.0
            self._last_active_sources = ()
            self._session.start()
            self._session_started_iso = _now_iso()
            self._rebuild_snapshot()

    def stop_session(self) -> None:
        with self._lock:
            if not self._session.running:
                return
            stats = self._engine.stats
            duration = self._session.elapsed_seconds
            self._session.stop()
            self._stats.record_session(
                started_at=self._session_started_iso or _now_iso(),
                ended_at=_now_iso(),
                duration_seconds=duration,
                focus_pct=stats.focus_pct,
                distraction_episodes=stats.distraction_episodes,
                punishments=stats.punishments,
            )
            self._rebuild_snapshot()
        if self._gui is not None:
            self._gui.request_toast(f"Session over - Focus {stats.focus_pct:.0f}%")

    def take_break(self) -> bool:
        with self._lock:
            ok = self._session.take_break()
            self._rebuild_snapshot()
            return ok

    def toggle_preview(self, enabled: bool) -> None:
        # Only set the flag; the worker thread owns all cv2 window calls.
        self._preview_enabled = bool(enabled)

    # --- lifecycle --------------------------------------------------------

    def run(self) -> None:
        from .gui.main_window import MainWindow

        self._gui = MainWindow(
            state_provider=self.snapshot,
            on_start=self._on_start_clicked,
            on_stop=self.stop_session,
            on_take_break=self.take_break,
            on_toggle_preview=self.toggle_preview,
            on_close=self._on_close,
        )
        self._gui.set_preview_checkbox(self._preview_enabled)

        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()
        self._start_tray()

        self._gui.run()  # blocks until the window is destroyed
        self.shutdown()

    def _start_tray(self) -> None:
        try:
            from .tray import TrayController

            self._tray = TrayController(
                on_show=self._gui.request_show,
                on_start=self._on_start_clicked,
                on_stop=self.stop_session,
                on_take_break=self.take_break,
                on_toggle_preview=lambda: self.toggle_preview(not self._preview_enabled),
                on_quit=self._on_quit,
            )
            self._tray.start()
        except Exception:
            self._tray = None  # tray is non-essential; app still works without it

    def _on_start_clicked(self) -> None:
        self.start_session()
        if self._cfg["ui"].get("hide_on_start", True) and self._gui is not None:
            self._gui.hide()

    def _on_close(self) -> None:
        if self._gui is not None:
            self._gui.hide()  # X minimizes to tray; quit via tray

    def _on_quit(self) -> None:
        if self._gui is not None:
            self._gui.request_quit()

    def _worker_loop(self) -> None:
        if self._vision is None:
            from .vision import VisionPipeline
            self._vision = VisionPipeline(self._cfg.get("detection"))
        if self._capture is None:
            from .capture import WebcamCapture
            self._capture = WebcamCapture(0)
        from .preview import PreviewWindow
        self._preview = PreviewWindow()

        interval = 1.0 / self._fps
        last = self._clock.now()
        while not self._stop_event.is_set():
            now = self._clock.now()
            dt = now - last
            last = now
            with self._lock:
                running = self._session.running
                on_break = self._session.on_break

            if running and not on_break:
                frame = self._capture.read()
                if frame is not None:
                    with self._lock:
                        result = self.process_frame(frame, dt)
                    if self._preview_enabled:
                        self._preview.show(
                            frame, self._last_analysis, result.level, result.distracted
                        )
            else:
                with self._lock:
                    self._rebuild_snapshot()
                if not self._preview_enabled:
                    self._preview.close()

            time.sleep(max(0.0, interval - (self._clock.now() - now)))

        self._cleanup_worker()

    def _cleanup_worker(self) -> None:
        if self._capture is not None:
            self._capture.release()
        if self._preview is not None:
            self._preview.close()
        if self._vision is not None and hasattr(self._vision, "close"):
            self._vision.close()

    def shutdown(self) -> None:
        self._stop_event.set()
        if self._worker is not None:
            self._worker.join(timeout=2.0)
        if self._tray is not None:
            try:
                self._tray.stop()
            except Exception:
                pass
        try:
            self._player.stop()
        except Exception:
            pass


def _build_default_player():
    from .audio import PygameAudioPlayer

    return PygameAudioPlayer()
