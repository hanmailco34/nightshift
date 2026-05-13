"""Color-temperature (Kelvin) to RGB white-point conversion.

Uses the well-known Tanner Helland approximation of black-body radiation,
which is the same family of curves f.lux / Redshift use. The result is a
per-channel multiplier in the range [0.0, 1.0] that can be applied to an
otherwise-linear gamma ramp.

Reference: https://tannerhelland.com/2012/09/18/convert-temperature-rgb-algorithm-code.html
"""

from __future__ import annotations

import math
from typing import Tuple

# Below this the approximation is not defined; clamp instead.
_MIN_TEMP = 1000
_MAX_TEMP = 40000


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def kelvin_to_rgb(kelvin: float) -> Tuple[float, float, float]:
    """Return (r, g, b) white-point multipliers in [0, 1] for ``kelvin``.

    6500K maps to approximately (1, 1, 1) — i.e. no tint, the neutral
    daylight white point. Lower temperatures shift towards warm orange/red.
    """
    temp = max(_MIN_TEMP, min(_MAX_TEMP, float(kelvin))) / 100.0

    # Red
    if temp <= 66:
        red = 255.0
    else:
        red = 329.698727446 * ((temp - 60) ** -0.1332047592)

    # Green
    if temp <= 66:
        green = 99.4708025861 * math.log(temp) - 161.1195681661
    else:
        green = 288.1221695283 * ((temp - 60) ** -0.0755148492)

    # Blue
    if temp >= 66:
        blue = 255.0
    elif temp <= 19:
        blue = 0.0
    else:
        blue = 138.5177312231 * math.log(temp - 10) - 305.0447927307

    return (_clamp01(red / 255.0), _clamp01(green / 255.0), _clamp01(blue / 255.0))
