"""Apply a color temperature to a display via the Windows gamma ramp.

The heavy lifting on Windows is ``SetDeviceGammaRamp`` (gdi32). We build a
256-entry-per-channel ramp where each channel is an otherwise-linear ramp
scaled by the white-point multiplier for the requested Kelvin value.

The pure ramp-building helpers work on any platform (so they can be unit
tested); the functions that actually touch ``gdi32`` raise ``OSError`` if
called off Windows.
"""

from __future__ import annotations

import sys
from typing import List, Sequence

from .temperature import kelvin_to_rgb

RAMP_SIZE = 256
_WORD_MAX = 65535

# Windows (Vista+) rejects a gamma ramp if any entry deviates more than
# ~0x8000 from the linear value ``i / 255 * 65535``. We clamp slightly inside
# that so warm temperatures degrade gracefully (the tint visually plateaus
# around ~3300K) instead of SetDeviceGammaRamp failing outright.
WINDOWS_GAMMA_DEVIATION_LIMIT = 32000


def build_gamma_ramp(kelvin: float, brightness: float = 1.0,
                     clamp_to_windows_limit: bool = True) -> List[List[int]]:
    """Return ``[red, green, blue]``, each a list of 256 WORD values.

    ``brightness`` (0..1) uniformly scales every channel; 1.0 is full.
    6500K at brightness 1.0 is approximately (but not exactly) the identity
    ramp; for an exact "no correction" reset use :func:`identity_ramp`.

    When ``clamp_to_windows_limit`` is true (default) every entry is kept
    within :data:`WINDOWS_GAMMA_DEVIATION_LIMIT` of the linear ramp so the
    OS will accept it; the visible warming therefore saturates near ~3300K.
    """
    r_mul, g_mul, b_mul = kelvin_to_rgb(kelvin)
    b = 0.0 if brightness < 0.0 else 1.0 if brightness > 1.0 else brightness
    limit = WINDOWS_GAMMA_DEVIATION_LIMIT
    channels = []
    for mul in (r_mul * b, g_mul * b, b_mul * b):
        channel = []
        for i in range(RAMP_SIZE):
            linear = (i / (RAMP_SIZE - 1)) * _WORD_MAX
            value = int(round(linear * mul))
            if clamp_to_windows_limit:
                lo = int(round(linear)) - limit
                hi = int(round(linear)) + limit
                if value < lo:
                    value = lo
                elif value > hi:
                    value = hi
            channel.append(0 if value < 0 else _WORD_MAX if value > _WORD_MAX else value)
        channels.append(channel)
    return channels


def identity_ramp() -> List[List[int]]:
    """The ramp that represents 'no correction' (6500K, full brightness)."""
    return [
        [int(round((i / (RAMP_SIZE - 1)) * _WORD_MAX)) for i in range(RAMP_SIZE)]
        for _ in range(3)
    ]


# --------------------------------------------------------------------------
# Windows-only plumbing
# --------------------------------------------------------------------------

def _require_windows():
    if sys.platform != "win32":
        raise OSError("gamma ramp control is only available on Windows")


def _ramp_to_ctypes(ramp: Sequence[Sequence[int]]):
    import ctypes

    arr = (ctypes.c_ushort * RAMP_SIZE * 3)()
    for ch in range(3):
        for i in range(RAMP_SIZE):
            arr[ch][i] = ctypes.c_ushort(ramp[ch][i])
    return arr


def _create_display_dc(device_name: str | None):
    """HDC for ``device_name`` (e.g. ``\\\\.\\DISPLAY1``) or the primary screen."""
    import ctypes

    gdi32 = ctypes.windll.gdi32
    gdi32.CreateDCW.restype = ctypes.c_void_p
    hdc = gdi32.CreateDCW(ctypes.c_wchar_p("DISPLAY"),
                          ctypes.c_wchar_p(device_name) if device_name else None,
                          None, None)
    if not hdc:
        raise OSError(f"CreateDC failed for device {device_name!r}")
    return hdc


def _set_ramp_on_dc(hdc, ramp) -> bool:
    import ctypes

    gdi32 = ctypes.windll.gdi32
    gdi32.SetDeviceGammaRamp.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    arr = _ramp_to_ctypes(ramp)
    return bool(gdi32.SetDeviceGammaRamp(hdc, ctypes.byref(arr)))


def apply_kelvin(device_name: str | None, kelvin: float, brightness: float = 1.0) -> bool:
    """Apply ``kelvin`` to one display. Returns True on success.

    ``device_name`` is a value from :func:`nightshift.display.monitors.list_monitors`
    (``\\\\.\\DISPLAYn``); ``None`` targets the primary display device context.
    """
    _require_windows()
    import ctypes

    hdc = _create_display_dc(device_name)
    try:
        return _set_ramp_on_dc(hdc, build_gamma_ramp(kelvin, brightness))
    finally:
        ctypes.windll.gdi32.DeleteDC(ctypes.c_void_p(hdc))


def reset(device_name: str | None) -> bool:
    """Restore the identity (uncorrected) ramp for one display."""
    _require_windows()
    import ctypes

    hdc = _create_display_dc(device_name)
    try:
        return _set_ramp_on_dc(hdc, identity_ramp())
    finally:
        ctypes.windll.gdi32.DeleteDC(ctypes.c_void_p(hdc))


# --------------------------------------------------------------------------
# CLI smoke test:  python -m nightshift.color.gamma --list
#                  python -m nightshift.color.gamma --apply 0 2700
#                  python -m nightshift.color.gamma --reset
# --------------------------------------------------------------------------

def _main(argv: list[str]) -> int:
    from ..display.monitors import list_monitors

    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        print("usage: --list | --apply <index> <kelvin> | --reset")
        return 0

    cmd = argv[0]
    mons = list_monitors()

    if cmd == "--list":
        for idx, m in enumerate(mons):
            print(f"[{idx}] {m.label}  device={m.device_name}  "
                  f"{m.width}x{m.height}{'  (primary)' if m.primary else ''}")
        return 0

    if cmd == "--apply":
        index, kelvin = int(argv[1]), float(argv[2])
        target = mons[index]
        ok = apply_kelvin(target.device_name, kelvin)
        print(f"apply {kelvin:.0f}K to {target.label}: {'OK' if ok else 'FAILED'}")
        return 0 if ok else 1

    if cmd == "--reset":
        rc = 0
        for m in mons:
            ok = reset(m.device_name)
            print(f"reset {m.label}: {'OK' if ok else 'FAILED'}")
            rc = rc or (0 if ok else 1)
        return rc

    print(f"unknown command: {cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
