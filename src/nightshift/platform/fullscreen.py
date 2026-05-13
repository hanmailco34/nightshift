"""Detect when a fullscreen window owns the foreground.

f.lux behavior: temporarily restore the identity gamma ramp while the user
is running a fullscreen game/video, so our color cast doesn't fight an
exclusive-fullscreen presentation.

The Win32 plumbing is isolated in :func:`_get_foreground_rect` and
:func:`_foreground_class_name`; the pure helper :func:`_rect_matches_monitor`
does the geometry comparison and is unit-tested directly.
"""

from __future__ import annotations

import sys
from typing import Iterable, Optional, Tuple

_SHELL_CLASSES = {"Progman", "WorkerW", "Shell_TrayWnd", "Button"}
_TOLERANCE_PX = 2


def _rect_matches_monitor(win_rect: Tuple[int, int, int, int], mon) -> bool:
    """True if ``win_rect`` covers ``mon`` within ±2px on every side."""
    l, t, r, b = win_rect
    ml, mt = mon.x, mon.y
    mr, mb = mon.x + mon.width, mon.y + mon.height
    return (abs(l - ml) <= _TOLERANCE_PX
            and abs(t - mt) <= _TOLERANCE_PX
            and abs(r - mr) <= _TOLERANCE_PX
            and abs(b - mb) <= _TOLERANCE_PX)


def _get_foreground_rect() -> Optional[Tuple[int, int, int, int]]:
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None

    class RECT(ctypes.Structure):
        _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                    ("right", wintypes.LONG), ("bottom", wintypes.LONG)]

    r = RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(r)):
        return None
    return (r.left, r.top, r.right, r.bottom)


def _foreground_class_name() -> str:
    if sys.platform != "win32":
        return ""
    import ctypes

    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return ""
    buf = ctypes.create_unicode_buffer(256)
    if user32.RealGetWindowClassW(hwnd, buf, 256):
        return buf.value
    return ""


def is_fullscreen_app_visible(monitors: Iterable) -> bool:
    """True if the foreground window covers any monitor (within ±2px) and
    isn't a recognised shell window (desktop / taskbar)."""
    cls = _foreground_class_name()
    if cls in _SHELL_CLASSES:
        return False
    rect = _get_foreground_rect()
    if rect is None:
        return False
    return any(_rect_matches_monitor(rect, m) for m in monitors)
