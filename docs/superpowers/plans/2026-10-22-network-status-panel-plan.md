# Network Status Panel (nst) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a GTK4 layer-shell network status panel for Fedora 44 Sway Atomic that answers "is my internet actually slow right now, and why?" with a glanceable verdict, replacing the browser speed-test detour.

**Architecture:** Python 3.14 app using GTK4 4.22 + libadwaita 1.9 + gtk4-layer-shell 1.3.0. Three-tier measurement: continuous passive (T0, free), scheduled capacity probe (T1, every 8 h, 40 MB), on-demand full test (T2). Verdict engine combines passive signals + last probe. Config-driven addon modules. Cairo for sparklines, CSS animations for bars/chips.

**Tech Stack:** Python 3.14, PyGObject 3.56, GTK4 4.22, libadwaita 1.9, gtk4-layer-shell 1.3.0, python3-cairo 1.28.0, TOML config, systemd user unit.

**Spec:** docs/superpowers/specs/2026-10-22-network-status-panel-design.md

## Global Constraints

- Python 3.14 (host interpreter at /usr/bin/python3); no gcc/rust/cargo/dnf on host
- GTK4 4.22, libadwaita 1.9, pygobject3 3.56, gtk4-layer-shell 1.3.0 (install via rpm-ostree install -yA)
- All GTK/GDK calls on the main thread; sampling in worker threads with GLib.idle_add() for results
- No 60 fps always-on animation; 20–30 fps bursts only, 0 fps when idle
- 120 MB/day data budget for scheduled probes (T1: 8×5 MB = 40 MB, every 8 hours)
- CacheFly primary probe host, Cloudflare backup (rotation on 429)
- All network measurement commands use subprocess with timeout; never shell=True
- Config in ~/.config/nst/config.toml; state in ~/.local/state/nst/; cache in ~/.local/cache/nst/
- Tokyo Night palette: bg #1a1b26, fg #c0caf5, blue #7aa2f7, cyan #7dcfff, purple #bb9af7, green #9ece6a, yellow #e0af68, red #f7768e, muted #a9b1d6, dim #414868
- Font: "JetBrainsMono Nerd Font", 12 px

## Review Focus

Five failure modes the spec implies but no task's tests exercise:

1. **Counter wrap/reset on interface flap** — /proc/net/dev counters reset to 0 on interface removal/recreation (Wi-Fi reconnect). A naive delta produces a negative rate. Tests must cover `bytes_now < bytes_prev` → discard sample, not clamp to zero.
2. **T0 loop running while a probe is in flight** — the passive monitor must not read /proc/net/dev during a probe (it would include probe traffic). Tests must verify the T0 loop pauses or excludes probe traffic during T1/T2.
3. **Verdict with no cached probe on cold start** — the verdict engine must handle `last_probe = None` without crashing, showing "MEASURING..." until the first probe completes.
4. **CacheFly 429 / network failure during probe** — the probe must not crash or show a false "degraded" verdict; it should retry with exponential backoff and fall back to Cloudflare.
5. **Reduced motion + battery gating interaction** — if both `prefers-reduced-motion` and "on battery + low" are active, animations must be fully disabled. Tests must verify no animation runs in this combined state.

---

### Task 1: Project scaffolding and configuration

**Files:**
- Create: `pyproject.toml`
- Create: `src/nst/__init__.py`
- Create: `src/nst/__main__.py`
- Create: `src/nst/config.py`
- Create: `tests/conftest.py`
- Create: `tests/test_config.py`
- Create: `config.toml.example`

**Interfaces:**
- Produces: `load_config(path) -> Config` — loads TOML config, returns dataclass with all settings and defaults
- Produces: `Config` dataclass with fields: `probe_interval_hours`, `probe_hosts`, `probe_size_mb`, `probe_connections`, `t0_interval_seconds`, `animation_enabled`, `battery_threshold`, `modules_enabled`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
import tomllib, tempfile, os
from nst.config import load_config, Config

def test_load_config_defaults():
    cfg = load_config(None)
    assert cfg.probe_interval_hours == 8
    assert cfg.probe_hosts == ["cacheFly", "cloudflare"]
    assert cfg.probe_size_mb == 5
    assert cfg.probe_connections == 8
    assert cfg.t0_interval_seconds == 2
    assert cfg.animation_enabled is True
    assert cfg.battery_threshold == 30
    assert "bufferbloat" in cfg.modules_enabled

