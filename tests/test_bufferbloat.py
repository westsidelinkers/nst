from nst.measurement.bufferbloat import compute_bufferbloat, BufferbloatResult


def test_compute_bufferbloat():
    result = compute_bufferbloat(
        baseline_lan=1.073, loaded_lan=40.947,
        baseline_wan=30.401, loaded_wan=30.809
    )
    assert result.delta_lan_ms == 39.874
    assert result.delta_wan_ms == 0.408
    assert result.success is True


def test_compute_bufferbloat_negative_delta():
    # If loaded < baseline (shouldn't happen but handle gracefully)
    result = compute_bufferbloat(
        baseline_lan=10.0, loaded_lan=5.0,
        baseline_wan=20.0, loaded_wan=18.0
    )
    assert result.delta_lan_ms == -5.0
    assert result.success is True
