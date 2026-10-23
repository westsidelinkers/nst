from nst.measurement.verdict import compute_verdict, VerdictSignals, Verdict


def test_healthy():
    s = VerdictSignals(throughput_mbps=35.0, ping_avg_ms=12.0, jitter_ms=1.1,
                       signal_dbm=-65, rx_dropped_rate=0.05, retransmits=0,
                       beacon_loss=0, bufferbloat_lan_ms=5.0, bufferbloat_wan_ms=0.4)
    assert compute_verdict(s) == Verdict.HEALTHY


def test_isp_limited():
    s = VerdictSignals(throughput_mbps=10.0, ping_avg_ms=12.0, jitter_ms=1.1,
                       signal_dbm=-70, rx_dropped_rate=0.07, retransmits=0,
                       beacon_loss=0, bufferbloat_lan_ms=5.0, bufferbloat_wan_ms=0.4)
    assert compute_verdict(s) == Verdict.ISP_LIMITED


def test_radio_degraded_signal():
    s = VerdictSignals(throughput_mbps=35.0, ping_avg_ms=12.0, jitter_ms=1.1,
                       signal_dbm=-80, rx_dropped_rate=0.05, retransmits=0,
                       beacon_loss=0, bufferbloat_lan_ms=5.0, bufferbloat_wan_ms=0.4)
    assert compute_verdict(s) == Verdict.RADIO_DEGRADED


def test_radio_degraded_retransmits():
    s = VerdictSignals(throughput_mbps=35.0, ping_avg_ms=12.0, jitter_ms=1.1,
                       signal_dbm=-70, rx_dropped_rate=0.05, retransmits=5,
                       beacon_loss=0, bufferbloat_lan_ms=5.0, bufferbloat_wan_ms=0.4)
    assert compute_verdict(s) == Verdict.RADIO_DEGRADED


def test_high_latency():
    s = VerdictSignals(throughput_mbps=35.0, ping_avg_ms=80.0, jitter_ms=25.0,
                       signal_dbm=-70, rx_dropped_rate=0.05, retransmits=0,
                       beacon_loss=0, bufferbloat_lan_ms=5.0, bufferbloat_wan_ms=0.4)
    assert compute_verdict(s) == Verdict.HIGH_LATENCY


def test_high_latency_bufferbloat():
    s = VerdictSignals(throughput_mbps=35.0, ping_avg_ms=12.0, jitter_ms=1.1,
                       signal_dbm=-70, rx_dropped_rate=0.05, retransmits=0,
                       beacon_loss=0, bufferbloat_lan_ms=15.0, bufferbloat_wan_ms=0.4)
    assert compute_verdict(s) == Verdict.HIGH_LATENCY


def test_precedence_radio_over_latency():
    s = VerdictSignals(throughput_mbps=35.0, ping_avg_ms=80.0, jitter_ms=25.0,
                       signal_dbm=-80, rx_dropped_rate=0.05, retransmits=0,
                       beacon_loss=0, bufferbloat_lan_ms=5.0, bufferbloat_wan_ms=0.4)
    assert compute_verdict(s) == Verdict.RADIO_DEGRADED


def test_no_probe_cold_start():
    s = VerdictSignals(throughput_mbps=None, ping_avg_ms=12.0, jitter_ms=1.1,
                       signal_dbm=-70, rx_dropped_rate=0.05, retransmits=0,
                       beacon_loss=0, bufferbloat_lan_ms=5.0, bufferbloat_wan_ms=0.4)
    assert compute_verdict(s) == Verdict.HEALTHY  # throughput unknown, but radio/latency OK
