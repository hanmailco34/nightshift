# nightshift

🌙 Windows multi-monitor color temperature controller. Set a different night-mode
temperature per display. Built with Python, ships as a single `.exe`.

> Status: early development. See `CLAUDE.md` and `cycles/` for the build log.

## Features (planned)
- Per-monitor day/night color temperature (2700K–6500K)
- Automatic switching on a schedule (or manual sunrise/sunset by latitude/longitude)
- System-tray background operation, run-at-startup, disable-on-fullscreen
- Single-file `.exe` (no install), Windows 10/11

## Dev setup
```sh
pip install -e .
python -m nightshift                       # diagnostic: list detected monitors
python -m nightshift.color.gamma --list    # list monitors (index + GDI device)
python -m nightshift.color.gamma --apply 0 3300   # warm monitor index 0 to 3300K
python -m nightshift.color.gamma --reset          # restore all monitors
python -m pytest
```

## Known limitation — Windows gamma clamp
Color control uses the GPU gamma ramp (`SetDeviceGammaRamp`). Windows rejects ramps
that deviate too far from linear, so **out of the box the warmest reachable value is
~3300K**. To go warmer (e.g. 2700K), set this registry value (as Administrator) and
reboot:

```
HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ICM
  GdiICMGammaRange  (DWORD) = 256
```

A future build will offer a one-click "extended range" setup for this. Also turn off
Windows **Night light** — it conflicts with gamma-ramp adjustment.
