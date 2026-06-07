"""The deliberately silly control window.

A single Tk ``Canvas`` holds everything: the transparent art collage sits at the
back, an opaque central panel guarantees the controls stay readable on top, and
the meter / timers / score / buttons live on the panel.

Threading model: the window runs on the main thread and *pulls* a
:class:`~thelockinanator.ui_state.UiState` from a provider each tick, so it never
reaches into engine internals from another thread. Cross-thread requests (the
tray asking to restore the window) go through a thread-safe queue drained on the
Tk thread.
"""

from __future__ import annotations

import queue
import tkinter as tk
from typing import Callable

from ..ui_state import UiState
from . import layout
from .meter_widget import MeterWidget

# --- palette (loud "energy drink" dark theme) ----------------------------
BG = "#1b1b28"
PANEL = "#2a2a3d"
PANEL_BORDER = "#ffd84d"
ACCENT = "#ff4d4d"
TEXT = "#f5f5f7"
MUTED = "#b9b9cc"
GOOD = "#48d17a"
BAD = "#ff5a4d"
BREAK = "#5ab0ff"

WIDTH, HEIGHT = 820, 560
REFRESH_MS = 100

# Central panel bounds.
PX0, PY0, PX1, PY1 = 205, 120, 615, 480


def _fmt_hms(seconds: float) -> str:
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


