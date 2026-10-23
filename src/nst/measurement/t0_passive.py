import re
import threading
import time
import subprocess
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

try:
    import gi
    gi.require_version("GLib", "2.0")
    from gi.repository import GLib
except Exception:  # pragma: no cover - environment dependent
    GLib = None

from nst.measurement.throughput import parse_proc_net_dev, compute_rate


def parse_iw_link(text: str) -> dict:
    result: dict[str, Any] = {}
    m = re.search(r"SSID:\s*(.+)", text)
    if m:
        result["ssid"] = m.group(1).strip()
    m = re.search(r"freq:\s*([\d.]+)", text)
    if m:
        result["freq_mhz"] = float(m.group(1))
    m = re.search(r"signal:\s*(-?\d+)\s*dBm", text)
    if m:
        result["signal_dbm"] = int(m.group(1))
    m = re.search(r"rx bitrate:\s*([\d.]+)\s*MBit/s", text, re.IGNORECASE)
    if m:
        result["rx_bitrate_mbps"] = float(m.group(1))
    m = re.search(r"tx bitrate:\s*([\d.]+)\s*MBit/s", text, re.IGNORECASE)
    if m:
        result["tx_bitrate_mbps"] = float(m.group(1))
    # Optional byte counters if present.
    m = re.search(r"RX:\s*(\d+)\s*bytes", text)
    if m:
        result["rx_bytes"] = int(m.group(1))
    m = re.search(r"TX:\s*(\d+)\s*bytes", text)
    if m:
        result["tx_bytes"] = int(m.group(1))
    return result


def parse_ping_output(text: str) -> dict:
    result: dict[str, Any] = {}
    m = re.search(r"(\d+)\s+packets transmitted,\s*(\d+)\s+received", text)
    if m:
        result["transmitted"] = int(m.group(1))
        result["received"] = int(m.group(2))
    m = re.search(r"([\d.]+)%\s*packet loss", text)
    if m:
        result["loss_pct"] = float(m.group(1))
    m = re.search(r"rtt min/avg/max/(?:mdev|stddev)\s*=\s*([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)", text)
    if m:
        result["min_ms"] = float(m.group(1))
        result["avg_ms"] = float(m.group(2))
        result["max_ms"] = float(m.group(3))
        result["mdev_ms"] = float(m.group(4))
    # Alternate summary line wording.
    if "avg_ms" not in result:
        m = re.search(r"round-trip min/avg/max/stddev\s*=\s*([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)", text)
        if m:
            result["min_ms"] = float(m.group(1))
            result["avg_ms"] = float(m.group(2))
            result["max_ms"] = float(m.group(3))
            result["mdev_ms"] = float(m.group(4))
    if "loss_pct" not in result:
        result["loss_pct"] = 0.0
    return result


def parse_iw_station_dump(text: str) -> dict:
    result: dict[str, Any] = {}
    m = re.search(r"tx retries:\s*(\d+)", text)
    if m:
        result["tx_retries"] = int(m.group(1))
    m = re.search(r"tx failed:\s*(\d+)", text)
    if m:
        result["tx_failed"] = int(m.group(1))
    m = re.search(r"beacon loss:\s*(\d+)", text)
    if m:
        result["beacon_loss"] = int(m.group(1))
    m = re.search(r"rx drop misc:\s*(\d+)", text)
    if m:
        result["rx_drop_misc"] = int(m.group(1))
    m = re.search(r"signal:\s*(-?\d+)\s*\[", text)
    if not m:
        m = re.search(r"^\s*signal:\s*(-?\d+)", text, re.MULTILINE)
    if m:
        result["signal_dbm"] = int(m.group(1))
    m = re.search(r"signal avg:\s*(-?\d+)", text)
    if m:
        result["signal_avg_dbm"] = int(m.group(1))
    return result


@dataclass
class T0Sample:
    timestamp: float = 0.0
    rx_bps: float = 0.0
    tx_bps: float = 0.0
    ping_avg_ms: float = 0.0
    ping_max_ms: float = 0.0
    ping_loss_pct: float = 0.0
    jitter_ms: float = 0.0
    dns_ms: float = 0.0
    tcp_connect_ms: float = 0.0
    tls_ms: float = 0.0
    ttfb_ms: float = 0.0
    signal_dbm: float = 0.0
    rx_dropped_rate: float = 0.0
    rx_dropped_total: int = 0
    battery_pct: float = 0.0
    battery_health_pct: float = 0.0
    on_battery: bool = False
    cpu_temp_c: float = 0.0
    public_ip: Optional[str] = None
    ipv6_global: Optional[str] = None


