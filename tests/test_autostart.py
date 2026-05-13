import sys

from nightshift.config import store
from nightshift.platform import autostart


def test_command_for_dev_uses_python_m(monkeypatch):
    monkeypatch.setattr(sys, "executable", r"C:\Python312\python.exe")
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    cmd = autostart._command()
    assert "python.exe" in cmd
    assert cmd.endswith(' -m nightshift')


def test_command_for_frozen_returns_exe_only(monkeypatch):
    monkeypatch.setattr(sys, "executable", r"C:\Program Files\nightshift\nightshift.exe")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    cmd = autostart._command()
    assert cmd == '"C:\\Program Files\\nightshift\\nightshift.exe"'


def _install_fake_store(monkeypatch):
    state = {"value": None}
    monkeypatch.setattr(autostart, "_read_value", lambda: state["value"])
    monkeypatch.setattr(autostart, "_write_value",
                         lambda v: state.__setitem__("value", v))
    monkeypatch.setattr(autostart, "_delete_value",
                         lambda: state.__setitem__("value", None))
    return state


def test_register_then_is_registered(monkeypatch):
    state = _install_fake_store(monkeypatch)
    assert autostart.is_registered() is False
    autostart.register()
    assert autostart.is_registered() is True
    assert state["value"] is not None and "nightshift" in state["value"]


def test_unregister_clears_value(monkeypatch):
    state = _install_fake_store(monkeypatch)
    autostart.register()
    autostart.unregister()
    assert autostart.is_registered() is False
    assert state["value"] is None


def test_unregister_when_not_registered_is_noop(monkeypatch):
    _install_fake_store(monkeypatch)
    autostart.unregister()
    assert autostart.is_registered() is False


def test_sync_with_config_registers_when_enabled(monkeypatch):
    _install_fake_store(monkeypatch)
    cfg = store.default_config()
    cfg["toggles"]["autostart"] = True
    autostart.sync_with_config(cfg)
    assert autostart.is_registered() is True


def test_sync_with_config_unregisters_when_disabled(monkeypatch):
    _install_fake_store(monkeypatch)
    cfg = store.default_config()
    autostart.register()
    cfg["toggles"]["autostart"] = False
    autostart.sync_with_config(cfg)
    assert autostart.is_registered() is False
