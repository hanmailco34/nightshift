"""Entry point. Launches the tkinter UI by default; ``--diagnose`` prints the
detected monitor list (the cycle-00 behavior)."""

from __future__ import annotations

import sys


def _diagnose() -> int:
    try:
        from .display.monitors import list_monitors
    except OSError as exc:
        print(f"nightshift: {exc}")
        return 1

    print(f"nightshift {__import__('nightshift').__version__} - detected monitors:")
    for mon in list_monitors():
        print(f"  [{mon.index}] {mon.label}  device={mon.device_name}  "
              f"{mon.width}x{mon.height} @ ({mon.x},{mon.y})")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "--diagnose":
        return _diagnose()
    from .ui.main_window import run
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
