# nightshift

🌙 Windows multi-monitor color temperature controller. Set a different night-mode
temperature per display. Built with Python, ships as a single `.exe`.

> Status: early development. See `CLAUDE.md` and `cycles/` for the build log.

## Features
- Per-monitor day/night color temperature (3300K–6500K by default, 1500K with the opt-in extended range)
- Schedule with manual times or sunrise/sunset by latitude/longitude (`astral`, offline)
- 5-second linear fade between day and night, cancelled instantly when you grab a slider
- System-tray icon (open / pause / set night now / quit); closing the window minimises to the tray
- Run-at-startup (HKCU, no admin) and "pause while fullscreen app is in focus" toggles
- Planned: single-file `.exe` (no install) for Windows 10/11 — cycle-03

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
that deviate too far from linear, so by default the **visible warming saturates
around ~3300K** — the slider still goes to 2700K, but below ~3300K it doesn't get
visibly warmer. nightshift clamps the ramp so it's always accepted (no failures),
it just plateaus.

**Extended range (opt-in).** Setting the registry value
`HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ICM\GdiICMGammaRange = 256`
(DWORD) and **rebooting Windows** unlocks the full range down to ~1500K — verified
on Windows 11 with `scripts/probe_unclamped.py`. This needs admin once and a real
reboot, so nightshift will surface it as an in-app "Extended color range" toggle
(cycle-01) rather than requiring it up front. Same trick f.lux's installer does
silently during admin install.

Also turn off Windows **Night light**; it conflicts with gamma-ramp control.
