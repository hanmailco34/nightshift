from nightshift.color.temperature import kelvin_to_rgb


def test_neutral_daylight_is_roughly_white():
    r, g, b = kelvin_to_rgb(6500)
    assert r == 1.0
    assert 0.95 <= g <= 1.0
    assert 0.95 <= b <= 1.0


def test_warm_temperatures_drop_blue():
    _, _, b_2700 = kelvin_to_rgb(2700)
    _, _, b_4000 = kelvin_to_rgb(4000)
    assert 0.0 <= b_2700 < b_4000 < 1.0


def test_red_is_always_full_at_or_below_6600k():
    for k in (1500, 2700, 4000, 5500, 6500):
        r, _, _ = kelvin_to_rgb(k)
        assert r == 1.0


def test_channels_clamped_to_unit_interval():
    for k in (500, 1000, 2700, 6500, 10000, 40000, 100000):
        for ch in kelvin_to_rgb(k):
            assert 0.0 <= ch <= 1.0


def test_monotonic_blue_with_temperature():
    temps = [2000, 2700, 3500, 4500, 5500, 6500]
    blues = [kelvin_to_rgb(t)[2] for t in temps]
    assert blues == sorted(blues)
