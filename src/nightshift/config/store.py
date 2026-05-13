"""Load/save the user's settings as JSON in ``%APPDATA%\\nightshift\\config.json``.

``load()`` always returns a fully populated config - any missing keys are
filled in from :func:`default_config`, so older or hand-edited files keep
working when the schema grows. Unknown keys the user may have added are
preserved.
"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

SCHEMA_VERSION = 1
_APP_DIR_NAME = "nightshift"
_FILE_NAME = "config.json"

DEFAULT_DAY_K = 6500
DEFAULT_NIGHT_K = 3300
DEFAULT_LAT = 37.5665    # Seoul
DEFAULT_LON = 126.9780


def default_config() -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "per_monitor_enabled": False,
        "global": {"day_k": DEFAULT_DAY_K, "night_k": DEFAULT_NIGHT_K},
        "monitors": {},
        "schedule": {"manual": True, "night_start": "21:00", "day_start": "07:00"},
        "location": {"lat": DEFAULT_LAT, "lon": DEFAULT_LON},
        "toggles": {"autostart": False, "use_sunset": False, "disable_on_fullscreen": True},
        "extended_range": False,
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
    return _merge(default_config(), loaded)


def save(cfg: Mapping[str, Any]) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


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
            }
            changed = True
    return changed
