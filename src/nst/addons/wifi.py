"""WiFi addon module."""

from __future__ import annotations

import re
import subprocess
from typing import Any

from nst.addons.base import AddonModule

from nst.measurement.t0_passive import parse_iw_link, parse_iw_station_dump


def _run(cmd: list[str], timeout: int = 10) -> str:
    try:
        res = subprocess.run(cmd, timeout=timeout, capture_output=True, text=True)
    except Exception:
        return ""
    out = getattr(res, "stdout", "") or ""
    err = getattr(res, "stderr", "") or ""
    return (out if isinstance(out, str) else str(out)) + "\n" + (err if isinstance(err, str) else str(err))


def _detect_interface() -> str:
    out = _run(["iw", "dev"])
    m = re.search(r"Interface\s+(\S+)", out)
    if m:
        return m.group(1)
    return "wlp2s0"


class WifiAddon(AddonModule):
    name = "wifi"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._data: dict = {}
        self.interface = getattr(self, "interface", None) or "wlp2s0"
        # allow config to specify
        try:
            cfg = self.config
            if cfg is not None:
                iface = getattr(cfg, "interface", None)
                if iface:
                    self.interface = iface
        except Exception:
            pass

    def update(self, sample: Any = None) -> dict:
        data: dict = {}
        iface = self.interface
        if iface == "wlp2s0":
            try:
                iface = _detect_interface() or iface
                self.interface = iface
            except Exception:
                pass

        # sample signal fallback
        try:
            if sample is not None:
                sd = getattr(sample, "signal_dbm", None)
                if sd is not None:
                    data["signal_dbm"] = float(sd)
        except Exception:
            pass

        try:
            out = _run(["iw", "dev", iface, "link"])
            info = parse_iw_link(out)
            if "ssid" in info:
                data["ssid"] = info["ssid"]
            if "signal_dbm" in info:
                data["signal_dbm"] = float(info["signal_dbm"])
            if "rx_bitrate_mbps" in info:
                data["rx_bitrate_mbps"] = float(info["rx_bitrate_mbps"])
            if "tx_bitrate_mbps" in info:
                data["tx_bitrate_mbps"] = float(info["tx_bitrate_mbps"])
            if "freq_mhz" in info:
                data["freq_mhz"] = float(info["freq_mhz"])
        except Exception:
            pass

        try:
            out = _run(["iw", "dev", iface, "station", "dump"])
            info = parse_iw_station_dump(out)
            if "signal_dbm" in info and "signal_dbm" not in data:
                data["signal_dbm"] = float(info["signal_dbm"])
            for key in ("tx_retries", "tx_failed", "beacon_loss", "rx_drop_misc", "signal_avg_dbm"):
                if key in info:
                    data[key] = info[key]
        except Exception:
            pass

        self._data = data
        return dict(data)

    def render(self) -> Any:
        import os
        if not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
            return None
        try:
            import gi

            gi.require_version("Gtk", "4.0")
            from gi.repository import Gtk
        except Exception:
            return None
        d = self._data or {}
        ssid = d.get("ssid", "")
        sig = d.get("signal_dbm", 0)
        rx = d.get("rx_bitrate_mbps", 0)
        tx = d.get("tx_bitrate_mbps", 0)
        drops = d.get("rx_drop_misc", 0)
        text = f"WiFi  {ssid}  {sig} dBm  ↓{rx:.0f} ↑{tx:.0f} Mbps"
        if drops:
            text += f"  drops {drops}"
        return Gtk.Label(label=text, xalign=0)


__all__ = ["WifiAddon"]
