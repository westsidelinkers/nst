import pytest
import os

pytestmark = pytest.mark.skipif(
    not (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY")),
    reason="No display available"
)

def test_expanded_import():
    from nst.ui.expanded import ExpandedPanel
    assert ExpandedPanel is not None

def test_expanded_creates_sections():
    from nst.ui.expanded import ExpandedPanel
    panel = ExpandedPanel()
    # Should have at least: hero, heartbeat, bars, latency, devices, actions
    assert hasattr(panel, "hero")
    assert hasattr(panel, "bars")
    assert hasattr(panel, "actions")
    assert hasattr(panel, "heartbeat")
    assert hasattr(panel, "latency")
    assert hasattr(panel, "devices")

def test_expanded_update_no_crash():
    from nst.ui.expanded import ExpandedPanel
    from nst.measurement.t0_passive import T0Sample
    from nst.measurement.verdict import Verdict
    from nst.measurement.t1_probe import ProbeResult
    panel = ExpandedPanel()
    sample = T0Sample(rx_bps=10e6, ping_avg_ms=20.0, signal_dbm=-60)
    panel.update(sample, Verdict.HEALTHY, ProbeResult(), [{"name": "router", "ip": "192.168.1.1", "status": "ok"}])
