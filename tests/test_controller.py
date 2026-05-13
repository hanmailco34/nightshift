from nightshift.color import controller, gamma
from nightshift.config import store


def test_apply_current_sends_mode_kelvin_with_clamp(monkeypatch):
    calls = []
    monkeypatch.setattr(gamma, "apply_kelvin",
                        lambda d, k, clamp_to_windows_limit: (
                            calls.append((d, k, clamp_to_windows_limit)) or True))

    c = controller.Controller(mode="night", extended_range=False)
    c.global_targets = {"day_k": 6500, "night_k": 3300}
    assert c.apply_current(["\\\\.\\DISPLAY1", "\\\\.\\DISPLAY2"]) == []
    assert calls == [
        ("\\\\.\\DISPLAY1", 3300, True),
        ("\\\\.\\DISPLAY2", 3300, True),
    ]


def test_extended_range_disables_clamp(monkeypatch):
    captured = []
    monkeypatch.setattr(gamma, "apply_kelvin",
                        lambda d, k, clamp_to_windows_limit: (
                            captured.append(clamp_to_windows_limit) or True))
    c = controller.Controller(mode="day", extended_range=True)
    c.apply_current(["\\\\.\\DISPLAY1"])
    assert captured == [False]


def test_per_monitor_overrides_take_precedence(monkeypatch):
    # extended_range=True so the visual floor doesn't clamp the test K values.
    seen = []
    monkeypatch.setattr(gamma, "apply_kelvin",
                        lambda d, k, clamp_to_windows_limit: (
                            seen.append((d, k)) or True))
    c = controller.Controller(mode="night", per_monitor_enabled=True,
                                extended_range=True)
    c.global_targets = {"day_k": 6500, "night_k": 3300}
    c.monitors["\\\\.\\DISPLAY1"] = {"day_k": 6000, "night_k": 2000}
    c.apply_current(["\\\\.\\DISPLAY1", "\\\\.\\DISPLAY2"])
    assert seen == [("\\\\.\\DISPLAY1", 2000), ("\\\\.\\DISPLAY2", 3300)]


def test_per_monitor_disabled_uses_global(monkeypatch):
    seen = []
    monkeypatch.setattr(gamma, "apply_kelvin",
                        lambda d, k, clamp_to_windows_limit: (
                            seen.append((d, k)) or True))
    c = controller.Controller(mode="night", per_monitor_enabled=False,
                                extended_range=True)
    c.global_targets = {"day_k": 6500, "night_k": 3300}
    c.monitors["\\\\.\\DISPLAY1"] = {"day_k": 6000, "night_k": 2000}
    c.apply_current(["\\\\.\\DISPLAY1"])
    assert seen == [("\\\\.\\DISPLAY1", 3300)]


def test_visual_floor_clamps_when_extended_range_off(monkeypatch):
    """Raw K stays in controller; OS-applied K is floored to 3300K."""
    seen = []
    monkeypatch.setattr(gamma, "apply_kelvin",
                        lambda d, k, clamp_to_windows_limit: (
                            seen.append((d, k)) or True))
    c = controller.Controller(mode="night", extended_range=False)
    c.global_targets = {"day_k": 6500, "night_k": 1900, "single_k": 3300}
    c.apply_current(["\\\\.\\DISPLAY1"])
    # raw target is 1900; effective (applied) is 3300 (CLAMPED_VISUAL_FLOOR_K).
    assert seen == [("\\\\.\\DISPLAY1", 3300)]
    assert c.target_for("\\\\.\\DISPLAY1") == 1900   # raw preserved
    assert c.effective_target_for("\\\\.\\DISPLAY1") == 3300


def test_visual_floor_lifts_when_extended_range_on(monkeypatch):
    seen = []
    monkeypatch.setattr(gamma, "apply_kelvin",
                        lambda d, k, clamp_to_windows_limit: (
                            seen.append((d, k)) or True))
    c = controller.Controller(mode="night", extended_range=True)
    c.global_targets = {"day_k": 6500, "night_k": 1900, "single_k": 3300}
    c.apply_current(["\\\\.\\DISPLAY1"])
    # 1900 >= UNCLAMPED floor (1500), so it goes through.
    assert seen == [("\\\\.\\DISPLAY1", 1900)]