def test_load_config_from_file():
    content = b"""
[probe]
interval_hours = 4
hosts = ["cloudflare"]
size_mb = 10
connections = 4

[t0]
interval_seconds = 1

[animation]
enabled = false
battery_threshold = 20

[modules]
enabled = ["throughput", "latency", "bufferbloat"]
"""
    with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
        f.write(content)
        f.flush()
        cfg = load_config(f.name)
    os.unlink(f.name)
    assert cfg.probe_interval_hours == 4
    assert cfg.probe_hosts == ["cloudflare"]
    assert cfg.probe_size_mb == 10
    assert cfg.probe_connections == 4
    assert cfg.t0_interval_seconds == 1
    assert cfg.animation_enabled is False
    assert cfg.battery_threshold == 20
    assert cfg.modules_enabled == ["throughput", "latency", "bufferbloat"]

def test_load_config_missing_file_raises():
    import pytest
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/path.toml")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'nst'"

- [ ] **Step 3: Implement config module**

Create `pyproject.toml`:
```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "nst"
version = "0.1.0"
requires-python = ">=3.14"

[tool.setuptools.packages.find]
where = ["src"]
```

Create `src/nst/__init__.py` (empty).
Create `src/nst/__main__.py`:
```python
import sys
from nst.config import load_config

def main():
    config = load_config(sys.argv[1] if len(sys.argv) > 1 else None)
    print(f"nst config loaded: probe every {config.probe_interval_hours}h, t0 every {config.t0_interval_seconds}s")

if __name__ == "__main__":
    main()
```

Create `src/nst/config.py`:
```python
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class Config:
    probe_interval_hours: int = 8
    probe_hosts: list[str] = field(default_factory=lambda: ["cacheFly", "cloudflare"])
    probe_size_mb: int = 5
    probe_connections: int = 8
    t0_interval_seconds: int = 2
    animation_enabled: bool = True
    battery_threshold: int = 30
    modules_enabled: list[str] = field(default_factory=lambda: [
        "throughput", "latency", "bufferbloat", "signal", "battery",
        "cpu", "memory", "disk", "public_ip", "os_updates", "ipv6", "devices"
    ])

def load_config(path: str | None) -> Config:
    if path is None:
        return Config()
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(p, "rb") as f:
        data = tomllib.load(f)
    probe = data.get("probe", {})
    t0 = data.get("t0", {})
    anim = data.get("animation", {})
    mods = data.get("modules", {})
    return Config(
        probe_interval_hours=probe.get("interval_hours", 8),
        probe_hosts=probe.get("hosts", ["cacheFly", "cloudflare"]),
        probe_size_mb=probe.get("size_mb", 5),
        probe_connections=probe.get("connections", 8),
        t0_interval_seconds=t0.get("interval_seconds", 2),
        animation_enabled=anim.get("enabled", True),
        battery_threshold=anim.get("battery_threshold", 30),
        modules_enabled=mods.get("enabled", Config().modules_enabled),
    )
```

Create `tests/conftest.py`:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
```

Create `config.toml.example` with documented defaults.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_config.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/nst/__init__.py src/nst/__main__.py src/nst/config.py tests/conftest.py tests/test_config.py config.toml.example
git commit -m "feat: project scaffolding and TOML config"
```

---

### Task 2: Throughput calculation and counter handling

**Files:**
- Create: `src/nst/measurement/throughput.py`
- Create: `tests/test_throughput.py`

**Interfaces:**
- Consumes: raw `/proc/net/dev` lines (string)
- Produces: `parse_proc_net_dev(text) -> dict[str, InterfaceCounters]` where `InterfaceCounters` has `rx_bytes, tx_bytes, rx_dropped, rx_errors, rx_packets, tx_packets, tx_dropped, tx_errors`
- Produces: `compute_rate(prev: InterfaceCounters, curr: InterfaceCounters, elapsed_s: float) -> ThroughputResult` where `ThroughputResult` has `rx_bps, tx_bps, rx_dropped_rate, valid: bool`
- Produces: `ThroughputResult.valid` is False when `curr.rx_bytes < prev.rx_bytes` (counter reset/wrap)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_throughput.py
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
    # No previous sample — should be invalid
    r = compute_rate(None, InterfaceCounters(rx_bytes=1000, tx_bytes=500, rx_dropped=0, rx_errors=0, rx_packets=0, tx_packets=0, tx_dropped=0, tx_errors=0), 1.0)
    assert r.valid is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_throughput.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement throughput module**

