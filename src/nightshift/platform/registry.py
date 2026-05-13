"""Read-only access to ``HKLM\\...\\ICM\\GdiICMGammaRange``.

Setting this DWORD to 256 and rebooting unlocks the warm end of the gamma
ramp. We only ever *read* it from the app: writing requires admin, so the
user runs the one-line PowerShell command we surface in the UI.
"""

from __future__ import annotations

import sys

_REG_SUBKEY = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ICM"
_REG_VALUE = "GdiICMGammaRange"


def read_gdi_icm_gamma_range() -> int | None:
    """Current DWORD value, or ``None`` if absent / unreadable / non-Windows."""
    if sys.platform != "win32":
        return None
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _REG_SUBKEY,
                            0, winreg.KEY_READ) as key:
            value, _type = winreg.QueryValueEx(key, _REG_VALUE)
            return int(value) if value is not None else None
    except OSError:
        return None
