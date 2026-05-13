"""Load/save the user's settings as JSON in ``%APPDATA%\\nightshift\\config.json``.

``load()`` always returns a fully populated config - any missing keys are
filled in from :func:`default_config`, so older or hand-edited files keep
working when the schema grows. Unknown keys the user may have added are
preserved.

Schema v2 (cycle-04) adds:
- ``mode`` ("day" | "night" | "single") at the top level so the chosen mode
  persists across restarts.
- ``global.single_k`` and ``monitors[device].single_k`` for the always-on
  single-temperature mode.
- ``presets`` list with builtin seeds (Daylight / Halogen / Incandescent /
  Candle) — each preset has an optional ``default_k`` (applied to all
  devices that lack a specific entry) and a ``kelvins`` dict for per-device
  K values.
"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

SCHEMA_VERSION = 2
_APP_DIR_NAME = "nightshift"
_FILE_NAME = "config.json"

DEFAULT_DAY_K = 6500
DEFAULT_NIGHT_K = 3300
DEFAULT_SINGLE_K = 3300
DEFAULT_LAT = 37.5665    # Seoul
DEFAULT_LON = 126.9780

# (preset_name, default_k_for_all_devices)
_BUILTIN_PRESETS: List[tuple] = [
    ("주광 (6500K)", 6500),
    ("할로겐 (3400K)", 3400),
    ("백열등 (2700K)", 2700),
    ("촛불 (1900K)", 1900),
]


def _builtin_presets() -> List[Dict[str, Any]]:
    return [{"name": name, "default_k": k, "kelvins": {}}
            for name, k in _BUILTIN_PRESETS]


def default_config() -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "day",
        "per_monitor_enabled": False,
        "global": {"day_k": DEFAULT_DAY_K,
                    "night_k": DEFAULT_NIGHT_K,
                    "single_k": DEFAULT_SINGLE_K},
        "monitors": {},
        "schedule": {"manual": True, "night_start": "21:00", "day_start": "07:00"},
        "location": {"lat": DEFAULT_LAT, "lon": DEFAULT_LON},
        "toggles": {"autostart": False, "use_sunset": False, "disable_on_fullscreen": True},
        "extended_range": False,
        "presets": _builtin_presets(),
    }


def config_path() -> Path:
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / _APP_DIR_NAME / _FILE_NAME
    return Path.home() / f".{_APP_DIR_NAME}" / _FILE_NAME


def _merge(default: Mapping[str, Any], loaded: Mapping[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, dv in default.items():
        if k in loaded:
            lv = loaded[k]
            if isinstance(dv, dict) and isinstance(lv, dict):
                out[k] = _merge(dv, lv)
            else:
                out[k] = lv
        else:
            out[k] = deepcopy(dv)
    for k, lv in loaded.items():
        if k not in out:
            out[k] = lv
    return out


def _migrate_v1_to_v2(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Fill v2-only fields in a v1 config that's already been merged with v2 defaults.

    The merge step already filled in ``mode`` / ``global.single_k`` / ``presets``
    from :func:`default_config`. The remaining gap is per-monitor entries: each
    ``monitors[device]`` came verbatim from the v1 file, so it has ``day_k`` and
    ``night_k`` but no ``single_k``. We backfill it from the global default.
    """
    g_single = cfg["global"].get("single_k", DEFAULT_SINGLE_K)
    for entry in cfg.get("monitors", {}).values():
        if isinstance(entry, dict):
            entry.setdefault("single_k", g_single)
    cfg["schema_version"] = SCHEMA_VERSION
    return cfg


def load() -> Dict[str, Any]:
    path = config_path()
    if not path.exists():
        return default_config()
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_config()
    if not isinstance(loaded, dict):
        return default_config()
    cfg = _merge(default_config(), loaded)
    if int(cfg.get("schema_version", 1)) < SCHEMA_VERSION:
        cfg = _migrate_v1_to_v2(cfg)
    return cfg


def save(cfg: Mapping[str, Any]) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False),
                    encoding="utf-8")


def ensure_monitor_entries(cfg: Dict[str, Any], device_names: Iterable[str]) -> bool:
    """Insert default per-monitor entries for any device not yet in ``cfg``.

    Returns True if ``cfg`` was mutated, so the caller can decide whether to
    persist.
    """
    changed = False
    for d in device_names:
        if d not in cfg["monitors"]:
            cfg["monitors"][d] = {
                "day_k": cfg["global"]["day_k"],
                "night_k": cfg["global"]["night_k"],
                "single_k": cfg["global"].get("single_k", DEFAULT_SINGLE_K),
            }
            changed = True
    return changed
