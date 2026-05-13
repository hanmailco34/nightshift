"""System-tray icon and menu (pystray).

The tray runs on its own daemon thread (``Icon.run_detached``). All menu
handlers receive ``(icon, item)`` from pystray; we ignore those and just
call the provided no-arg callback. The owner (``MainWindow``) is expected
to marshal each callback to the tk main thread via ``root.after(0, ...)``.

cycle-04: the menu can include a **프리셋** submenu, populated lazily from
``get_presets()``. After the preset list changes, the owner should call
``Tray.update_presets()`` so the next time the user opens the tray they
see the fresh list.
"""

from __future__ import annotations

from typing import Callable, Iterable, List, Optional

import pystray
from PIL import Image, ImageDraw
from pystray import Menu, MenuItem


def _make_icon_image() -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((6, 6, 58, 58), fill=(255, 213, 102, 255))
    return img


class Tray:
    def __init__(self, *,
                 on_open: Callable[[], None],
                 on_toggle_pause: Callable[[], None],
                 on_night_now: Callable[[], None],
                 on_quit: Callable[[], None],
                 is_paused: Callable[[], bool],
                 on_apply_preset: Optional[Callable[[str], None]] = None,
                 get_presets: Optional[Callable[[], Iterable[str]]] = None):
        self._on_open = on_open
        self._on_toggle_pause = on_toggle_pause
        self._on_night_now = on_night_now
        self._on_quit = on_quit
        self._is_paused = is_paused
        self._on_apply_preset = on_apply_preset
        self._get_presets = get_presets or (lambda: [])
        self.icon = pystray.Icon(
            "nightshift",
            icon=_make_icon_image(),
            title="nightshift",
            menu=self._build_menu(),
        )

    @staticmethod
    def _wrap(fn: Callable[[], None]):
        def cb(_icon, _item) -> None:
            fn()
        return cb

    def _make_preset_handler(self, name: str):
        def cb(_icon, _item) -> None:
            if self._on_apply_preset is not None:
                self._on_apply_preset(name)
        return cb

    def _build_menu(self) -> Menu:
        items: List[MenuItem] = [
            MenuItem("열기", self._wrap(self._on_open), default=True),
            MenuItem("일시중지", self._wrap(self._on_toggle_pause),
                      checked=lambda _i: self._is_paused()),
            MenuItem("야간 즉시", self._wrap(self._on_night_now)),
        ]
        if self._on_apply_preset is not None:
            entries = list(self._get_presets() or [])
            preset_items: List[MenuItem] = []
            for entry in entries:
                if isinstance(entry, tuple):
                    name, enabled = entry[0], bool(entry[1])
                else:
                    name, enabled = str(entry), True
                preset_items.append(
                    MenuItem(name, self._make_preset_handler(name),
                              enabled=enabled))
            if preset_items:
                items.append(MenuItem("프리셋", Menu(*preset_items)))
        items.append(Menu.SEPARATOR)
        items.append(MenuItem("종료", self._wrap(self._on_quit)))
        return Menu(*items)

    def update_presets(self) -> None:
        """Rebuild the menu (presets submenu reflects the latest list)."""
        self.icon.menu = self._build_menu()
        try:
            self.icon.update_menu()
        except Exception:
            pass

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
