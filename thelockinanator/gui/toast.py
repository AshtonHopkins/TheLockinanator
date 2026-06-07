"""A deliberately low-key toast popup.

The audio is the real punishment; this is just a small, brief, borderless banner
near the top of the screen that auto-dismisses, so you can refocus quickly. Must
be created on the Tk main thread.
"""

from __future__ import annotations

import tkinter as tk

_BG = "#2a2a3d"
_BORDER = "#ffd84d"
_FG = "#f5f5f7"


def show_toast(root: tk.Misc, message: str, duration_ms: int = 1800) -> tk.Toplevel:
    top = tk.Toplevel(root)
    top.overrideredirect(True)
    top.attributes("-topmost", True)
    try:
        top.attributes("-alpha", 0.95)
    except tk.TclError:
        pass

    frame = tk.Frame(top, bg=_BG, highlightbackground=_BORDER, highlightthickness=2)
    frame.pack()
    tk.Label(
        frame, text=message, bg=_BG, fg=_FG, font=("Segoe UI", 11),
        padx=18, pady=10,
    ).pack()

    top.update_idletasks()
    screen_w = top.winfo_screenwidth()
    win_w = top.winfo_width()
    top.geometry(f"+{(screen_w - win_w) // 2}+44")  # top-center

    top.after(duration_ms, top.destroy)
    return top