class MainWindow:
    def __init__(
        self,
        state_provider: Callable[[], UiState],
        on_start: Callable[[], None] = lambda: None,
        on_stop: Callable[[], None] = lambda: None,
        on_take_break: Callable[[], None] = lambda: None,
        on_toggle_preview: Callable[[bool], None] = lambda _enabled: None,
        on_close: Callable[[], None] | None = None,
        start_hidden: bool = False,
    ) -> None:
        self._state_provider = state_provider
        self._on_start = on_start
        self._on_stop = on_stop
        self._on_take_break = on_take_break
        self._on_toggle_preview = on_toggle_preview
        self._on_close = on_close
        self._requests: queue.Queue[str] = queue.Queue()

        self.root = tk.Tk()
        self.root.title("The Lockinanator")
        self.root.geometry(f"{WIDTH}x{HEIGHT}")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self._handle_close)

        self.canvas = tk.Canvas(
            self.root, width=WIDTH, height=HEIGHT, bg=BG, highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)

        self._art_refs: list[layout.PlacedArt] = []
        self._build()

        if start_hidden:
            self.root.withdraw()

    # --- construction -----------------------------------------------------

    def _build(self) -> None:
        # Background art collage (kept behind everything; refs prevent GC).
        self._art_refs = layout.load_art(WIDTH, HEIGHT)
        for art in self._art_refs:
            self.canvas.create_image(art.x, art.y, image=art.image, anchor="nw")

        # Title (sits above the panel, over the top-corner art). Outlined so the
        # white text stays readable even over the eagle's white head.
        self._outlined_text(
            WIDTH // 2, 60, "THE  LOCKINANATOR",
            font=("Arial Black", 26, "bold"), fill=TEXT, outline="#000000", width=2,
        )
        self._outlined_text(
            WIDTH // 2, 90, "lock in. or else.",
            font=("Consolas", 12, "italic"), fill=ACCENT, outline="#000000", width=1,
        )

        # Opaque central panel so controls are never obscured by the art.
        self.canvas.create_rectangle(
            PX0, PY0, PX1, PY1, fill=PANEL, outline=PANEL_BORDER, width=4,
        )

        # Focus meter (centerpiece).
        self.canvas.create_text(
            PX0 + 24, PY0 + 28, text="FOCUS METER", anchor="w",
            fill=MUTED, font=("Consolas", 11, "bold"),
        )
        self._meter = MeterWidget(self.canvas, PX0 + 24, PY0 + 44, (PX1 - PX0) - 48, 46)

        cx = (PX0 + PX1) // 2

        # Status line.
        self._status_id = self.canvas.create_text(
            cx, PY0 + 120, text="Idle", fill=MUTED, font=("Arial Black", 16),
        )

        # Timers and score, stacked as full-width centered rows (the panel is too
        # narrow for two side-by-side text columns).
        self._elapsed_id = self.canvas.create_text(
            cx, PY0 + 158, text="Session  0:00", fill=TEXT, font=("Consolas", 15),
        )
        self._break_id = self.canvas.create_text(
            cx, PY0 + 192, text="Next break in  --:--", fill=MUTED, font=("Consolas", 13),
        )
        self._score_id = self.canvas.create_text(
            cx, PY0 + 226, text="Focus 100%  ·  Distractions 0  ·  Blasts 0",
            fill=GOOD, font=("Consolas", 11, "bold"),
        )

        # Buttons (short labels so all three fit the panel width comfortably).
        self._start_btn = self._make_button("START", GOOD, self._handle_start)
        self._stop_btn = self._make_button("STOP", BAD, self._handle_stop)
        self._break_btn = self._make_button("BREAK", BREAK, self._handle_break)
        self.canvas.create_window(PX0 + 78, PY1 - 78, window=self._start_btn)
        self.canvas.create_window((PX0 + PX1) // 2, PY1 - 78, window=self._stop_btn)
        self.canvas.create_window(PX1 - 78, PY1 - 78, window=self._break_btn)

        # Preview toggle.
        self._preview_var = tk.BooleanVar(value=False)
        self._preview_chk = tk.Checkbutton(
            self.canvas, text="Show camera preview", variable=self._preview_var,
            command=self._handle_preview, bg=PANEL, fg=MUTED, selectcolor=BG,
            activebackground=PANEL, activeforeground=TEXT, font=("Consolas", 10),
            borderwidth=0, highlightthickness=0,
        )
        self.canvas.create_window((PX0 + PX1) // 2, PY1 - 28, window=self._preview_chk)

        self._refresh_buttons(UiState())

    def _outlined_text(self, x: int, y: int, text: str, font, fill: str,
                       outline: str = "#000000", width: int = 2, **kw) -> int:
        """Draw ``text`` with a solid outline so it reads over any background art."""
        for dx in (-width, 0, width):
            for dy in (-width, 0, width):
                if dx or dy:
                    self.canvas.create_text(x + dx, y + dy, text=text, font=font,
                                            fill=outline, **kw)
        return self.canvas.create_text(x, y, text=text, font=font, fill=fill, **kw)

    def _make_button(self, label: str, color: str, command: Callable[[], None]) -> tk.Button:
        return tk.Button(
            self.canvas, text=label, command=command,
            bg=color, fg="#11111a", activebackground=color, activeforeground="#11111a",
            font=("Arial Black", 11), relief="raised", borderwidth=3,
            padx=8, pady=6, width=6, cursor="hand2",
        )

    # --- button / event handlers -----------------------------------------

    def _handle_start(self) -> None:
        self._on_start()

    def _handle_stop(self) -> None:
        self._on_stop()

    def _handle_break(self) -> None:
        self._on_take_break()

    def _handle_preview(self) -> None:
        self._on_toggle_preview(bool(self._preview_var.get()))

    def _handle_close(self) -> None:
        if self._on_close is not None:
            self._on_close()
        else:
            self.root.destroy()

    # --- public, thread-safe controls ------------------------------------

    def request_show(self) -> None:
        """Ask the window to restore itself (safe to call from any thread)."""
        self._requests.put("show")

    def hide(self) -> None:
        self.root.withdraw()

    def show(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def set_preview_checkbox(self, enabled: bool) -> None:
        self._preview_var.set(bool(enabled))

    # --- per-tick rendering ----------------------------------------------

    def update(self, state: UiState) -> None:
        self._meter.set_level(state.level, state.max_level)

        if state.on_break:
            status, color = "ON BREAK", BREAK
        elif state.running and state.active_sources:
            sources = ", ".join(state.active_sources)
            status, color = f"DISTRACTED: {sources}", BAD
        elif state.running:
            status, color = "LOCKED IN", GOOD
        else:
            status, color = "IDLE", MUTED
        self.canvas.itemconfigure(self._status_id, text=status, fill=color)

        self.canvas.itemconfigure(
            self._elapsed_id, text=f"Session  {_fmt_hms(state.elapsed_seconds)}"
        )
        self.canvas.itemconfigure(self._break_id, **self._break_label(state))

        focus_color = GOOD if state.focus_pct >= 70 else (PANEL_BORDER if state.focus_pct >= 40 else BAD)
        self.canvas.itemconfigure(
            self._score_id,
            text=(
                f"Focus {state.focus_pct:.0f}%  ·  "
                f"Distractions {state.distraction_episodes}  ·  "
                f"Blasts {state.punishments}"
            ),
            fill=focus_color,
        )
        self._refresh_buttons(state)

    @staticmethod
    def _break_label(state: UiState) -> dict[str, str]:
        if state.on_break:
            return {"text": f"On break  {_fmt_hms(state.break_remaining)} left", "fill": BREAK}
        if not state.running:
            return {"text": "Next break in  --:--", "fill": MUTED}
        if state.break_available:
            return {"text": "Break ready!", "fill": GOOD}
        return {"text": f"Next break in  {_fmt_hms(state.next_break_in)}", "fill": MUTED}

    def _refresh_buttons(self, state: UiState) -> None:
        self._start_btn.configure(state="disabled" if state.running else "normal")
        self._stop_btn.configure(state="normal" if state.running else "disabled")
        can_break = state.running and not state.on_break and state.break_available
        self._break_btn.configure(state="normal" if can_break else "disabled")

    # --- main loop --------------------------------------------------------

    def _tick(self) -> None:
        while True:
            try:
                cmd = self._requests.get_nowait()
            except queue.Empty:
                break
            if cmd == "show":
                self.show()
        try:
            self.update(self._state_provider())
        finally:
            self.root.after(REFRESH_MS, self._tick)

    def run(self) -> None:
        self.root.after(REFRESH_MS, self._tick)
        self.root.mainloop()
