"""Generate ``assets/nightshift.ico``.

Yellow disc at multiple sizes (16/32/48/256) saved as a single multi-resolution
ICO file, matching the in-memory tray icon in ``ui.tray._make_icon_image``.

Re-run this script if you change the design; commit the resulting .ico
(small binary, ~50KB) so the PyInstaller build doesn't have to regenerate it.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

OUTPUT = Path(__file__).resolve().parent.parent / "assets" / "nightshift.ico"
COLOR = (255, 213, 102, 255)
SIZES = [16, 32, 48, 256]


def make_disc(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pad = max(1, size // 10)
    ImageDraw.Draw(img).ellipse(
        (pad, pad, size - pad - 1, size - pad - 1), fill=COLOR)
    return img


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    largest = make_disc(max(SIZES))
    largest.save(OUTPUT, format="ICO",
                  sizes=[(s, s) for s in SIZES])
    size_b = OUTPUT.stat().st_size
    print(f"wrote {OUTPUT} ({size_b} bytes, sizes {SIZES})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
