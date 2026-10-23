"""Bufferbloat addon module."""

from __future__ import annotations

from typing import Any

from nst.addons.base import AddonModule


class BufferbloatAddon(AddonModule):
    name = "bufferbloat"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._result: Any = None
        self._data: dict = {}

    def update(self, sample: Any = None) -> dict:
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
            return data
        except Exception:
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
