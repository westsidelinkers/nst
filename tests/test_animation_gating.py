import os
import pytest

pytestmark = pytest.mark.skipif(
    not (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY")),
    reason="No display available",
)

def test_animations_disabled_reduced_motion():
    from nst.ui.css import animations_enabled
    assert animations_enabled(reduced_motion=True, on_battery=False, battery_pct=100) is False

def test_animations_disabled_low_battery():
    from nst.ui.css import animations_enabled
    assert animations_enabled(reduced_motion=False, on_battery=True, battery_pct=10, battery_threshold=30) is False

def test_animations_enabled_combined_requires_both():
    from nst.ui.css import animations_enabled
    # reduced motion alone disables
    assert animations_enabled(reduced_motion=True, on_battery=True, battery_pct=5) is False
    # on battery but above threshold enables
    assert animations_enabled(reduced_motion=False, on_battery=True, battery_pct=80, battery_threshold=30) is True
    # ac power enables
    assert animations_enabled(reduced_motion=False, on_battery=False, battery_pct=5, battery_threshold=30) is True
