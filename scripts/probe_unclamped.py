"""Probe whether SetDeviceGammaRamp accepts unclamped warm ramps after reboot.

Tries kelvins 3300, 3000, 2700, 2000, 1500 on the primary monitor, *without*
the Windows deviation clamp. Prints OK/FAIL per kelvin. Always resets at end.
"""
from __future__ import annotations

import ctypes
import time
from ctypes import wintypes

from nightshift.color.gamma import build_gamma_ramp, identity_ramp
from nightshift.display.monitors import list_monitors


def _set_ramp(device_name: str, ramp) -> bool:
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    CreateDCW = gdi32.CreateDCW
    CreateDCW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_void_p]
    CreateDCW.restype = wintypes.HDC
    DeleteDC = gdi32.DeleteDC
    DeleteDC.argtypes = [wintypes.HDC]
    DeleteDC.restype = wintypes.BOOL
    SetDeviceGammaRamp = gdi32.SetDeviceGammaRamp
    SetDeviceGammaRamp.argtypes = [wintypes.HDC, ctypes.c_void_p]
    SetDeviceGammaRamp.restype = wintypes.BOOL

    Buf = (ctypes.c_uint16 * 256 * 3)
    buf = Buf()
    for ci, ch in enumerate(ramp):
        for i, v in enumerate(ch):
            buf[ci][i] = v
    hdc = CreateDCW("DISPLAY", device_name, None, None)
    if not hdc:
        return False
    try:
        return bool(SetDeviceGammaRamp(hdc, ctypes.byref(buf)))
    finally:
        DeleteDC(hdc)


def main() -> int:
    mons = list_monitors()
    target = next((m for m in mons if m.primary), mons[0])
    print(f"target: {target.device_name}  ({target.label})")
    try:
        for k in (3300, 3000, 2700, 2000, 1500):
            ramp = build_gamma_ramp(k, clamp_to_windows_limit=False)
            ok = _set_ramp(target.device_name, ramp)
            print(f"  apply {k}K  (unclamped) -> {'OK' if ok else 'FAIL'}  (holding 2.5s)")
            time.sleep(2.5)
    finally:
        _set_ramp(target.device_name, identity_ramp())
        print("  reset to identity")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
