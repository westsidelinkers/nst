"""T1 scheduled capacity probe.

Provides a pure ``compute_probe_result`` aggregator plus ``run_probe`` which
executes curl subprocesses in parallel and implements host rotation with
retry/backoff between CacheFly (primary) and Cloudflare (backup).
"""

from __future__ import annotations

import concurrent.futures
import json
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Optional

# Host name -> base URL. Keys are matched case-insensitively.
_HOST_URLS = {
    "cachefly": "https://cachefly.cachefly.net/100mb.test",
    "cache fly": "https://cachefly.cachefly.net/100mb.test",
    "cloudflare": "https://speed.cloudflare.com/__down",
}


def _is_cachefly(host: Any) -> bool:
    key = str(host).strip().lower()
    return key in ("cachefly", "cache fly", "cachefly.cachefly.net") or "cachefly" in key


def _host_url(host: Any, size_mb: float) -> str:
    key = str(host).strip().lower()
    size_bytes = max(1, int(float(size_mb) * 1024 * 1024))
    if key in _HOST_URLS and key != "cloudflare":
        return _HOST_URLS[key]
    if key == "cloudflare" or "cloudflare" in key:
        return f"https://speed.cloudflare.com/__down?bytes={size_bytes}"
    if str(host).startswith("http://") or str(host).startswith("https://"):
        return str(host)
    # Unknown host: treat as a hostname and build a best-effort URL.
    return f"https://{host}/"


def _to_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _is_success(conn: Any) -> bool:
    if not isinstance(conn, dict):
        return False
    code = conn.get("http_code", conn.get("response_code", conn.get("http_code", 0)))
    code = _to_int(code, 0)
    size = _to_int(conn.get("size_download", 0), 0)
    total = _to_float(conn.get("time_total", 0), 0.0)
    return 200 <= code < 300 and size > 0 and total > 0.0


@dataclass
class ProbeResult:
    timestamp: float = 0.0
    host: str = ""
    down_mbps: float = 0.0
    up_mbps: float = 0.0
    down_mbps_transfer_phase: float = 0.0
    up_mbps_transfer_phase: float = 0.0
    dns_ms: float = 0.0
    tcp_connect_ms: float = 0.0
    tls_ms: float = 0.0
    ttfb_ms: float = 0.0
    total_ms: float = 0.0
    success: bool = False
    error: Optional[str] = None
    bytes_consumed: int = 0


def compute_probe_result(host: str, conn_data: Any, size_mb: float) -> ProbeResult:
    """Aggregate per-connection curl data into a single ProbeResult.

    Pure function: no subprocess or network access.
    """
    conns = list(conn_data) if conn_data else []
    success_conns = [c for c in conns if _is_success(c)]

    success_bytes = sum(_to_int(c.get("size_download", 0), 0) for c in success_conns)
    all_bytes = sum(_to_int(c.get("size_download", 0), 0) for c in conns)
    bytes_consumed = success_bytes if success_conns else all_bytes

    times = [_to_float(c.get("time_total", 0), 0.0) for c in success_conns]
    wall = max(times) if times else 0.0

    if wall > 0.0:
        down_mbps = success_bytes * 8.0 / (wall * 1_000_000.0)
    else:
        down_mbps = 0.0

    if wall > 2.0:
        transfer_time = wall - 2.0
    else:
        transfer_time = wall
    if transfer_time > 0.0:
        down_transfer = success_bytes * 8.0 / (transfer_time * 1_000_000.0)
    else:
        down_transfer = down_mbps

    # Latency metrics averaged over successful connections.
    def _avg(key: str) -> float:
        vals = [_to_float(c.get(key, 0), 0.0) for c in success_conns]
        return (sum(vals) / len(vals)) if vals else 0.0

    dns_s = _avg("time_namelookup")
    connect_s = _avg("time_connect")
    appconnect_s = _avg("time_appconnect")
    start_s = _avg("time_starttransfer")
    total_s = _avg("time_total")

    dns_ms = max(0.0, dns_s * 1000.0)
    tcp_connect_ms = max(0.0, (connect_s - dns_s) * 1000.0)
    tls_ms = max(0.0, (appconnect_s - connect_s) * 1000.0)
    ttfb_ms = max(0.0, (start_s - appconnect_s) * 1000.0)
    total_ms = max(0.0, total_s * 1000.0)

    # Success only if every connection succeeded (no partial / 429 / errors).
    success = len(conns) > 0 and len(success_conns) == len(conns)

    error: Optional[str] = None
    if not success:
        if not conns:
            error = "no connections"
        else:
            for c in conns:
                if _is_success(c):
                    continue
                code = _to_int(c.get("http_code", c.get("response_code", 0)), 0)
                if code == 429:
                    error = "HTTP 429"
                    break
                if code and not (200 <= code < 300):
                    error = f"HTTP {code}"
                    break
                if c.get("error"):
                    error = str(c.get("error"))
                    break
                size = _to_int(c.get("size_download", 0), 0)
                total = _to_float(c.get("time_total", 0), 0.0)
                if size <= 0:
                    error = "no data received"
                    break
                if total <= 0.0:
                    error = "zero elapsed time"
                    break
            if error is None:
                error = "probe failed"

    return ProbeResult(
        timestamp=time.time(),
        host=str(host),
        down_mbps=down_mbps,
        up_mbps=0.0,
        down_mbps_transfer_phase=down_transfer,
        up_mbps_transfer_phase=0.0,
        dns_ms=dns_ms,
        tcp_connect_ms=tcp_connect_ms,
        tls_ms=tls_ms,
        ttfb_ms=ttfb_ms,
        total_ms=total_ms,
        success=success,
        error=error,
        bytes_consumed=int(bytes_consumed),
    )


