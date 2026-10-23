from dataclasses import dataclass
from enum import Enum


class Verdict(Enum):
    HEALTHY = "HEALTHY"
    ISP_LIMITED = "ISP_LIMITED"
    RADIO_DEGRADED = "RADIO_DEGRADED"
    HIGH_LATENCY = "HIGH_LATENCY"


@dataclass
class VerdictSignals:
    throughput_mbps: float | None = None
    ping_avg_ms: float = 0.0
    jitter_ms: float = 0.0
    signal_dbm: float = 0.0
    rx_dropped_rate: float = 0.0
    retransmits: int = 0
    beacon_loss: int = 0
    bufferbloat_lan_ms: float = 0.0
    bufferbloat_wan_ms: float = 0.0


def compute_verdict(signals: VerdictSignals) -> Verdict:
    s = signals

    # 1. RADIO_DEGRADED (highest severity)
    if (
        s.signal_dbm < -75
        or s.rx_dropped_rate > 1.0
        or s.retransmits > 0
        or s.beacon_loss > 0
    ):
        return Verdict.RADIO_DEGRADED

    # 2. HIGH_LATENCY
    throughput_ok_for_latency = s.throughput_mbps is None or s.throughput_mbps >= 15
    if throughput_ok_for_latency and (
        s.ping_avg_ms > 50
        or s.jitter_ms > 20
        or s.bufferbloat_lan_ms > 10
    ):
        return Verdict.HIGH_LATENCY

    # 3. ISP_LIMITED
    if (
        s.throughput_mbps is not None
        and s.throughput_mbps < 30
        and s.signal_dbm >= -75
        and s.retransmits == 0
        and s.beacon_loss == 0
        and s.rx_dropped_rate <= 0.2
        and s.bufferbloat_wan_ms <= 5
    ):
        return Verdict.ISP_LIMITED

    # 4. HEALTHY (default)
    return Verdict.HEALTHY
