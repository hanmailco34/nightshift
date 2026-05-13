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
that deviate too far from linear, so the **visible warming saturates around ~3300K** —
the slider still goes to 2700K, but below ~3300K it doesn't get visibly warmer.
nightshift clamps the ramp so it's always accepted (no failures), it just plateaus.

The often-cited registry workaround
(`HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ICM\GdiICMGammaRange = 256`,
DWORD, then reboot) had **no effect** on the test machine (Windows 11) — your mileage
may vary. Also turn off Windows **Night light**; it conflicts with gamma-ramp control.