def _run_connection(host: Any, size_mb: float) -> dict[str, Any]:
    """Run a single curl connection and return its parsed write-out data."""
    size_bytes = max(1, int(float(size_mb) * 1024 * 1024))
    url = _host_url(host, size_mb)
    cmd = ["curl", "-sS", "-o", "/dev/null", "--max-time", "10"]
    if _is_cachefly(host):
        cmd += ["-H", f"Range: bytes=0-{size_bytes - 1}"]
    cmd += ["-w", "%{json}", url]

    try:
        proc = subprocess.run(cmd, timeout=15, capture_output=True, text=True)
    except Exception as exc:  # network failure / timeout / missing curl
        return {
            "http_code": 0,
            "size_download": 0,
            "time_total": 0,
            "time_starttransfer": 0,
            "time_namelookup": 0,
            "time_connect": 0,
            "time_appconnect": 0,
            "error": str(exc),
        }

    # Support both CompletedProcess and dict-like mocked returns.
    if isinstance(proc, dict):
        data = dict(proc)
        stdout = ""
        stderr = ""
        returncode = _to_int(proc.get("returncode", 0), 0)
    else:
        stdout = getattr(proc, "stdout", "") or ""
        stderr = getattr(proc, "stderr", "") or ""
        returncode = _to_int(getattr(proc, "returncode", 0), 0)
        data = None
        if isinstance(stdout, dict):
            data = dict(stdout)
        else:
            text = stdout if isinstance(stdout, str) else str(stdout)
            # Try the whole blob, then the last non-empty line.
            candidates = [text.strip()] + [ln.strip() for ln in reversed(text.splitlines()) if ln.strip()]
            for cand in candidates:
                if not cand:
                    continue
                try:
                    data = json.loads(cand)
                    break
                except (json.JSONDecodeError, ValueError):
                    continue
        if data is None:
            data = {}
            msg = (stderr or stdout or f"curl exit {returncode}").strip()
            if msg:
                data["error"] = msg

    # Normalise types and propagate curl failures.
    if "http_code" not in data and "response_code" not in data:
        data["http_code"] = 200 if returncode == 0 else 0
    for key in ("size_download",):
        if key in data:
            data[key] = _to_int(data.get(key), 0)
    for key in ("time_total", "time_starttransfer", "time_namelookup", "time_connect", "time_appconnect"):
        if key in data:
            data[key] = _to_float(data.get(key), 0.0)

    if returncode != 0 and not data.get("error"):
        data["error"] = (stderr or f"curl exit {returncode}").strip()
    if "http_code" not in data:
        data["http_code"] = 0

    return data


def _attempt_host(host: Any, connections: int, size_mb: float) -> tuple[ProbeResult, bool]:
    """Run all connections for a host. Returns (result, failed)."""
    n = max(1, int(connections))
    conn_data: list[dict[str, Any]] = []
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=n) as executor:
            futures = [executor.submit(_run_connection, host, size_mb) for _ in range(n)]
            for future in concurrent.futures.as_completed(futures):
                try:
                    conn_data.append(future.result())
                except Exception as exc:  # pragma: no cover - defensive
                    conn_data.append(
                        {
                            "http_code": 0,
                            "size_download": 0,
                            "time_total": 0,
                            "time_starttransfer": 0,
                            "time_namelookup": 0,
                            "time_connect": 0,
                            "time_appconnect": 0,
                            "error": str(exc),
                        }
                    )
    except Exception as exc:  # pragma: no cover - defensive
        conn_data.append(
            {
                "http_code": 0,
                "size_download": 0,
                "time_total": 0,
                "time_starttransfer": 0,
                "time_namelookup": 0,
                "time_connect": 0,
                "time_appconnect": 0,
                "error": str(exc),
            }
        )

    result = compute_probe_result(str(host), conn_data, size_mb)
    failed = not result.success
    return result, failed


def run_probe(
    hosts: Any,
    connections: int = 8,
    size_mb: float = 5.0,
    max_retries: int = 3,
    backoff_base: float = 1.0,
) -> ProbeResult:
    """Run the T1 probe with host rotation, retry and exponential backoff.

    Tries each host in order. On failure (429 or any network/transport error)
    retries the same host up to ``max_retries`` times with exponential backoff
    before falling back to the next host.
    """
    if isinstance(hosts, str):
        host_list = [hosts]
    elif hosts is None:
        host_list = []
    else:
        host_list = list(hosts)
    if not host_list:
        host_list = ["cacheFly", "cloudflare"]

    last_result: Optional[ProbeResult] = None
    last_error: Optional[str] = None

    for host in host_list:
        for attempt in range(max_retries + 1):
            result, failed = _attempt_host(host, connections, size_mb)
            last_result = result
            last_error = result.error or last_error
            if not failed:
                return result
            if attempt < max_retries:
                try:
                    time.sleep(backoff_base * (2 ** attempt))
                except Exception:
                    pass
        # Fall back to next host.

    if last_result is not None:
        last_result.success = False
        if last_result.error is None:
            last_result.error = last_error or "all hosts failed"
        return last_result

    return ProbeResult(
        timestamp=time.time(),
        host="",
        success=False,
        error="no hosts configured",
    )
