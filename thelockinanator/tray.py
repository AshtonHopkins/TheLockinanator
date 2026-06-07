"""System-tray icon and menu (pystray).

Runs detached so the Tk GUI keeps the main thread. The menu mirrors the window
controls plus Show/Quit. The tray is non-essential: if it fails to start, the
app still runs from the window.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pystray
from PIL import Image

_ICON_PATH = Path(__file__).resolve().parent / "assets" / "images" / "Monster.png"


def _load_icon() -> Image.Image:
    try:
        return Image.open(_ICON_PATH).convert("RGBA").resize((64, 64))
    except Exception:
        return Image.new("RGBA", (64, 64), (255, 77, 77, 255))


class TrayController:
    def __init__(
        self,
        on_show: Callable[[], None],
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
        on_take_break: Callable[[], None],
        on_toggle_preview: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        self._on_quit = on_quit
        menu = pystray.Menu(
            pystray.MenuItem("Show Window", lambda i, item: on_show(), default=True),
            pystray.MenuItem("Start", lambda i, item: on_start()),
            pystray.MenuItem("Stop", lambda i, item: on_stop()),
            pystray.MenuItem("Take Break", lambda i, item: on_take_break()),
            pystray.MenuItem("Toggle Preview", lambda i, item: on_toggle_preview()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", lambda i, item: self._quit()),
        )
        self._icon = pystray.Icon("lockinanator", _load_icon(), "The Lockinanator", menu)

    def start(self) -> None:
        self._icon.run_detached()

    def stop(self) -> None:
        try:
            self._icon.stop()
        except Exception:
            pass

    def _quit(self) -> None:
        self._on_quit()
        self.stop()
