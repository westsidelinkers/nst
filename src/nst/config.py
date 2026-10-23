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