Create `src/nst/measurement/__init__.py` (empty).
Create `src/nst/measurement/throughput.py` with `InterfaceCounters` dataclass, `ThroughputResult` dataclass, `parse_proc_net_dev()`, and `compute_rate()`.

Key implementation details:
- `parse_proc_net_dev`: skip first 2 header lines, parse each interface line with split(), handle interface names with colons
- `compute_rate`: if prev is None → invalid; if elapsed_s <= 0 → invalid; if curr.rx_bytes < prev.rx_bytes → invalid (counter reset); otherwise compute rates as (curr - prev) / elapsed_s

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_throughput.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/nst/measurement/ tests/test_throughput.py
git commit -m "feat: throughput calculation with counter reset detection"
```

---

### Task 3: Verdict engine

**Files:**
- Create: `src/nst/measurement/verdict.py`
- Create: `tests/test_verdict.py`

**Interfaces:**
- Consumes: throughput result, latency data, signal strength, rx_dropped rate, retransmit count, beacon loss, bufferbloat delta
- Produces: `compute_verdict(signals: VerdictSignals) -> Verdict` where `Verdict` is one of HEALTHY, ISP_LIMITED, RADIO_DEGRADED, HIGH_LATENCY

- [ ] **Step 1: Write the failing test**

```python
# tests/test_verdict.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_verdict.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement verdict engine**

Create `src/nst/measurement/verdict.py` with `Verdict` enum (HEALTHY, ISP_LIMITED, RADIO_DEGRADED, HIGH_LATENCY), `VerdictSignals` dataclass, and `compute_verdict()`.

