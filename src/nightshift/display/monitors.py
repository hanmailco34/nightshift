"""Enumerate connected monitors on Windows.

Combines ``EnumDisplayMonitors`` / ``GetMonitorInfoW`` (geometry, primary flag,
GDI device name like ``\\\\.\\DISPLAY1``) with ``EnumDisplayDevicesW`` (the
human-readable monitor model). Produces stable, human-identifiable labels such
as ``"Monitor 1 - Dell U2719D (primary)"``.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import List, Optional

_MONITORINFOF_PRIMARY = 0x1


@dataclass(frozen=True)
class Monitor:
    index: int            # 0-based, ordered left-to-right then top-to-bottom
    device_name: str      # GDI device, e.g. "\\.\DISPLAY1" — pass to gamma.apply_kelvin
    model: str            # e.g. "Dell U2719D" (best effort; may be "Generic PnP Monitor")
    width: int
    height: int
    x: int
    y: int
    primary: bool

    @property
    def label(self) -> str:
        suffix = " (primary)" if self.primary else ""
        return f"Monitor {self.index + 1} - {self.model}{suffix}"


def _enum_windows():
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32

    class RECT(ctypes.Structure):
        _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                    ("right", wintypes.LONG), ("bottom", wintypes.LONG)]

    class MONITORINFOEXW(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", RECT),
                    ("rcWork", RECT), ("dwFlags", wintypes.DWORD),
                    ("szDevice", wintypes.WCHAR * 32)]

    class DISPLAY_DEVICEW(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("DeviceName", wintypes.WCHAR * 32),
                    ("DeviceString", wintypes.WCHAR * 128), ("StateFlags", wintypes.DWORD),
                    ("DeviceID", wintypes.WCHAR * 128), ("DeviceKey", wintypes.WCHAR * 128)]

    MONITORENUMPROC = ctypes.WINFUNCTYPE(
        wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
        ctypes.POINTER(RECT), wintypes.LPARAM)

    raw = []

    def _callback(hmon, hdc, lprc, lparam):
        info = MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(MONITORINFOEXW)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(info)):
            r = info.rcMonitor
            raw.append({
                "device": info.szDevice,
                "x": r.left, "y": r.top,
                "w": r.right - r.left, "h": r.bottom - r.top,
                "primary": bool(info.dwFlags & _MONITORINFOF_PRIMARY),
            })
        return True

    user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(_callback), 0)

    # Resolve a model name per adapter device via the attached monitor child.
    def _model_for(adapter: str) -> str:
        dd = DISPLAY_DEVICEW()
        dd.cb = ctypes.sizeof(DISPLAY_DEVICEW)
        # iDevNum 0 = first monitor attached to that adapter
        if user32.EnumDisplayDevicesW(ctypes.c_wchar_p(adapter), 0, ctypes.byref(dd), 0):
            name = dd.DeviceString.strip()
            if name:
                return name
        # fall back to the adapter's own string
        dd2 = DISPLAY_DEVICEW()
        dd2.cb = ctypes.sizeof(DISPLAY_DEVICEW)
        if user32.EnumDisplayDevicesW(None, _adapter_index(adapter), ctypes.byref(dd2), 0):
            return dd2.DeviceString.strip() or "Display"
        return "Display"

    def _adapter_index(adapter: str) -> int:
        # "\\.\DISPLAY3" -> 2
        try:
            return int(adapter.rsplit("DISPLAY", 1)[1]) - 1
        except (IndexError, ValueError):
            return 0

    for entry in raw:
        entry["model"] = _model_for(entry["device"])
    return raw


def list_monitors() -> List[Monitor]:
    """Return the connected monitors, ordered left-to-right then top-to-bottom."""
    if sys.platform != "win32":
        raise OSError("monitor enumeration is only available on Windows")
    entries = _enum_windows()
    entries.sort(key=lambda e: (e["x"], e["y"]))
    return [
        Monitor(index=i, device_name=e["device"], model=e["model"],
                width=e["w"], height=e["h"], x=e["x"], y=e["y"], primary=e["primary"])
        for i, e in enumerate(entries)
    ]


def find_by_device(device_name: str) -> Optional[Monitor]:
    for m in list_monitors():
        if m.device_name == device_name:
            return m
    return None


if __name__ == "__main__":
    for mon in list_monitors():
        print(f"[{mon.index}] {mon.label}  device={mon.device_name}  "
              f"{mon.width}x{mon.height} @ ({mon.x},{mon.y})")
