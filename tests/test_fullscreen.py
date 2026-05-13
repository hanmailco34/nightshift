from dataclasses import dataclass

from nightshift.platform import fullscreen


@dataclass
class _Mon:
    x: int
    y: int
    width: int
    height: int


def test_rect_matches_monitor_exact():
    m = _Mon(0, 0, 1920, 1080)
    assert fullscreen._rect_matches_monitor((0, 0, 1920, 1080), m) is True


def test_rect_matches_monitor_within_tolerance():
    m = _Mon(0, 0, 1920, 1080)
    assert fullscreen._rect_matches_monitor((-1, 1, 1921, 1079), m) is True
    assert fullscreen._rect_matches_monitor((2, -2, 1918, 1082), m) is True


def test_rect_matches_monitor_outside_tolerance():
    m = _Mon(0, 0, 1920, 1080)
    assert fullscreen._rect_matches_monitor((5, 0, 1920, 1080), m) is False
    assert fullscreen._rect_matches_monitor((0, 0, 1920, 1085), m) is False
    assert fullscreen._rect_matches_monitor((0, 0, 1280, 720), m) is False


def test_rect_matches_offset_monitor():
    m = _Mon(1920, 0, 1440, 900)
    assert fullscreen._rect_matches_monitor((1920, 0, 3360, 900), m) is True
    assert fullscreen._rect_matches_monitor((0, 0, 1440, 900), m) is False


def test_is_fullscreen_visible_filters_shell_classes(monkeypatch):
    monkeypatch.setattr(fullscreen, "_foreground_class_name",
                         lambda: "Progman")
    monkeypatch.setattr(fullscreen, "_get_foreground_rect",
                         lambda: (0, 0, 1920, 1080))
    assert fullscreen.is_fullscreen_app_visible([_Mon(0, 0, 1920, 1080)]) is False


def test_is_fullscreen_visible_matches_any_monitor(monkeypatch):
    monkeypatch.setattr(fullscreen, "_foreground_class_name",
                         lambda: "GameOverlay")
    monkeypatch.setattr(fullscreen, "_get_foreground_rect",
                         lambda: (1920, 0, 3360, 900))
    monitors = [_Mon(0, 0, 1920, 1080), _Mon(1920, 0, 1440, 900)]
    assert fullscreen.is_fullscreen_app_visible(monitors) is True


def test_is_fullscreen_visible_normal_window(monkeypatch):
    monkeypatch.setattr(fullscreen, "_foreground_class_name",
                         lambda: "Notepad")
    monkeypatch.setattr(fullscreen, "_get_foreground_rect",
                         lambda: (100, 100, 1000, 800))
    assert fullscreen.is_fullscreen_app_visible([_Mon(0, 0, 1920, 1080)]) is False


def test_is_fullscreen_visible_no_rect(monkeypatch):
    monkeypatch.setattr(fullscreen, "_foreground_class_name",
                         lambda: "GameOverlay")
    monkeypatch.setattr(fullscreen, "_get_foreground_rect", lambda: None)
    assert fullscreen.is_fullscreen_app_visible([_Mon(0, 0, 1920, 1080)]) is False