def test_failed_devices_are_reported(monkeypatch):
    monkeypatch.setattr(
        gamma, "apply_kelvin",
        lambda d, k, clamp_to_windows_limit: d != "\\\\.\\DISPLAY2")
    c = controller.Controller(mode="day")
    assert c.apply_current(["\\\\.\\DISPLAY1", "\\\\.\\DISPLAY2"]) == ["\\\\.\\DISPLAY2"]


def test_oserror_counts_as_failure(monkeypatch):
    def raises(d, k, clamp_to_windows_limit):
        raise OSError("HDR or driver refusal")
    monkeypatch.setattr(gamma, "apply_kelvin", raises)
    c = controller.Controller(mode="day")
    assert c.apply_current(["\\\\.\\DISPLAY1"]) == ["\\\\.\\DISPLAY1"]


def test_set_temperature_writes_to_correct_target():
    c = controller.Controller()
    c.set_temperature(None, "night", 2800)
    assert c.global_targets["night_k"] == 2800
    c.set_temperature("\\\\.\\DISPLAY1", "day", 6200)
    assert c.monitors["\\\\.\\DISPLAY1"]["day_k"] == 6200


def test_reset_all_calls_gamma_reset(monkeypatch):
    called = []
    monkeypatch.setattr(gamma, "reset", lambda d: called.append(d) or True)
    c = controller.Controller()
    assert c.reset_all(["\\\\.\\DISPLAY1", "\\\\.\\DISPLAY2"]) == []
    assert called == ["\\\\.\\DISPLAY1", "\\\\.\\DISPLAY2"]


def test_from_config_populates_controller():
    cfg = store.default_config()
    cfg["per_monitor_enabled"] = True
    cfg["extended_range"] = True
    cfg["global"]["night_k"] = 2700
    cfg["monitors"]["\\\\.\\DISPLAY1"] = {"day_k": 6000, "night_k": 2000,
                                           "single_k": 4500}

    c = controller.from_config(cfg)
    assert c.per_monitor_enabled is True
    assert c.extended_range is True
    assert c.global_targets["night_k"] == 2700
    assert c.global_targets["single_k"] == store.DEFAULT_SINGLE_K
    assert c.monitors["\\\\.\\DISPLAY1"] == {"day_k": 6000, "night_k": 2000,
                                              "single_k": 4500}


def test_from_config_reads_mode_field():
    cfg = store.default_config()
    cfg["mode"] = "single"
    c = controller.from_config(cfg)
    assert c.mode == "single"


def test_target_for_single_mode_uses_single_k(monkeypatch):
    c = controller.Controller(mode="single")
    c.global_targets = {"day_k": 6500, "night_k": 3300, "single_k": 4200}
    assert c.target_for("\\\\.\\D1") == 4200


def test_target_for_single_mode_per_monitor_override(monkeypatch):
    c = controller.Controller(mode="single", per_monitor_enabled=True)
    c.global_targets = {"day_k": 6500, "night_k": 3300, "single_k": 4200}
    c.monitors["\\\\.\\D1"] = {"day_k": 6000, "night_k": 2000, "single_k": 4800}
    assert c.target_for("\\\\.\\D1") == 4800
    # D2 not in monitors → fallback to global
    assert c.target_for("\\\\.\\D2") == 4200


def test_set_temperature_writes_single_k():
    c = controller.Controller(mode="single")
    c.set_temperature(None, "single", 4700)
    assert c.global_targets["single_k"] == 4700

    c.set_temperature("\\\\.\\D1", "single", 5100)
    assert c.monitors["\\\\.\\D1"]["single_k"] == 5100


def test_apply_current_in_single_mode_passes_single_k(monkeypatch):
    seen = []
    monkeypatch.setattr(gamma, "apply_kelvin",
                        lambda d, k, clamp_to_windows_limit: (
                            seen.append((d, k)) or True))
    c = controller.Controller(mode="single")
    c.global_targets = {"day_k": 6500, "night_k": 3300, "single_k": 4400}
    c.apply_current(["\\\\.\\D1", "\\\\.\\D2"])
    assert seen == [("\\\\.\\D1", 4400), ("\\\\.\\D2", 4400)]
