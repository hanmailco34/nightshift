from datetime import datetime, timedelta, timezone

import pytest

from nightshift.config import store
from nightshift.schedule import engine


def _cfg(use_sunset: bool = False,
         day_start: str = "07:00", night_start: str = "21:00") -> dict:
    cfg = store.default_config()
    cfg["toggles"]["use_sunset"] = use_sunset
    cfg["schedule"]["day_start"] = day_start
    cfg["schedule"]["night_start"] = night_start
    return cfg


def _dt(h: int, m: int) -> datetime:
    return datetime(2026, 5, 13, h, m)


@pytest.mark.parametrize("hh,mm,expected", [
    (6, 59, "night"),
    (7, 0, "day"),
    (12, 0, "day"),
    (20, 59, "day"),
    (21, 0, "night"),
    (23, 30, "night"),
    (2, 0, "night"),
])
def test_manual_mode_standard_window(hh, mm, expected):
    assert engine.current_target_mode(_dt(hh, mm), _cfg()) == expected


def test_manual_mode_inverted_window():
    # Unusual: day_start > night_start. Night spans [night_start, day_start);
    # day is the wraparound. Documenting current behavior so it doesn't drift.
    cfg = _cfg(day_start="21:00", night_start="07:00")
    assert engine.current_target_mode(_dt(12, 0), cfg) == "night"
    assert engine.current_target_mode(_dt(22, 0), cfg) == "day"
    assert engine.current_target_mode(_dt(3, 0), cfg) == "day"


def test_next_transition_manual_today():
    nt = engine.next_transition(_dt(12, 0), _cfg())
    assert nt == _dt(21, 0)


def test_next_transition_manual_crosses_midnight():
    nt = engine.next_transition(_dt(22, 0), _cfg())
    assert nt == datetime(2026, 5, 14, 7, 0)


def _seoul_sun_factory():
    tz = timezone(timedelta(hours=9))

    def fake_sun(d, lat, lon, tz_name="Asia/Seoul"):
        return {
            "sunrise": datetime(d.year, d.month, d.day, 6, 0, tzinfo=tz),
            "sunset": datetime(d.year, d.month, d.day, 19, 0, tzinfo=tz),
        }
    return fake_sun


def test_astral_mode_uses_wrapper(monkeypatch):
    monkeypatch.setattr(engine, "_astral_sun_for_date", _seoul_sun_factory())
    cfg = _cfg(use_sunset=True)
    assert engine.current_target_mode(_dt(6, 30), cfg) == "day"
    assert engine.current_target_mode(_dt(18, 59), cfg) == "day"
    assert engine.current_target_mode(_dt(19, 1), cfg) == "night"
    assert engine.current_target_mode(_dt(5, 30), cfg) == "night"


def test_next_transition_astral(monkeypatch):
    monkeypatch.setattr(engine, "_astral_sun_for_date", _seoul_sun_factory())
    cfg = _cfg(use_sunset=True)
    nt = engine.next_transition(_dt(12, 0), cfg)
    assert nt.hour == 19 and nt.minute == 0
    nt2 = engine.next_transition(_dt(20, 0), cfg)
    assert nt2.date() == datetime(2026, 5, 14).date()
    assert nt2.hour == 6 and nt2.minute == 0


def test_interp_sequence_endpoints_and_length():
    seq = engine.interp_sequence(6500, 2700, steps=20)
    assert len(seq) == 21
    assert seq[0] == 6500
    assert seq[-1] == 2700


def test_interp_sequence_monotone_for_descending():
    seq = engine.interp_sequence(6500, 2700, steps=20)
    for a, b in zip(seq, seq[1:]):
        assert a >= b


def test_interp_sequence_monotone_for_ascending():
    seq = engine.interp_sequence(2700, 6500, steps=20)
    for a, b in zip(seq, seq[1:]):
        assert a <= b


def test_interp_sequence_zero_steps():
    assert engine.interp_sequence(6500, 2700, steps=0) == [2700]


def test_kelvin_for_mode_per_monitor_off():
    class FakeCtrl:
        per_monitor_enabled = False
        monitors = {"\\\\.\\D1": {"day_k": 6000, "night_k": 2000}}
        global_targets = {"day_k": 6500, "night_k": 3300}
    assert engine._kelvin_for_mode(FakeCtrl(), "\\\\.\\D1", "night") == 3300


def test_kelvin_for_mode_per_monitor_on_falls_back_for_unknown():
    class FakeCtrl:
        per_monitor_enabled = True
        monitors = {"\\\\.\\D1": {"day_k": 6000, "night_k": 2000}}
        global_targets = {"day_k": 6500, "night_k": 3300}
    assert engine._kelvin_for_mode(FakeCtrl(), "\\\\.\\D1", "night") == 2000
    assert engine._kelvin_for_mode(FakeCtrl(), "\\\\.\\D2", "night") == 3300


def test_scheduler_skips_evaluation_in_single_mode():
    class FakeCtrl:
        mode = "single"
        extended_range = False
        per_monitor_enabled = False
        monitors: dict = {}
        global_targets = {"day_k": 6500, "night_k": 3300, "single_k": 3300}

    triggered: list = []

    sched = engine.Scheduler(
        FakeCtrl(),
        get_devices=lambda: ["\\\\.\\D1"],
        root=None,
        get_cfg=_cfg,
    )
    sched._begin_transition = lambda target: triggered.append(target)  # type: ignore[method-assign]
    sched._evaluate_once()
    assert triggered == []


def test_scheduler_evaluates_in_day_or_night_mode():
    class FakeCtrl:
        mode = "day"
        extended_range = False
        per_monitor_enabled = False
        monitors: dict = {}
        global_targets = {"day_k": 6500, "night_k": 3300, "single_k": 3300}

    triggered: list = []

    # Inverted-schedule trick to make "night" the target at virtually any
    # real wall-clock time without mocking datetime.now():
    # day_t (23:59) > night_t (00:00) → night spans [00:00, 23:59).
    sched = engine.Scheduler(
        FakeCtrl(),
        get_devices=lambda: ["\\\\.\\D1"],
        root=None,
        get_cfg=lambda: _cfg(night_start="00:00", day_start="23:59"),
    )
    sched._begin_transition = lambda target: triggered.append(target)  # type: ignore[method-assign]
    sched._evaluate_once()
    assert triggered == ["night"]