class T0Monitor:
    def __init__(
        self,
        config: Any = None,
        interface: Optional[str] = None,
        interval: Optional[float] = None,
        interval_seconds: Optional[float] = None,
        t0_interval_seconds: Optional[float] = None,
        ping_target: str = "1.1.1.1",
        **_kwargs: Any,
    ) -> None:
        self.config = config
        if interface is None and config is not None:
            interface = getattr(config, "interface", None)
        self.interface = interface or "wlp2s0"
        if interval is None:
            interval = interval_seconds
        if interval is None:
            interval = t0_interval_seconds
        if interval is None and config is not None:
            interval = getattr(config, "t0_interval_seconds", None)
        if interval is None:
            interval = 2
        self.interval = float(interval)
        self.ping_target = ping_target

        self._lock = threading.Lock()
        self._latest: Optional[T0Sample] = None
        self._callback: Optional[Callable[[T0Sample], Any]] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        self._paused_flag = False
        self._probe_in_flight_flag = False

        self._prev_counters: Any = None
        self._prev_time: Optional[float] = None

    # --- pause / probe handling ---
    @property
    def paused(self) -> bool:
        return self._paused_flag

    @paused.setter
    def paused(self, value: bool) -> None:
        self._paused_flag = bool(value)
        if self._paused_flag:
            self._reset_prev()

    @property
    def is_paused(self) -> bool:
        return self._paused_flag

    @is_paused.setter
    def is_paused(self, value: bool) -> None:
        self.paused = value

    @property
    def probe_in_flight(self) -> bool:
        return self._probe_in_flight_flag

    @probe_in_flight.setter
    def probe_in_flight(self, value: bool) -> None:
        new = bool(value)
        if new and not self._probe_in_flight_flag:
            self._reset_prev()
        self._probe_in_flight_flag = new

    @property
    def is_probe_in_flight(self) -> bool:
        return self._probe_in_flight_flag

    @is_probe_in_flight.setter
    def is_probe_in_flight(self, value: bool) -> None:
        self.probe_in_flight = value

    def _reset_prev(self) -> None:
        with self._lock:
            self._prev_counters = None
            self._prev_time = None

    def pause(self) -> None:
        self.paused = True

    def resume(self) -> None:
        self.paused = False

    def pause_for_probe(self) -> None:
        self.probe_in_flight = True

    def resume_from_probe(self) -> None:
        self.probe_in_flight = False

    def set_probe_in_flight(self, value: bool) -> None:
        self.probe_in_flight = value

    # --- public API ---
    def start(self, callback: Callable[[T0Sample], Any]) -> None:
        self._callback = callback
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=5)
        self._thread = None

    def get_latest(self) -> Optional[T0Sample]:
        with self._lock:
            return self._latest

    # --- worker ---
    def _run(self) -> None:
        while not self._stop_event.is_set():
            if self.paused or self.probe_in_flight:
                self._reset_prev()
                self._stop_event.wait(max(self.interval, 0.05))
                continue
            try:
                sample = self._collect()
            except Exception:
                sample = T0Sample(timestamp=time.time())
            with self._lock:
                self._latest = sample
            cb = self._callback
            if cb is not None:
                if GLib is not None:
                    try:
                        GLib.idle_add(cb, sample)
                    except Exception:
                        try:
                            cb(sample)
                        except Exception:
                            pass
                else:
                    try:
                        cb(sample)
                    except Exception:
                        pass
            self._stop_event.wait(max(self.interval, 0.01))

    def _collect(self) -> T0Sample:
        sample = T0Sample(timestamp=time.time())

        # Throughput from /proc/net/dev.
        try:
            with open("/proc/net/dev", "r") as f:
                text = f.read()
            counters_map = parse_proc_net_dev(text)
            curr = counters_map.get(self.interface)
            now = time.monotonic()
            if curr is not None:
                with self._lock:
                    prev = self._prev_counters
                    prev_time = self._prev_time
                if prev is not None and prev_time is not None:
                    elapsed = now - prev_time
                    rate = compute_rate(prev, curr, elapsed)
                    if rate.valid:
                        sample.rx_bps = rate.rx_bps
                        sample.tx_bps = rate.tx_bps
                        sample.rx_dropped_rate = rate.rx_dropped_rate
                sample.rx_dropped_total = int(getattr(curr, "rx_dropped", 0))
                with self._lock:
                    self._prev_counters = curr
                    self._prev_time = now
        except Exception:
            pass

        # iw link.
        try:
            res = subprocess.run(
                ["iw", "dev", self.interface, "link"],
                timeout=10,
                capture_output=True,
                text=True,
            )
            if res.returncode == 0:
                out = res.stdout if isinstance(res.stdout, str) else ""
                info = parse_iw_link(out)
                if "ssid" in info:
                    pass
                if "signal_dbm" in info:
                    sample.signal_dbm = float(info["signal_dbm"])
        except Exception:
            pass

        # ping.
        try:
            res = subprocess.run(
                ["ping", "-c", "3", "-W", "1", self.ping_target],
                timeout=10,
                capture_output=True,
                text=True,
            )
            if res.returncode in (0, 1):
                _out = res.stdout if isinstance(res.stdout, str) else ""
                _err = res.stderr if isinstance(res.stderr, str) else ""
                info = parse_ping_output(_out + "\n" + _err)
                if "avg_ms" in info:
                    sample.ping_avg_ms = float(info["avg_ms"])
                if "max_ms" in info:
                    sample.ping_max_ms = float(info["max_ms"])
                if "mdev_ms" in info:
                    sample.jitter_ms = float(info["mdev_ms"])
                if "loss_pct" in info:
                    sample.ping_loss_pct = float(info["loss_pct"])
        except Exception:
            pass

        # iw station dump.
        try:
            res = subprocess.run(
                ["iw", "dev", self.interface, "station", "dump"],
                timeout=10,
                capture_output=True,
                text=True,
            )
            if res.returncode == 0:
                _out = res.stdout if isinstance(res.stdout, str) else ""
                info = parse_iw_station_dump(_out)
                if "signal_dbm" in info:
                    sample.signal_dbm = float(info["signal_dbm"])
                if "rx_drop_misc" in info:
                    # Fold into dropped total if available.
                    pass
        except Exception:
            pass

        # curl timing.
        try:
            res = subprocess.run(
                [
                    "curl", "-sS", "-o", "/dev/null",
                    "-w", "%{time_namelookup} %{time_connect} %{time_appconnect} %{time_starttransfer} %{time_total}",
                    "--max-time", "5",
                    "https://speed.cloudflare.com/__down?bytes=1",
                ],
                timeout=10,
                capture_output=True,
                text=True,
            )
            if res.returncode == 0:
                _out = res.stdout if isinstance(res.stdout, str) else ""
                parts = _out.split()
                if len(parts) >= 5:
                    vals = [float(x) for x in parts[:5]]
                    nl, conn, app, start, total = vals
                    sample.dns_ms = nl * 1000.0
                    sample.tcp_connect_ms = (conn - nl) * 1000.0
                    sample.tls_ms = (app - conn) * 1000.0
                    sample.ttfb_ms = (start - app) * 1000.0
        except Exception:
            pass

        # Battery (best effort).
        try:
            for bat in ("BAT0", "BAT1"):
                cap_path = f"/sys/class/power_supply/{bat}/capacity"
                try:
                    with open(cap_path) as f:
                        sample.battery_pct = float(f.read().strip())
                    break
                except FileNotFoundError:
                    continue
            # on_battery
            for ac in ("AC", "ACAD", "ADP0"):
                online_path = f"/sys/class/power_supply/{ac}/online"
                try:
                    with open(online_path) as f:
                        sample.on_battery = (f.read().strip() == "0")
                    break
                except FileNotFoundError:
                    continue
            # health
            for bat in ("BAT0", "BAT1"):
                try:
                    with open(f"/sys/class/power_supply/{bat}/health") as f:
                        health = f.read().strip()
                    # Not a percentage; leave 0 unless energy files exist.
                    break
                except FileNotFoundError:
                    continue
            for bat in ("BAT0", "BAT1"):
                try:
                    with open(f"/sys/class/power_supply/{bat}/energy_full") as f:
                        full = float(f.read().strip())
                    with open(f"/sys/class/power_supply/{bat}/energy_full_design") as f:
                        design = float(f.read().strip())
                    if design > 0:
                        sample.battery_health_pct = (full / design) * 100.0
                    break
                except FileNotFoundError:
                    continue
        except Exception:
            pass

        # CPU temp.
        try:
            with open("/sys/class/thermal/thermal_zone0/temp") as f:
                sample.cpu_temp_c = float(f.read().strip()) / 1000.0
        except Exception:
            pass

        return sample