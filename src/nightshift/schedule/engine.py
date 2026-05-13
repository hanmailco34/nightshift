"""Drive the day/night mode transition in the background.

Two modes:
- **manual**: ``config.schedule.day_start`` / ``night_start`` (HH:MM strings).
- **astral**: sunrise / sunset for ``config.location.lat,lon`` via the
  ``astral`` package.

The switch is ``config.toggles.use_sunset`` (true = astral, false = manual).

A mode change schedules a 5-second linear K interpolation on the tk main
thread; :meth:`Scheduler.cancel_transition` aborts the remainder, e.g. when
the user drags a slider mid-fade. The 30-second tick runs on a daemon
thread and only ever calls :meth:`tkinter.Tk.after`; the controller and
``gamma.apply_kelvin`` are therefore always touched from the tk thread.
"""

from __future__ import annotations

import threading
from datetime import date, datetime, time, timedelta
from typing import Callable, Iterable, List, Literal, Mapping, Optional

from ..color import gamma

Mode = Literal["day", "night"]

TICK_SECONDS = 30
INTERP_DURATION_MS = 5000
INTERP_STEPS = 20


# --------------------------------------------------------------------------
# Pure functions (mode classification + next-boundary lookup)
# --------------------------------------------------------------------------

def _parse_hhmm(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


def _manual_mode(now: datetime, cfg: Mapping) -> Mode:
    sched = cfg.get("schedule", {})
    day_t = _parse_hhmm(sched.get("day_start", "07:00"))
    night_t = _parse_hhmm(sched.get("night_start", "21:00"))
    cur = now.time()
    if day_t <= night_t:
        return "day" if day_t <= cur < night_t else "night"
    # inverted (night_start < day_start): night spans [night_t, day_t)
    return "night" if night_t <= cur < day_t else "day"


def _astral_sun_for_date(d: date, lat: float, lon: float,
                          tz_name: str = "Asia/Seoul") -> dict:
    """Thin wrapper around ``astral.sun.sun`` for easy monkeypatching."""
    from astral import LocationInfo
    from astral.sun import sun
    info = LocationInfo(latitude=lat, longitude=lon, timezone=tz_name)
    return sun(info.observer, date=d, tzinfo=info.timezone)


def _astral_mode(now: datetime, cfg: Mapping) -> Mode:
    loc = cfg.get("location", {})
    s = _astral_sun_for_date(now.date(),
                              float(loc.get("lat", 37.5665)),
                              float(loc.get("lon", 126.9780)))
    sunrise, sunset = s["sunrise"], s["sunset"]
    if sunrise.tzinfo is not None and now.tzinfo is None:
        now = now.replace(tzinfo=sunrise.tzinfo)
    return "night" if (now >= sunset or now < sunrise) else "day"


def current_target_mode(now: datetime, cfg: Mapping) -> Mode:
    if cfg.get("toggles", {}).get("use_sunset", False):
        return _astral_mode(now, cfg)
    return _manual_mode(now, cfg)


def _next_manual(now: datetime, cfg: Mapping) -> datetime:
    sched = cfg.get("schedule", {})
    day_t = _parse_hhmm(sched.get("day_start", "07:00"))
    night_t = _parse_hhmm(sched.get("night_start", "21:00"))
    today = now.date()
    cands = [
        datetime.combine(today, day_t),
        datetime.combine(today, night_t),
        datetime.combine(today + timedelta(days=1), day_t),
        datetime.combine(today + timedelta(days=1), night_t),
    ]
    return min(c for c in cands if c > now)


def _next_astral(now: datetime, cfg: Mapping) -> datetime:
    loc = cfg.get("location", {})
    lat = float(loc.get("lat", 37.5665))
    lon = float(loc.get("lon", 126.9780))
    today = _astral_sun_for_date(now.date(), lat, lon)
    tom = _astral_sun_for_date(now.date() + timedelta(days=1), lat, lon)
    cands = [today["sunrise"], today["sunset"],
             tom["sunrise"], tom["sunset"]]
    if cands[0].tzinfo is not None and now.tzinfo is None:
        now = now.replace(tzinfo=cands[0].tzinfo)
    return min(c for c in cands if c > now)


def next_transition(now: datetime, cfg: Mapping) -> datetime:
    if cfg.get("toggles", {}).get("use_sunset", False):
        return _next_astral(now, cfg)
    return _next_manual(now, cfg)


def interp_sequence(start_k: int, end_k: int,
                    steps: int = INTERP_STEPS) -> List[int]:
    """Inclusive linear K sequence: ``steps + 1`` points from start to end."""
    if steps <= 0:
        return [int(end_k)]
    return [int(round(start_k + (end_k - start_k) * i / steps))
            for i in range(steps + 1)]


def _kelvin_for_mode(controller, device_name: str, mode: Mode) -> int:
    """Read the K a device would have in ``mode`` without mutating ``controller``."""
    key = f"{mode}_k"
    if controller.per_monitor_enabled and device_name in controller.monitors:
        return int(controller.monitors[device_name][key])
    return int(controller.global_targets[key])


# --------------------------------------------------------------------------
# Scheduler
# --------------------------------------------------------------------------

class Scheduler:
    def __init__(self, controller, get_devices: Callable[[], Iterable[str]],
                 root, get_cfg: Callable[[], Mapping],
                 interp_steps: int = INTERP_STEPS,
                 interp_duration_ms: int = INTERP_DURATION_MS,
                 tick_seconds: int = TICK_SECONDS,
                 on_mode_change: Optional[Callable[[Mode], None]] = None):
        self.controller = controller
        self.get_devices = get_devices
        self.root = root
        self.get_cfg = get_cfg
        self.interp_steps = interp_steps
        self.interp_duration_ms = interp_duration_ms
        self.tick_seconds = tick_seconds
        self.on_mode_change = on_mode_change

        self._thread: Optional[threading.Thread] = None
        self._stop_evt = threading.Event()
        self._paused = False
        self._token_lock = threading.Lock()
        self._transition_token = 0

    # ---- public lifecycle -------------------------------------------------
    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_evt.clear()
        self._thread = threading.Thread(target=self._run, daemon=True,
                                         name="nightshift-scheduler")
        self._thread.start()

    def stop(self) -> None:
        self._stop_evt.set()

    def pause(self) -> None:
        self._paused = True
        self.cancel_transition()

    def resume(self) -> None:
        self._paused = False
        self.root.after(0, self._evaluate_once)

    def cancel_transition(self) -> None:
        with self._token_lock:
            self._transition_token += 1  # invalidates pending after callbacks

    def begin_transition_now(self, target: Mode) -> None:
        """Public hook (e.g. tray 'Set night now')."""
        self._begin_transition(target)

    # ---- internal --------------------------------------------------------
    def _run(self) -> None:
        # Tick loop: every TICK_SECONDS evaluate target mode on tk thread.
        while not self._stop_evt.wait(self.tick_seconds):
            if self._paused:
                continue
            self.root.after(0, self._evaluate_once)

    def _evaluate_once(self) -> None:
        if self._paused:
            return
        cfg = self.get_cfg()
        target = current_target_mode(datetime.now(), cfg)
        if self.controller.mode != target:
            self._begin_transition(target)

    def _begin_transition(self, target: Mode) -> None:
        with self._token_lock:
            self._transition_token += 1
            token = self._transition_token

        devices = list(self.get_devices())
        if not devices:
            self.controller.mode = target
            return

        starts = {d: _kelvin_for_mode(self.controller, d, self.controller.mode)
                  for d in devices}
        ends = {d: _kelvin_for_mode(self.controller, d, target)
                for d in devices}
        seqs = {d: interp_sequence(starts[d], ends[d], self.interp_steps)
                for d in devices}
        step_ms = max(1, self.interp_duration_ms // max(1, self.interp_steps))
        clamp = not self.controller.extended_range

        def step(i: int) -> None:
            with self._token_lock:
                if token != self._transition_token:
                    return  # cancelled / superseded
            for d in devices:
                try:
                    gamma.apply_kelvin(d, seqs[d][i],
                                        clamp_to_windows_limit=clamp)
                except OSError:
                    pass
            if i >= self.interp_steps:
                self.controller.mode = target
                if self.on_mode_change is not None:
                    try:
                        self.on_mode_change(target)
                    except Exception:
                        pass
                return
            self.root.after(step_ms, lambda: step(i + 1))

        step(0)
