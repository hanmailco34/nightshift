"""Thin orchestration between the UI and :mod:`nightshift.color.gamma`.

Holds the desired day/night kelvin per monitor, the current mode, and the
``extended_range`` flag. ``apply_current`` is the one path the UI calls to
push the current state to the OS.

All OS calls go through ``gamma.apply_kelvin`` / ``gamma.reset`` (module
attribute access on purpose, so tests can monkeypatch them).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Literal, Mapping, Optional

from . import gamma

Mode = Literal["day", "night"]


@dataclass
class Controller:
    mode: Mode = "day"
    extended_range: bool = False
    per_monitor_enabled: bool = False
    monitors: Dict[str, Dict[str, int]] = field(default_factory=dict)
    global_targets: Dict[str, int] = field(
        default_factory=lambda: {"day_k": 6500, "night_k": 3300})

    def target_for(self, device_name: str) -> int:
        key = f"{self.mode}_k"
        if self.per_monitor_enabled and device_name in self.monitors:
            return int(self.monitors[device_name][key])
        return int(self.global_targets[key])

    def apply_current(self, device_names: Iterable[str]) -> List[str]:
        """Apply the current mode/kelvin to each device.

        Returns the list of devices where ``apply_kelvin`` returned False or
        raised :class:`OSError` (e.g. HDR display, driver refusal).
        """
        failed: List[str] = []
        clamp = not self.extended_range
        for d in device_names:
            try:
                ok = gamma.apply_kelvin(d, self.target_for(d),
                                        clamp_to_windows_limit=clamp)
            except OSError:
                ok = False
            if not ok:
                failed.append(d)
        return failed

    def reset_all(self, device_names: Iterable[str]) -> List[str]:
        failed: List[str] = []
        for d in device_names:
            try:
                ok = gamma.reset(d)
            except OSError:
                ok = False
            if not ok:
                failed.append(d)
        return failed

    def set_mode(self, mode: Mode) -> None:
        self.mode = mode

    def set_temperature(self, device: Optional[str], target_mode: Mode,
                        kelvin: int) -> None:
        key = f"{target_mode}_k"
        if device is None:
            self.global_targets[key] = int(kelvin)
        else:
            entry = self.monitors.setdefault(device, dict(self.global_targets))
            entry[key] = int(kelvin)

    def set_extended_range(self, enabled: bool) -> None:
        self.extended_range = bool(enabled)

    def set_per_monitor_enabled(self, enabled: bool) -> None:
        self.per_monitor_enabled = bool(enabled)


def from_config(cfg: Mapping[str, Any]) -> Controller:
    """Build a Controller from a config dict (see :mod:`nightshift.config.store`)."""
    c = Controller()
    c.per_monitor_enabled = bool(cfg.get("per_monitor_enabled", False))
    c.extended_range = bool(cfg.get("extended_range", False))
    g = cfg.get("global", {}) or {}
    c.global_targets["day_k"] = int(g.get("day_k", c.global_targets["day_k"]))
    c.global_targets["night_k"] = int(g.get("night_k", c.global_targets["night_k"]))
    c.monitors = {
        k: {"day_k": int(v.get("day_k", c.global_targets["day_k"])),
            "night_k": int(v.get("night_k", c.global_targets["night_k"]))}
        for k, v in (cfg.get("monitors") or {}).items()
    }
    return c
