import pytest
import os

pytestmark = pytest.mark.skipif(
    not (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY")),
    reason="No display available"
)

def test_heartbeat_import():
    from nst.ui.heartbeat import HeartbeatGraph
    assert HeartbeatGraph is not None

def test_heartbeat_sample_buffer():
    from nst.ui.heartbeat import HeartbeatGraph
    g = HeartbeatGraph()
    g.add_sample(38.1)
    g.add_sample(35.2)
    assert len(g.samples) == 2
    assert g.samples[-1] == 35.2

def test_heartbeat_ring_buffer():
    from nst.ui.heartbeat import HeartbeatGraph
    g = HeartbeatGraph(max_samples=5)
    for i in range(10):
        g.add_sample(float(i))
    assert len(g.samples) == 5
    assert g.samples[0] == 5.0