Verdict logic (in severity order):
1. RADIO_DEGRADED if: signal_dbm < -75 OR rx_dropped_rate > 1.0 OR retransmits > 0 OR beacon_loss > 0
2. HIGH_LATENCY if: ping_avg_ms > 50 OR jitter_ms > 20 OR bufferbloat_lan_ms > 10 (with throughput >= 15 or throughput is None)
3. ISP_LIMITED if: throughput is not None AND throughput < 30 AND radio is healthy (signal >= -75, retransmits 0, beacon_loss 0, rx_dropped_rate <= 0.2) AND WAN latency normal (bufferbloat_wan_ms <= 5)
4. HEALTHY (default)

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_verdict.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add src/nst/measurement/verdict.py tests/test_verdict.py
git commit -m "feat: verdict engine with precedence rules"
```

---

### Task 4: T0 passive monitoring

**Files:**
- Create: `src/nst/measurement/t0_passive.py`
- Create: `tests/test_t0.py`

**Interfaces:**
- Consumes: config, subprocess (ping, iw, curl)
- Produces: `T0Sample` dataclass with fields: timestamp, rx_bps, tx_bps, ping_avg_ms, ping_max_ms, ping_loss_pct, jitter_ms, dns_ms, tcp_connect_ms, tls_ms, ttfb_ms, signal_dbm, rx_dropped_rate, rx_dropped_total, battery_pct, battery_health_pct, on_battery, cpu_temp_c, public_ip, ipv6_global
- Produces: `T0Monitor` class with `start(callback)`, `stop()`, `get_latest() -> T0Sample | None`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_t0.py
from nst.measurement.t0_passive import parse_iw_link, parse_ping_output, parse_iw_station_dump

def test_parse_iw_link():
    output = """Connected to a4:81:7a:2e:1e:ad (on wlp2s0)
\tSSID: RYAN 5G
\tfreq: 5220.0
\tRX: 3136115294 bytes (3994752 packets)
\tTX: 1912424200 bytes (2342866 packets)
\tsignal: -70 dBm
\trx bitrate: 87.8 MBit/s VHT-MCS 2 80MHz VHT-NSS 1
\ttx bitrate: 175.5 MBit/s VHT-MCS 4 80MHz VHT-NSS 1
\tbss flags: short-slot-time
\tdtim period: 1
\tbeacon int: 100
"""
    result = parse_iw_link(output)
    assert result["ssid"] == "RYAN 5G"
    assert result["signal_dbm"] == -70
    assert result["rx_bitrate_mbps"] == 87.8
    assert result["tx_bitrate_mbps"] == 175.5
    assert result["freq_mhz"] == 5220.0

def test_parse_ping_output():
    output = """PING 1.1.1.1 (1.1.1.1) 56(84) bytes of data.
64 bytes from 1.1.1.1: icmp_seq=1 ttl=58 time=10.8 ms
64 bytes from 1.1.1.1: icmp_seq=2 ttl=58 time=12.0 ms
64 bytes from 1.1.1.1: icmp_seq=3 ttl=58 time=10.7 ms
--- 1.1.1.1 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2003ms
rtt min/avg/max/mdev = 10.700/11.167/12.000/0.569 ms
"""
    result = parse_ping_output(output)
    assert result["avg_ms"] == 11.167
    assert result["max_ms"] == 12.0
    assert result["mdev_ms"] == 0.569
    assert result["loss_pct"] == 0.0
    assert result["received"] == 3
    assert result["transmitted"] == 3

def test_parse_iw_station_dump():
    output = """Station a4:81:7a:2e:1e:ad (on wlp2s0)
\tauthorized: yes
\tinactive time: 108 ms
\trx bytes: 3136115294   rx packets: 3994752
\ttx bytes: 1912424200   tx packets: 2342866
\ttx retries: 0          tx failed: 0        beacon loss: 0
\tbeacon rx: 366569
\trx drop misc: 1205
\tsignal:      -70 [-70] dBm
\tsignal avg:  -70 [-70] dBm
\ttx bitrate: 175.5 MBit/s VHT-MCS 4 80MHz VHT-NSS 1
\ttx duration: 0 us
\trx bitrate: 87.8 MBit/s VHT-MCS 2 80MHz VHT-NSS 1
"""
    result = parse_iw_station_dump(output)
    assert result["tx_retries"] == 0
    assert result["tx_failed"] == 0
    assert result["beacon_loss"] == 0
    assert result["rx_drop_misc"] == 1205
    assert result["signal_dbm"] == -70
    assert result["signal_avg_dbm"] == -70
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_t0.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement T0 passive monitoring**

Create `src/nst/measurement/t0_passive.py` with:
- `T0Sample` dataclass
- `parse_iw_link(text) -> dict`
- `parse_ping_output(text) -> dict`
- `parse_iw_station_dump(text) -> dict`
- `T0Monitor` class with worker thread, subprocess calls with timeout, and callback dispatch via GLib.idle_add

Key implementation details:
- Worker thread runs in a loop with configurable interval
- Subprocess calls: `iw dev wlp2s0 link`, `ping -c 3 -W 1 1.1.1.1`, `iw dev wlp2s0 station dump`, `curl -sS -o /dev/null -w '...' --max-time 5 https://speed.cloudflare.com/__down?bytes=1`
- All subprocess calls use `subprocess.run(..., timeout=10, capture_output=True, text=True)` with a 10 s timeout
- Results are marshalled to the main thread via `GLib.idle_add(callback, sample)`
- `get_latest()` returns the most recent sample (thread-safe via lock)

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_t0.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/nst/measurement/t0_passive.py tests/test_t0.py
git commit -m "feat: T0 passive monitoring with iw/ping/curl parsers"
```

---

### Task 5: T1 scheduled probe

**Files:**
- Create: `src/nst/measurement/t1_probe.py`
- Create: `tests/test_t1.py`

**Interfaces:**
- Consumes: config, subprocess (curl)
- Produces: `ProbeResult` dataclass with fields: timestamp, host, down_mbps, up_mbps, down_mbps_transfer_phase, up_mbps_transfer_phase, dns_ms, tcp_connect_ms, tls_ms, ttfb_ms, total_ms, success, error, bytes_consumed
- Produces: `run_probe(hosts, connections, size_mb) -> ProbeResult` — runs the probe and returns results

- [ ] **Step 1: Write the failing test**

```python
# tests/test_t1.py
from nst.measurement.t1_probe import compute_probe_result, ProbeResult

