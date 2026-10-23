"""Bufferbloat measurement.

Provides a pure ``compute_bufferbloat`` aggregator plus ``measure_bufferbloat``
which runs ping/curl subprocesses to estimate LAN and WAN latency inflation
under load.
"""

from __future__ import annotations

import math
import re
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class BufferbloatResult:
    baseline_lan_ms: float = 0.0
    loaded_lan_ms: float = 0.0
    delta_lan_ms: float = 0.0
    baseline_wan_ms: float = 0.0
    loaded_wan_ms: float = 0.0
    delta_wan_ms: float = 0.0
    success: bool = False


def parse_ping_output(text: str) -> dict[str, Any]:
    """Parse ping output, returning a dict with avg_ms when available."""
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


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (bytes, bytearray)):
        try:
            return value.decode("utf-8", errors="replace")
        except Exception:
            return str(value)
    return str(value)


def _run_result_text(res: Any) -> str:
    if isinstance(res, dict):
        stdout = res.get("stdout", res.get("output", ""))
        stderr = res.get("stderr", "")
        return _as_text(stdout) + "\n" + _as_text(stderr)
    stdout = getattr(res, "stdout", "")
    stderr = getattr(res, "stderr", "")
    return _as_text(stdout) + "\n" + _as_text(stderr)


def _ping_avg(target: str) -> Optional[float]:
    """Run a ping against *target* and return the average RTT in ms, or None."""
    cmd = ["ping", "-c", "10", "-i", "0.2", "-W", "1", target]
    try:
        res = subprocess.run(cmd, timeout=15, capture_output=True, text=True)
    except Exception:
        return None
    # Support mocked returns that are dicts.
    if isinstance(res, dict):
        rc = res.get("returncode", 0)
    else:
        rc = getattr(res, "returncode", 0)
    text = _run_result_text(res)
    info = parse_ping_output(text)
    if "avg_ms" not in info:
        # Some mocks provide avg directly.
        if isinstance(res, dict) and "avg_ms" in res:
            try:
                return float(res["avg_ms"])
            except (TypeError, ValueError):
                return None
        return None
    try:
        val = float(info["avg_ms"])
    except (TypeError, ValueError):
        return None
    if not math.isfinite(val):
        return None
    # Accept non-zero return codes only if we parsed an avg (e.g. partial loss).
    _ = rc
    return val


def compute_bufferbloat(
    baseline_lan: Any,
    loaded_lan: Any,
    baseline_wan: Any,
    loaded_wan: Any,
) -> BufferbloatResult:
    """Pure aggregator: compute deltas (loaded - baseline) for LAN and WAN."""
    try:
        bl = float(baseline_lan)
        ll = float(loaded_lan)
        bw = float(baseline_wan)
        lw = float(loaded_wan)
    except (TypeError, ValueError):
        return BufferbloatResult(success=False)
    if not all(math.isfinite(v) for v in (bl, ll, bw, lw)):
        return BufferbloatResult(success=False)
    delta_lan = ll - bl
    delta_wan = lw - bw
    return BufferbloatResult(
        baseline_lan_ms=bl,
        loaded_lan_ms=ll,
        delta_lan_ms=round(delta_lan, 9),
        baseline_wan_ms=bw,
        loaded_wan_ms=lw,
        delta_wan_ms=round(delta_wan, 9),
        success=True,
    )


def measure_bufferbloat() -> BufferbloatResult:
    """Best-effort live measurement using ping + a background curl download."""
    baseline_lan = _ping_avg("192.168.1.254")
    baseline_wan = _ping_avg("1.1.1.1")

    proc = None
    loaded_lan: Optional[float] = None
    loaded_wan: Optional[float] = None
    try:
        try:
            proc = subprocess.Popen(
                ["curl", "-o", "/dev/null", "--max-time", "10",
                 "https://cachefly.cachefly.net/100mb.test"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            proc = None
        # Give the download a moment to start saturating the link.
        try:
            time.sleep(0.2)
        except Exception:
            pass
        loaded_lan = _ping_avg("192.168.1.254")
        loaded_wan = _ping_avg("1.1.1.1")
    finally:
        if proc is not None:
            try:
                proc.terminate()
            except Exception:
                pass
            try:
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
                try:
                    proc.wait(timeout=5)
                except Exception:
                    pass

    if any(v is None for v in (baseline_lan, baseline_wan, loaded_lan, loaded_wan)):
        bl = 0.0 if baseline_lan is None else float(baseline_lan)
        ll = 0.0 if loaded_lan is None else float(loaded_lan)
        bw = 0.0 if baseline_wan is None else float(baseline_wan)
        lw = 0.0 if loaded_wan is None else float(loaded_wan)
        delta_lan = (ll - bl) if (baseline_lan is not None and loaded_lan is not None) else 0.0
        delta_wan = (lw - bw) if (baseline_wan is not None and loaded_wan is not None) else 0.0
        return BufferbloatResult(
            baseline_lan_ms=bl,
            loaded_lan_ms=ll,
            delta_lan_ms=round(delta_lan, 9),
            baseline_wan_ms=bw,
            loaded_wan_ms=lw,
            delta_wan_ms=round(delta_wan, 9),
            success=False,
        )

    return compute_bufferbloat(
        baseline_lan=baseline_lan,
        loaded_lan=loaded_lan,
        baseline_wan=baseline_wan,
        loaded_wan=loaded_wan,
    )
