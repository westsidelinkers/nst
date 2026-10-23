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
