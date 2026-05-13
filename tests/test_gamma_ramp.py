from nightshift.color.gamma import RAMP_SIZE, build_gamma_ramp, identity_ramp


def test_ramp_shape():
    ramp = build_gamma_ramp(2700)
    assert len(ramp) == 3
    assert all(len(ch) == RAMP_SIZE for ch in ramp)


def test_values_within_16bit_range():
    for k in (1500, 2700, 4500, 6500):
        for ch in build_gamma_ramp(k):
            assert ch[0] == 0
            assert all(0 <= v <= 65535 for v in ch)


def test_each_channel_non_decreasing():
    for ch in build_gamma_ramp(3000):
        assert ch == sorted(ch)


def test_identity_ramp_is_neutral_full_range():
    ident = identity_ramp()
    for ch in ident:
        assert ch[0] == 0
        assert ch[-1] == 65535
    # 6500K is close to (but not exactly) the identity — green is ~0.976 in
    # the Tanner Helland approximation. Within ~3% of full scale is enough.
    near = build_gamma_ramp(6500, brightness=1.0)
    for ach, bch in zip(ident, near):
        assert abs(ach[-1] - bch[-1]) <= 0.03 * 65535


def test_warm_temperature_attenuates_blue_channel():
    warm = build_gamma_ramp(2700)
    neutral = build_gamma_ramp(6500)
    assert warm[2][-1] < neutral[2][-1]   # blue top end pulled down
    assert warm[0][-1] == neutral[0][-1]  # red untouched


def test_brightness_scales_all_channels():
    # without the Windows clamp, brightness uniformly scales the endpoints
    full = build_gamma_ramp(6500, brightness=1.0, clamp_to_windows_limit=False)
    half = build_gamma_ramp(6500, brightness=0.5, clamp_to_windows_limit=False)
    for fch, hch in zip(full, half):
        assert abs(hch[-1] - fch[-1] * 0.5) <= 1.0
    assert build_gamma_ramp(6500, brightness=0.0, clamp_to_windows_limit=False)[0][-1] == 0


def test_clamp_keeps_entries_within_windows_deviation_limit():
    from nightshift.color.gamma import RAMP_SIZE, _WORD_MAX, WINDOWS_GAMMA_DEVIATION_LIMIT
    for k in (1500, 2000, 2700, 3300, 6500):
        for ch in build_gamma_ramp(k):  # clamp on by default
            for i, v in enumerate(ch):
                linear = round((i / (RAMP_SIZE - 1)) * _WORD_MAX)
                assert abs(v - linear) <= WINDOWS_GAMMA_DEVIATION_LIMIT


def test_unclamped_warm_ramp_exceeds_the_limit():
    # sanity: this is *why* the clamp exists
    from nightshift.color.gamma import RAMP_SIZE, _WORD_MAX, WINDOWS_GAMMA_DEVIATION_LIMIT
    blue = build_gamma_ramp(2700, clamp_to_windows_limit=False)[2]
    worst = max(abs(v - round((i / (RAMP_SIZE - 1)) * _WORD_MAX)) for i, v in enumerate(blue))
    assert worst > WINDOWS_GAMMA_DEVIATION_LIMIT


def test_apply_kelvin_propagates_clamp_kwarg(monkeypatch):
    from nightshift.color import gamma

    seen: dict = {}

    def fake_build(kelvin, brightness=1.0, clamp_to_windows_limit=True):
        seen["clamp"] = clamp_to_windows_limit
        return [[0] * 256 for _ in range(3)]

    monkeypatch.setattr(gamma, "build_gamma_ramp", fake_build)
    monkeypatch.setattr(gamma, "_apply_ramp_to_device", lambda d, r: True)

    assert gamma.apply_kelvin("X", 2700, clamp_to_windows_limit=False) is True
    assert seen["clamp"] is False

    assert gamma.apply_kelvin("X", 2700) is True
    assert seen["clamp"] is True
