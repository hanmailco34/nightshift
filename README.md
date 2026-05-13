# nightshift

🌙 Windows multi-monitor color temperature controller. Set a different night-mode
temperature per display. Built with Python, ships as a single `.exe`.

> Status: early development. See `CLAUDE.md` and `cycles/` for the build log.

## Features
- Per-monitor day/night color temperature (3300K–6500K by default, 1500K with the opt-in extended range)
- Schedule with manual times or sunrise/sunset by latitude/longitude (`astral`, offline)
- 5-second linear fade between day and night, cancelled instantly when you grab a slider
- System-tray icon (open / pause / set night now / quit); closing the window minimises to the tray
- Run-at-startup (HKCU, no admin) and "pause while a fullscreen app is in focus" toggles
- Single-file `.exe` (~32 MB, no install) for Windows 10/11

## Download
Grab the latest `nightshift.exe` from the [Releases page](https://github.com/hanmailco34/nightshift/releases/latest)
and double-click. There's no installer — settings live in
`%APPDATA%\nightshift\config.json` and nothing else is touched until you
flip the "Run at Windows startup" toggle.

**First-run warning.** Because the build isn't signed with a paid code
certificate, Windows will show a "Windows protected your PC" SmartScreen
dialog the first time you run it. Click **More info → Run anyway** — that's
a one-time prompt.

**Can't see the tray icon?** Windows 11 groups new tray icons under the
**^** arrow in the system tray. Click it, then drag the nightshift icon
onto the taskbar so it stays visible.

## Dev setup
```sh
pip install -e .
pip install -r requirements-dev.txt

python -m nightshift                # launch the UI + tray
python -m nightshift --diagnose     # print detected monitors and exit
python -m pytest                    # run the test suite
```

### Build the .exe locally
```sh
python scripts/make_icon.py         # regenerate assets/nightshift.ico (only if you changed it)
pyinstaller --clean --noconfirm nightshift.spec
# -> dist/nightshift.exe
```
GitHub Actions runs the same command on every `v*.*.*` tag push and uploads
the resulting `nightshift.exe` to a Releases entry — see
`.github/workflows/release.yml`.

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
