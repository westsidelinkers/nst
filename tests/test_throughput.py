from nst.measurement.throughput import parse_proc_net_dev, compute_rate, InterfaceCounters

SAMPLE = """Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
    lo: 1595452051 1335868    0    0    0     0          0         0 1595452051 1335868    0    0    0     0       0          0
enp1s0:       0       0    0    0    0     0          0         0        0       0    0    0    0     0       0          0
wlp2s0: 2929680012 3258313    0 2623    0     0          0         0 1911208594 2340685    0    0    0     0       0          0
"""

def test_parse_proc_net_dev():
    result = parse_proc_net_dev(SAMPLE)
    assert "wlp2s0" in result
    assert result["wlp2s0"].rx_bytes == 2929680012
    assert result["wlp2s0"].tx_bytes == 1911208594
    assert result["wlp2s0"].rx_dropped == 2623
    assert result["lo"].rx_bytes == 1595452051
    assert "enp1s0" in result

def test_compute_rate_normal():
    prev = InterfaceCounters(rx_bytes=1000, tx_bytes=500, rx_dropped=0, rx_errors=0, rx_packets=10, tx_packets=5, tx_dropped=0, tx_errors=0)
    curr = InterfaceCounters(rx_bytes=2000, tx_bytes=1500, rx_dropped=2, rx_errors=0, rx_packets=20, tx_packets=15, tx_dropped=0, tx_errors=0)
    r = compute_rate(prev, curr, 1.0)
    assert r.valid is True
    assert r.rx_bps == 1000.0
    assert r.tx_bps == 1000.0
    assert r.rx_dropped_rate == 2.0

def test_compute_rate_counter_reset():
    prev = InterfaceCounters(rx_bytes=2929680012, tx_bytes=1911208594, rx_dropped=2623, rx_errors=0, rx_packets=0, tx_packets=0, tx_dropped=0, tx_errors=0)
    curr = InterfaceCounters(rx_bytes=100, tx_bytes=50, rx_dropped=0, rx_errors=0, rx_packets=0, tx_packets=0, tx_dropped=0, tx_errors=0)
    r = compute_rate(prev, curr, 1.0)
    assert r.valid is False

def test_compute_rate_zero_elapsed():
    prev = InterfaceCounters(rx_bytes=1000, tx_bytes=500, rx_dropped=0, rx_errors=0, rx_packets=0, tx_packets=0, tx_dropped=0, tx_errors=0)
    curr = InterfaceCounters(rx_bytes=2000, tx_bytes=1500, rx_dropped=0, rx_errors=0, rx_packets=0, tx_packets=0, tx_dropped=0, tx_errors=0)
    r = compute_rate(prev, curr, 0.0)
    assert r.valid is False

def test_compute_rate_first_sample():
    r = compute_rate(None, InterfaceCounters(rx_bytes=1000, tx_bytes=500, rx_dropped=0, rx_errors=0, rx_packets=0, tx_packets=0, tx_dropped=0, tx_errors=0), 1.0)
    assert r.valid is False