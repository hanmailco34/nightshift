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
    full = build_gamma_ramp(6500, brightness=1.0)
    half = build_gamma_ramp(6500, brightness=0.5)
    for fch, hch in zip(full, half):
        assert abs(hch[-1] - fch[-1] * 0.5) <= 1.0
    assert build_gamma_ramp(6500, brightness=0.0)[0][-1] == 0
