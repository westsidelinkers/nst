from dataclasses import dataclass


@dataclass
class InterfaceCounters:
    rx_bytes: int = 0
    tx_bytes: int = 0
    rx_dropped: int = 0
    rx_errors: int = 0
    rx_packets: int = 0
    tx_packets: int = 0
    tx_dropped: int = 0
    tx_errors: int = 0


@dataclass
class ThroughputResult:
    rx_bps: float = 0.0
    tx_bps: float = 0.0
    rx_dropped_rate: float = 0.0
    valid: bool = False


def parse_proc_net_dev(text: str) -> dict[str, InterfaceCounters]:
    result: dict[str, InterfaceCounters] = {}
    lines = text.splitlines()
    # Skip the two header lines.
    data_lines = lines[2:]
    for line in data_lines:
        if not line.strip():
            continue
        if ":" not in line:
            continue
        name, rest = line.rsplit(":", 1)
        name = name.strip()
        if not name:
            continue
        tokens = rest.split()
        if len(tokens) < 16:
            continue
        counters = InterfaceCounters(
            rx_bytes=int(tokens[0]),
            rx_packets=int(tokens[1]),
            rx_errors=int(tokens[2]),
            rx_dropped=int(tokens[3]),
            tx_bytes=int(tokens[8]),
            tx_packets=int(tokens[9]),
            tx_errors=int(tokens[10]),
            tx_dropped=int(tokens[11]),
        )
        result[name] = counters
    return result


def compute_rate(prev, curr: InterfaceCounters, elapsed_s: float) -> ThroughputResult:
    if prev is None:
        return ThroughputResult(valid=False)
    if elapsed_s is None or elapsed_s <= 0:
        return ThroughputResult(valid=False)
    if curr.rx_bytes < prev.rx_bytes:
        return ThroughputResult(valid=False)
    rx_bps = (curr.rx_bytes - prev.rx_bytes) / elapsed_s
    tx_bps = (curr.tx_bytes - prev.tx_bytes) / elapsed_s
    rx_dropped_rate = (curr.rx_dropped - prev.rx_dropped) / elapsed_s
    return ThroughputResult(
        rx_bps=rx_bps,
        tx_bps=tx_bps,
        rx_dropped_rate=rx_dropped_rate,
        valid=True,
    )