"""Bufferbloat addon module."""

from __future__ import annotations

import time
from typing import Any

from nst.addons.base import AddonModule


class BufferbloatAddon(AddonModule):
    name = "bufferbloat"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._result: Any = None
        self._data: dict = {}
        self._cache_ttl: float = 300.0
        try:
            if self.config is not None:
                self._cache_ttl = float(getattr(self.config, "bufferbloat_cache_ttl", self._cache_ttl))
        except Exception:
            pass
        self._cached_data: dict = {}
        self._last_attempt: float = 0.0

    def update(self, sample: Any = None) -> dict:
        now = time.monotonic()
        # Return cached result within TTL to avoid running the (expensive)
        # bufferbloat measurement on every T0 sample.
        if self._last_attempt > 0 and (now - self._last_attempt) < self._cache_ttl:
            self._data = dict(self._cached_data)
            return dict(self._data)

        self._last_attempt = now
        try:
            from nst.measurement.bufferbloat import measure_bufferbloat

            result = measure_bufferbloat()
            self._result = result
            data = {
                "baseline_lan_ms": getattr(result, "baseline_lan_ms", 0.0),
                "loaded_lan_ms": getattr(result, "loaded_lan_ms", 0.0),
                "delta_lan_ms": getattr(result, "delta_lan_ms", 0.0),
                "baseline_wan_ms": getattr(result, "baseline_wan_ms", 0.0),
                "loaded_wan_ms": getattr(result, "loaded_wan_ms", 0.0),
                "delta_wan_ms": getattr(result, "delta_wan_ms", 0.0),
                "success": getattr(result, "success", False),
            }
            self._data = data
            self._cached_data = dict(data)
            return data
        except Exception:
            # Throttle failures too: keep any previous cached data.
            if self._cached_data:
                self._data = dict(self._cached_data)
                return dict(self._data)
            return dict(self._data)

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
        text = (
            f"Bufferbloat  LAN +{d.get('delta_lan_ms', 0):.1f} ms  "
            f"WAN +{d.get('delta_wan_ms', 0):.1f} ms"
        )
        return Gtk.Label(label=text, xalign=0)


__all__ = ["BufferbloatAddon"]
