"""System-tray icon and menu (pystray).

The tray runs on its own daemon thread (``Icon.run_detached``). All menu
handlers receive ``(icon, item)`` from pystray; we ignore those and just
call the provided no-arg callback. The owner (``MainWindow``) is expected
to marshal each callback to the tk main thread via ``root.after(0, ...)``.
"""

from __future__ import annotations

from typing import Callable

import pystray
from PIL import Image, ImageDraw
from pystray import Menu, MenuItem


def _make_icon_image() -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Filled yellow disc (sun/moon). Looks fine at 16x16 in the tray.
    d.ellipse((6, 6, 58, 58), fill=(255, 213, 102, 255))
    return img


class Tray:
    def __init__(self, *,
                 on_open: Callable[[], None],
                 on_toggle_pause: Callable[[], None],
                 on_night_now: Callable[[], None],
                 on_quit: Callable[[], None],
                 is_paused: Callable[[], bool]):
        self._is_paused = is_paused
        self.icon = pystray.Icon(
            "nightshift",
            icon=_make_icon_image(),
            title="nightshift",
            menu=Menu(
                MenuItem("열기", self._wrap(on_open), default=True),
                MenuItem("일시중지", self._wrap(on_toggle_pause),
                          checked=lambda _i: is_paused()),
                MenuItem("야간 즉시", self._wrap(on_night_now)),
                Menu.SEPARATOR,
                MenuItem("종료", self._wrap(on_quit)),
            ),
        )

    @staticmethod
    def _wrap(fn: Callable[[], None]):
        def cb(_icon, _item) -> None:
            fn()
        return cb

    def start(self) -> None:
        self.icon.run_detached()

    def stop(self) -> None:
        try:
            self.icon.stop()
        except Exception:
            pass

    def notify(self, message: str, title: str = "nightshift") -> None:
        try:
            self.icon.notify(message, title=title)
        except Exception:
            pass