def test_compute_probe_result_from_curl_output():
    # Simulated curl -w output for one connection
    conn_data = [
        {"size_download": 5000000, "time_total": 1.0, "time_starttransfer": 0.2, "http_code": 200, "time_namelookup": 0.004, "time_connect": 0.021, "time_appconnect": 0.064},
        {"size_download": 5000000, "time_total": 1.1, "time_starttransfer": 0.25, "http_code": 200, "time_namelookup": 0.004, "time_connect": 0.021, "time_appconnect": 0.064},
    ]
    result = compute_probe_result("cacheFly", conn_data, 5.0)
    assert result.host == "cacheFly"
    assert result.success is True
    assert result.down_mbps > 0
    assert result.bytes_consumed == 10000000

def test_compute_probe_result_failure():
    conn_data = [{"size_download": 0, "time_total": 0, "time_starttransfer": 0, "http_code": 429, "time_namelookup": 0, "time_connect": 0, "time_appconnect": 0}]
    result = compute_probe_result("cloudflare", conn_data, 5.0)
    assert result.success is False
    assert result.error is not None

def test_compute_probe_result_empty():
    result = compute_probe_result("cacheFly", [], 5.0)
    assert result.success is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_t1.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement T1 probe module**

Create `src/nst/measurement/t1_probe.py` with:
- `ProbeResult` dataclass
- `compute_probe_result(host, conn_data, size_mb) -> ProbeResult`
- `run_probe(hosts, connections, size_mb) -> ProbeResult` — runs curl subprocesses in parallel, collects results, computes aggregate
- Host rotation logic: try CacheFly first, fall back to Cloudflare on 429 or failure
- Uses `subprocess.run` with `--max-time` and `-w` format string for curl

Key implementation details:
- Each connection: `curl -sS -o /dev/null --max-time 10 -w '%{json}' 'https://cachefly.cachefly.net/100mb.test'` with Range header for partial download
- Run connections in parallel using `concurrent.futures.ThreadPoolExecutor`
- Aggregate: total bytes / wall-clock span, discard first 2 seconds
- On 429: retry with Cloudflare, then exponential backoff (max 3 retries)

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_t1.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/nst/measurement/t1_probe.py tests/test_t1.py
git commit -m "feat: T1 scheduled probe with host rotation and ramp discard"
```

---

### Task 6: Bufferbloat measurement

**Files:**
- Create: `src/nst/measurement/bufferbloat.py`
- Create: `tests/test_bufferbloat.py`

**Interfaces:**
- Consumes: subprocess (ping, curl)
- Produces: `BufferbloatResult` dataclass with fields: `baseline_lan_ms, loaded_lan_ms, delta_lan_ms, baseline_wan_ms, loaded_wan_ms, delta_wan_ms, success`
- Produces: `measure_bufferbloat() -> BufferbloatResult`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_bufferbloat.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_bufferbloat.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement bufferbloat module**

Create `src/nst/measurement/bufferbloat.py` with:
- `BufferbloatResult` dataclass
- `compute_bufferbloat(baseline_lan, loaded_lan, baseline_wan, loaded_wan) -> BufferbloatResult`
- `measure_bufferbloat() -> BufferbloatResult` — runs baseline ping, starts a background download (CacheFly), pings during load, stops download, computes deltas

Key implementation details:
- Baseline: `ping -c 10 -i 0.2 -W 1 192.168.1.254` and `ping -c 10 -i 0.2 -W 1 1.1.1.1`
- Load: `curl -o /dev/null --max-time 10 https://cachefly.cachefly.net/100mb.test` in background
- Loaded ping: same ping commands while download is running
- Parse ping output for avg RTT
- Clean up background process on completion or timeout

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_bufferbloat.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/nst/measurement/bufferbloat.py tests/test_bufferbloat.py
git commit -m "feat: bufferbloat measurement (LAN +39.9ms, WAN +0.4ms)"
```

---

### Task 7: GTK4 panel window (layer-shell, transparent)

**Files:**
- Create: `src/nst/ui/__init__.py`
- Create: `src/nst/ui/panel.py`
- Create: `src/nst/ui/css.py`

**Interfaces:**
- Consumes: config, Gdk.Display, Gtk.Application
- Produces: `NetworkPanel` class (Gtk.Window subclass) with `show_collapsed()`, `show_expanded()`, `update(sample)`, `set_verdict(verdict)`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_panel.py
# Note: GTK tests require a display. Skip if no DISPLAY/WAYLAND_DISPLAY.
import pytest
import os

pytestmark = pytest.mark.skipif(
    not (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY")),
    reason="No display available"
)

def test_panel_import():
    from nst.ui.panel import NetworkPanel
    assert NetworkPanel is not None

def test_css_provider_loads():
    from nst.ui.css import install_css
    import gi
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk
    display = Gtk.Display.get_default()
    if display is None:
        pytest.skip("No display")
    provider = install_css(display)
    assert provider is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_panel.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement panel window**

Create `src/nst/ui/__init__.py` (empty).
Create `src/nst/ui/css.py` with `install_css(display)` — loads Tokyo Night CSS, binds prefers-reduced-motion.
Create `src/nst/ui/panel.py` with `NetworkPanel` class.

Key implementation details:
- `Gtk.Window` subclass, `set_decorated(False)`, `set_default_size(434, 172)`
- `gi.require_version("Gtk4LayerShell", "1.0")` before importing
- `from ctypes import CDLL; CDLL("libgtk4-layer-shell.so.0")` before `import gi`
- `Gtk4LayerShell.init_for_window(self)` before present()
- `set_layer(Layer.TOP)`, `set_namespace("netstatus")`
- Anchors: BOTTOM=True, LEFT=True (collapsed); bottom-left corner
- `set_exclusive_zone(0)` (floats, no space reserved)
- `set_keyboard_mode(KeyboardMode.NONE)` (collapsed)
- `set_margin(BOTTOM, 34)` (above waybar's 32px + 2px gap)
- CSS: `window { background: transparent; }`
- Methods: `show_collapsed()`, `show_expanded()` (switches keyboard mode to ON_DEMAND), `update(sample)`, `set_verdict(verdict)`

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_panel.py -v`
Expected: PASS or SKIP (if no display)

