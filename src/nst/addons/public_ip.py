"""Public IP addon module."""

from __future__ import annotations

import json
import urllib.request
from typing import Any

from nst.addons.base import AddonModule


class PublicIpAddon(AddonModule):
    name = "public_ip"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._data: dict = {}

    def update(self, sample: Any = None) -> dict:
        # Prefer sample-provided value when available.
        ip = None
        try:
            ip = getattr(sample, "public_ip", None) if sample is not None else None
        except Exception:
            ip = None
        data: dict = {}
        if ip:
            data["ip"] = ip
        # Fetch details from ifconfig.co (best effort).
        try:
            req = urllib.request.Request(
                "https://ifconfig.co/json",
                headers={"Accept": "application/json", "User-Agent": "nst"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            info = json.loads(raw) if raw else {}
            if isinstance(info, dict):
                if "ip" in info and "ip" not in data:
                    data["ip"] = info.get("ip")
                for key in ("country", "city", "asn", "org", "hostname"):
                    if key in info and info.get(key) is not None:
                        data[key] = info.get(key)
                # ISP may be under various keys.
                for isp_key in ("org", "asn_org", "isp", "network"):
                    if isp_key in info and info.get(isp_key):
                        data.setdefault("isp", info.get(isp_key))
                        break
        except Exception:
            pass
        # Fallback: use sample public_ip if fetch failed.
        if "ip" not in data and ip:
            data["ip"] = ip
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
        ip = d.get("ip", "unknown")
        isp = d.get("isp") or d.get("org") or ""
        label = f"Public IP  {ip}"
        if isp:
            label += f"  ({isp})"
        return Gtk.Label(label=label, xalign=0)


__all__ = ["PublicIpAddon"]
