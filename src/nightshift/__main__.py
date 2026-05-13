"""Entry point. For now (cycle-00) this just runs a diagnostic dump;
the tkinter UI is wired up in cycle-01."""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    try:
        from .display.monitors import list_monitors
    except OSError as exc:
        print(f"nightshift: {exc}")
        return 1

    print(f"nightshift {__import__('nightshift').__version__} - detected monitors:")
    for mon in list_monitors():
        print(f"  [{mon.index}] {mon.label}  device={mon.device_name}  "
              f"{mon.width}x{mon.height} @ ({mon.x},{mon.y})")
    print("\n(UI arrives in cycle-01; use `python -m nightshift.color.gamma --help` "
          "for the color-control smoke test.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