- [ ] **Step 5: Commit**

```bash
git add src/nst/ui/ tests/test_panel.py
git commit -m "feat: GTK4 layer-shell panel window with transparent CSS"
```

---

### Task 8: Collapsed panel tiles with data-driven bars

**Files:**
- Create: `src/nst/ui/tiles.py`
- Modify: `src/nst/ui/panel.py`

**Interfaces:**
- Consumes: `T0Sample`, `Verdict`
- Produces: `TileGrid` class with `update(sample, verdict)`, `flash()`, `set_state(state)`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_tiles.py
import pytest
import os

pytestmark = pytest.mark.skipif(
    not (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY")),
    reason="No display available"
)

def test_tile_grid_import():
    from nst.ui.tiles import TileGrid
    assert TileGrid is not None

def test_tile_grid_creates_six_tiles():
    from nst.ui.tiles import TileGrid
    import gi
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk
    grid = TileGrid()
    assert len(grid.tiles) == 6
    assert "DOWN" in grid.tiles
    assert "CPU" in grid.tiles
    assert "DISK" in grid.tiles
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_tiles.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement tile grid**

Create `src/nst/ui/tiles.py` with:
- `TileGrid(Gtk.Grid)` subclass
- 6 tiles in 3×2 grid: DOWN, UP, PING, SIGNAL, CPU, DISK
- Each tile: label, musical bar (Gtk.Box with CSS class), value, subtitle
- `update(sample, verdict)` — updates values, bar widths (via CSS class), colors
- `set_state(state)` — toggles good/warn/bad CSS classes
- `flash()` — adds flash CSS class briefly
- Bar width set via CSS custom property or inline style

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_tiles.py -v`
Expected: PASS or SKIP (if no display)

- [ ] **Step 5: Commit**

```bash
git add src/nst/ui/tiles.py tests/test_tiles.py
git commit -m "feat: collapsed panel tiles with data-driven musical bars"
```

---

### Task 9: Scrolling heartbeat graph

**Files:**
- Create: `src/nst/ui/heartbeat.py`
- Create: `tests/test_heartbeat.py`

**Interfaces:**
- Consumes: throughput samples (list of floats)
- Produces: `HeartbeatGraph(Gtk.DrawingArea)` with `add_sample(value)`, `start_scroll()`, `stop_scroll()`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_heartbeat.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_heartbeat.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement heartbeat graph**

Create `src/nst/ui/heartbeat.py` with:
- `HeartbeatGraph(Gtk.DrawingArea)` subclass
- Ring buffer of samples (max 200 at 1 Hz = ~3.3 min history)
- `add_sample(value)` — appends to buffer, triggers scroll animation
- `set_draw_func()` with Cairo: draws grid, threshold line, waveform, fill gradient, latest dot
- `start_scroll()` — installs `add_tick_callback` at 20–30 fps
- `stop_scroll()` — removes tick callback
- Scroll animation: new samples push old ones left, 300 ms smooth scroll
- Tick callback removed automatically when scroll settles
- Threshold line at 15 Mbit/s (red dashed)

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_heartbeat.py -v`
Expected: PASS or SKIP (if no display)

- [ ] **Step 5: Commit**

```bash
git add src/nst/ui/heartbeat.py tests/test_heartbeat.py
git commit -m "feat: scrolling heartbeat graph with ring buffer"
```

---

### Task 10: Expanded panel with detail view

**Files:**
- Create: `src/nst/ui/expanded.py`
- Modify: `src/nst/ui/panel.py`

**Interfaces:**
- Consumes: `T0Sample`, `Verdict`, `ProbeResult`, list of devices
- Produces: `ExpandedPanel(Gtk.Box)` with `update(sample, verdict, probe_result, devices)`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_expanded.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_expanded.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement expanded panel**

Create `src/nst/ui/expanded.py` with:
- `ExpandedPanel(Gtk.Box)` — vertical layout
- Hero section: big throughput number + verdict block
- Heartbeat graph (from Task 9)
- Local link bars (signal, link rate, delivered, retransmits, bufferbloat) with data-driven musical bars
- Latency section (avg, max, jitter, loss, DNS, gateway, drops, WAN bloat)
- Devices section (router, android, etc.)
- Actions row: "Run speed test now", "Copy diagnostics", "Open in terminal"
- `update(sample, verdict, probe_result, devices)` — refreshes all sections

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_expanded.py -v`
Expected: PASS or SKIP (if no display)

- [ ] **Step 5: Commit**

```bash
git add src/nst/ui/expanded.py tests/test_expanded.py
git commit -m "feat: expanded detail panel with bars, latency, devices, actions"
```

---

### Task 11: Addon modules

**Files:**
- Create: `src/nst/addons/__init__.py`
- Create: `src/nst/addons/base.py`
- Create: `src/nst/addons/bufferbloat.py`
- Create: `src/nst/addons/public_ip.py`
- Create: `src/nst/addons/battery.py`
- Create: `src/nst/addons/os_updates.py`
- Create: `src/nst/addons/cpu_mem.py`
- Create: `src/nst/addons/wifi.py`
- Create: `tests/test_addons.py`

**Interfaces:**
- Consumes: config, T0Sample, subprocess
- Produces: `AddonModule` base class with `update(sample) -> dict`, `render() -> Gtk.Widget`
- Produces: `load_modules(config) -> list[AddonModule]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_addons.py
from nst.addons.base import AddonModule, load_modules
from nst.config import Config

def test_addon_base_interface():
    class DummyAddon(AddonModule):
        name = "dummy"
        def update(self, sample):
            return {"value": 42}
        def render(self):
            import gi
            gi.require_version("Gtk", "4.0")
            from gi.repository import Gtk
            return Gtk.Label(label="dummy")
    addon = DummyAddon()
    assert addon.update(None) == {"value": 42}
    assert addon.name == "dummy"

def test_load_modules():
    cfg = Config(modules_enabled=["cpu", "battery"])
    modules = load_modules(cfg)
    names = [m.name for m in modules]
    assert "cpu" in names
    assert "battery" in names

def test_load_modules_empty():
    cfg = Config(modules_enabled=[])
    modules = load_modules(cfg)
    assert modules == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_addons.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement addon modules**

Create `src/nst/addons/base.py` with `AddonModule` ABC and `load_modules()` factory.
Create each addon module implementing the interface:
- `bufferbloat.py`: wraps bufferbloat measurement
- `public_ip.py`: fetches public IP + ISP from ifconfig.co
- `battery.py`: reads UPower for health %, cycles, charge threshold
- `os_updates.py`: runs rpm-ostree status --json, checks for pending updates/reboot
- `cpu_mem.py`: reads /proc/stat, /proc/meminfo, thermal zones
- `wifi.py`: reads iw link + station dump for signal, rate, drops

Each module's `update()` returns a dict of values; `render()` returns a Gtk.Widget.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_addons.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/nst/addons/ tests/test_addons.py
git commit -m "feat: addon module system with 6 Tier 1 modules"
```

---

### Task 12: Application entry point and main loop

**Files:**
- Modify: `src/nst/__main__.py`
- Create: `src/nst/app.py`

**Interfaces:**
- Consumes: all modules above
- Produces: `NstApplication(Gtk.Application)` with `do_activate()`, `run()`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_app.py
import pytest
import os

pytestmark = pytest.mark.skipif(
    not (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY")),
    reason="No display available"
)

def test_app_import():
    from nst.app import NstApplication
    assert NstApplication is not None

def test_app_creates_panel():
    from nst.app import NstApplication
    app = NstApplication()
    # do_activate requires a display; just check the class
    assert hasattr(app, "do_activate")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_app.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement application**

Create `src/nst/app.py` with:
- `NstApplication(Gtk.Application)` subclass
- `do_activate()`: creates the NetworkPanel, loads config, starts T0 monitor, schedules T1 probe, starts addon modules
- `on_t0_sample(sample)`: updates panel tiles, heartbeat graph, verdict engine
- `on_probe_complete(result)`: updates probe history, verdict
- `on_quit()`: stops monitors, saves state
- Main loop: `app.run()` with proper signal handling

Update `src/nst/__main__.py` to use `NstApplication`.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_app.py -v`
Expected: PASS or SKIP (if no display)

- [ ] **Step 5: Commit**

```bash
git add src/nst/app.py src/nst/__main__.py tests/test_app.py
git commit -m "feat: application entry point with main loop"
```

---

### Task 13: Autostart and packaging

**Files:**
- Create: `src/nst/autostart.py`
- Create: `install.sh`
- Create: `nst.service` (systemd user unit template)

**Interfaces:**
- Produces: `install(config) -> None` — installs the app to ~/.local/bin, creates systemd user unit, enables it

- [ ] **Step 1: Write the failing test**

```python
# tests/test_autostart.py
from nst.autostart import generate_systemd_unit, generate_sway_exec

def test_generate_systemd_unit():
    unit = generate_systemd_unit("/home/user/.local/bin/nst", "/home/user/.config/nst/config.toml")
    assert "ExecStart=" in unit
    assert "WantedBy=sway-session.target" in unit
    assert "ExecStartPre=" in unit
    assert "swaymsg -t get_outputs" in unit

def test_generate_sway_exec():
    exec_line = generate_sway_exec("/home/user/.local/bin/nst")
    assert "swaymsg -t get_outputs" in exec_line
    assert "/home/user/.local/bin/nst" in exec_line
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_autostart.py -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement autostart**

Create `src/nst/autostart.py` with:
- `generate_systemd_unit(binary_path, config_path) -> str`
- `generate_sway_exec(binary_path) -> str`
- `install(config) -> None` — copies script to ~/.local/bin, creates systemd unit, enables it

Create `nst.service` template and `install.sh` script.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_autostart.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/nst/autostart.py tests/test_autostart.py install.sh nst.service
git commit -m "feat: autostart via systemd user unit with sway readiness guard"
```

---

### Task 14: Integration and polish

**Files:**
- Modify: `src/nst/app.py`
- Modify: `src/nst/ui/panel.py`
- Modify: `src/nst/ui/expanded.py`

**Interfaces:**
- Integrates all modules into a working application

- [ ] **Step 1: Wire everything together**

- Connect T0 monitor → panel.update() + verdict engine + heartbeat graph
- Connect T1 probe → panel.probe_history + verdict
- Connect addon modules → expanded panel sections
- Connect bufferbloat → verdict engine
- Add keyboard shortcuts: Escape (close expanded), Ctrl+R (run probe)
- Add error handling: DNS failure, interface down, no network
- Add logging via Python logging module (journald-compatible)

- [ ] **Step 2: Run full test suite**

Run: `PYTHONPATH=src python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 3: Manual smoke test**

Run: `PYTHONPATH=src python -m nst` (requires display)
Expected: Panel appears bottom-left, shows tiles, heartbeat graph scrolls, bars animate, verdict shows "ISP LIMITED"

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: integration and polish — working panel"
```