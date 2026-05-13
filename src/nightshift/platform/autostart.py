"""HKCU autostart entry for nightshift.

Writes to the user's own ``Run`` key — no admin needed. ``register`` /
``unregister`` are idempotent; ``sync_with_config`` makes the Run value
match the user's ``toggles.autostart`` preference.
"""

from __future__ import annotations

import sys
from typing import Mapping, Optional

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "nightshift"


def _command() -> str:
    """The command line to register.

    For a PyInstaller bundle (``sys.frozen``) this is just the exe; for a
    dev checkout it re-launches via ``python -m nightshift`` so the editable
    install keeps working.
    """
    exe = sys.executable
    if getattr(sys, "frozen", False):
        return f'"{exe}"'
    return f'"{exe}" -m nightshift'


def _read_value() -> Optional[str]:
    if sys.platform != "win32":
        return None
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY,
                            0, winreg.KEY_READ) as key:
            value, _t = winreg.QueryValueEx(key, VALUE_NAME)
            return value if value else None
    except OSError:
        return None


def _write_value(value: str) -> None:
    if sys.platform != "win32":
        return
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY,
                        0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, value)


def _delete_value() -> None:
    if sys.platform != "win32":
        return
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY,
                            0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, VALUE_NAME)
    except OSError:
        pass


def is_registered() -> bool:
    return _read_value() is not None


def register() -> None:
    _write_value(_command())


def unregister() -> None:
    _delete_value()


def sync_with_config(cfg: Mapping) -> None:
    """Make the Run-key state match ``cfg['toggles']['autostart']``."""
    enabled = bool(cfg.get("toggles", {}).get("autostart", False))
    if enabled:
        register()
    else:
        unregister()
