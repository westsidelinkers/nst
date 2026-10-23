"""Collapsed panel tiles with data-driven musical bars."""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

try:
    from nst.ui.css import animations_enabled as _animations_enabled
except Exception:
    def _animations_enabled(*a, **k):
        return True

try:
    from gi.repository import GLib
except Exception:  # pragma: no cover - environment dependent
    GLib = None

# State CSS class names we manage (normalized + common aliases).
_STATE_CLASSES = {
    "good", "warn", "bad", "healthy", "warning", "error",
    "critical", "ok", "nst-good", "nst-warn", "nst-bad",
}
_WIDTH_CLASSES = {f"nst-bar--w-{i}" for i in range(0, 105, 5)}


def _attr(sample, *names, default=None):
    if sample is None:
        return default
    if isinstance(sample, dict):
        for name in names:
            if name in sample and sample[name] is not None:
                return sample[name]
        return default
    for name in names:
        if hasattr(sample, name):
            value = getattr(sample, name)
            if value is not None:
                return value
    return default


def _to_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_state(state):
    if state is None:
        return None
    s = str(state).strip().lower()
    mapping = {
        "healthy": "good",
        "ok": "good",
        "success": "good",
        "warning": "warn",
        "error": "bad",
        "critical": "bad",
        "danger": "bad",
    }
    return mapping.get(s, s)


class Tile(Gtk.Box):
    """A single collapsed panel tile: label, musical bar, value, subtitle."""

    def __init__(self, name, *args, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=2, *args, **kwargs)
        self.name = name
        self.tile_name = name

        self.label = Gtk.Label(label=str(name))
        self.label.add_css_class("nst-tile-label")
        self.label.set_xalign(0.0)

        self.bar = Gtk.Box()
        self.bar.add_css_class("nst-bar")
        self.bar.set_size_request(-1, 4)

        self.value = Gtk.Label(label="\u2014")
        self.value.add_css_class("nst-tile-value")
        self.value.set_xalign(0.0)

        self.subtitle = Gtk.Label(label="")
        self.subtitle.add_css_class("nst-tile-subtitle")
        self.subtitle.set_xalign(0.0)

        self.append(self.label)
        self.append(self.bar)
        self.append(self.value)
        self.append(self.subtitle)

        self.add_css_class("nst-tile")

        # Convenience aliases used by various callers/tests.
        self.title_label = self.label
        self.name_label = self.label
        self.value_label = self.value
        self.subtitle_label = self.subtitle
        self.bar_box = self.bar

    def set_state(self, state):
        state = _normalize_state(state)
        if state is None:
            return self
        # Remove managed state classes from both the tile and its bar.
        for css_class in _STATE_CLASSES:
            try:
                self.remove_css_class(css_class)
            except Exception:
                pass
            try:
                self.bar.remove_css_class(css_class)
            except Exception:
                pass
        for css_class in (state, f"nst-{state}", f"nst-state-{state}"):
            try:
                self.add_css_class(css_class)
            except Exception:
                pass
            try:
                self.bar.add_css_class(css_class)
            except Exception:
                pass
        return self

    def flash(self):
        for widget in (self, self.bar):
            try:
                widget.add_css_class("flash")
                widget.add_css_class("nst-flash")
            except Exception:
                pass
        return self


class TileGrid(Gtk.Grid):
    """3x2 grid of six collapsed panel tiles."""

    TILE_NAMES = ("DOWN", "UP", "PING", "SIGNAL", "CPU", "DISK")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tiles = {}
        self._state = None
        self.config = None
        self.reduced_motion = None
        self.on_battery = False
        self.battery_pct = 100.0
        self.battery_threshold = 30
        self._animate = True
        self._sample = None
        self.add_css_class("nst-tile-grid")

        for index, name in enumerate(self.TILE_NAMES):
            tile = Tile(name)
            self.tiles[name] = tile
            column = index % 3
            row = index // 3
            try:
                self.attach(tile, column, row, 1, 1)
            except Exception:
                pass

    def _reduced_motion_active(self):
        if self.reduced_motion is not None:
            return bool(self.reduced_motion)
        try:
            settings = None
            try:
                from gi.repository import Gtk as _Gtk
                settings = _Gtk.Settings.get_default()
            except Exception:
                settings = None
            if settings is not None:
                return bool(getattr(settings, "gtk_interface_reduced_motion", False))
        except Exception:
            pass
        return False

    def animations_enabled(self, sample=None, reduced_motion=None, on_battery=None,
                           battery_pct=None, battery_threshold=None, config=None):
        cfg = config if config is not None else self.config
        if sample is not None:
            try:
                if on_battery is None:
                    v = _attr(sample, "on_battery", default=None)
                    if v is not None:
                        on_battery = bool(v)
                if battery_pct is None:
                    v = _attr(sample, "battery_pct", default=None)
                    if v is not None:
                        battery_pct = _to_float(v, self.battery_pct)
            except Exception:
                pass
        rm = self._reduced_motion_active() if reduced_motion is None else bool(reduced_motion)
        ob = self.on_battery if on_battery is None else bool(on_battery)
        bp = self.battery_pct if battery_pct is None else _to_float(battery_pct, self.battery_pct)
        bt = self.battery_threshold if battery_threshold is None else battery_threshold
        try:
            if cfg is not None:
                bt = getattr(cfg, "battery_threshold", bt)
                if getattr(cfg, "animation_enabled", True) is False:
                    return False
        except Exception:
            pass
        return _animations_enabled(reduced_motion=rm, on_battery=ob, battery_pct=bp,
                                 battery_threshold=bt, config=cfg)

    def animation_enabled(self, *args, **kwargs):
        return self.animations_enabled(*args, **kwargs)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def update(self, sample=None, verdict=None):
        """Update tile values, bar heights and colors from a sample."""
        self._sample = sample
        if sample is not None:
            try:
                v = _attr(sample, "on_battery", default=None)
                if v is not None:
                    self.on_battery = bool(v)
                v = _attr(sample, "battery_pct", default=None)
                if v is not None:
                    self.battery_pct = _to_float(v, self.battery_pct)
            except Exception:
                pass
        self._animate = self.animations_enabled(sample=sample)
        # Determine an overall state from the verdict when provided.
        verdict_str = None
        if verdict is not None:
            verdict_str = getattr(verdict, "value", verdict)
            verdict_str = str(verdict_str)

        vmap = {
            "HEALTHY": "good",
            "ISP_LIMITED": "warn",
            "HIGH_LATENCY": "warn",
            "RADIO_DEGRADED": "bad",
        }
        overall = vmap.get(verdict_str.upper() if verdict_str else "", None)
        if overall is not None:
            self.set_state(overall)

        # DOWN / UP (throughput)
        rx_bps = _to_float(_attr(sample, "rx_bps", "rx_rate_bps", "download_bps", default=0.0))
        tx_bps = _to_float(_attr(sample, "tx_bps", "tx_rate_bps", "upload_bps", default=0.0))
        rx_mbps = rx_bps / 1e6
        tx_mbps = tx_bps / 1e6

        def throughput_state(mbps):
            if mbps >= 15:
                return "good"
            if mbps >= 5:
                return "warn"
            return "bad"

        self._update_tile(
            "DOWN",
            value=f"{rx_mbps:.1f} M",
            subtitle="down",
            pct=min(100.0, rx_mbps / 38.0 * 100.0) if rx_mbps else 0.0,
            state=throughput_state(rx_mbps),
        )
        self._update_tile(
            "UP",
            value=f"{tx_mbps:.1f} M",
            subtitle="up",
            pct=min(100.0, tx_mbps / 38.0 * 100.0) if tx_mbps else 0.0,
            state=throughput_state(tx_mbps),
        )

        # PING (latency, inverse scale)
        ping_avg = _to_float(_attr(sample, "ping_avg_ms", "ping_ms", "rtt_ms", default=0.0))
        ping_pct = max(0.0, min(100.0, 100.0 - ping_avg))
        if ping_avg <= 50:
            ping_state = "good"
        elif ping_avg <= 100:
            ping_state = "warn"
        else:
            ping_state = "bad"
        self._update_tile(
            "PING",
            value=f"{ping_avg:.0f} ms",
            subtitle="latency",
            pct=ping_pct,
            state=ping_state,
        )

        # SIGNAL (dBm, -90..-50 scale)
        signal_dbm = _to_float(_attr(sample, "signal_dbm", "signal", default=0.0))
        if signal_dbm == 0.0 and not _attr(sample, "signal_dbm", "signal", default=None):
            signal_dbm = 0.0
        signal_pct = max(0.0, min(100.0, (signal_dbm + 90.0) / 40.0 * 100.0))
        if signal_dbm >= -67:
            signal_state = "good"
        elif signal_dbm >= -75:
            signal_state = "warn"
        else:
            signal_state = "bad"
        self._update_tile(
            "SIGNAL",
            value=f"{signal_dbm:.0f} dBm",
            subtitle="signal",
            pct=signal_pct,
            state=signal_state,
        )

        # CPU (usage percent, falling back to temperature)
        cpu_usage = _attr(sample, "cpu_pct", "cpu_percent", "cpu_usage", "cpu", default=None)
        cpu_temp = _attr(sample, "cpu_temp_c", "cpu_temp", default=None)
        if cpu_usage is not None:
            cpu = _to_float(cpu_usage)
            cpu_value = f"{cpu:.0f}%"
        elif cpu_temp is not None:
            cpu = _to_float(cpu_temp)
            cpu_value = f"{cpu:.0f}\u00b0C"
        else:
            cpu = 0.0
            cpu_value = "\u2014"
        if cpu <= 70:
            cpu_state = "good"
        elif cpu <= 90:
            cpu_state = "warn"
        else:
            cpu_state = "bad"
        self._update_tile(
            "CPU",
            value=cpu_value,
            subtitle="cpu",
            pct=max(0.0, min(100.0, cpu)),
            state=cpu_state,
        )

        # DISK (used/available space)
        disk_free = _to_float(
            _attr(sample, "disk_free_pct", "disk_pct", "disk_free_percent", "disk_percent", default=0.0)
        )
        # If a usage value was provided instead, convert.
        if "disk_free_pct" not in (sample if isinstance(sample, dict) else {}) and disk_free == 0.0:
            usage = _attr(sample, "disk_usage_pct", "disk_usage_percent", "disk_usage", default=None)
            if usage is not None:
                disk_free = max(0.0, 100.0 - _to_float(usage))
        disk_total_bytes = _attr(sample, "disk_total_bytes", default=None)
        disk_used_bytes = _attr(sample, "disk_used_bytes", default=None)
        disk_free_bytes = _attr(sample, "disk_free_bytes", default=None)
        if disk_total_bytes is not None and disk_used_bytes is not None and disk_free_bytes is not None:
            try:
                total_gb = _to_float(disk_total_bytes) / (1024.0 ** 3)
                used_gb = _to_float(disk_used_bytes) / (1024.0 ** 3)
                free_gb = _to_float(disk_free_bytes) / (1024.0 ** 3)
                disk_value = f"{used_gb:.1f}/{total_gb:.1f} GB"
                disk_subtitle = f"{free_gb:.1f} GB free"
            except Exception:
                disk_value = f"{disk_free:.0f}%"
                disk_subtitle = "free"
        else:
            # Fall back to free percentage when byte counts are unavailable.
            disk_value = f"{disk_free:.0f}%"
            disk_subtitle = "free"
        if disk_free >= 20:
            disk_state = "good"
        elif disk_free >= 10:
            disk_state = "warn"
        else:
            disk_state = "bad"
        self._update_tile(
            "DISK",
            value=disk_value,
            subtitle=disk_subtitle,
            pct=max(0.0, min(100.0, disk_free)),
            state=disk_state,
        )

        return self

    def _update_tile(self, name, value=None, subtitle=None, pct=0.0, state=None):
        tile = self.tiles.get(name)
        if tile is None:
            return
        if value is not None:
            try:
                tile.value.set_label(str(value))
            except Exception:
                tile.value.set_text(str(value))
        if subtitle is not None:
            try:
                tile.subtitle.set_label(str(subtitle))
            except Exception:
                tile.subtitle.set_text(str(subtitle))
        self._set_bar(tile, pct, state)

    def _set_bar(self, tile, pct, state):
        pct = max(0.0, min(100.0, float(pct or 0.0)))
        # Width classes (CSS) + inline height request.
        for css_class in _WIDTH_CLASSES:
            try:
                tile.bar.remove_css_class(css_class)
            except Exception:
                pass
        bucket = int(round(pct / 5.0) * 5)
        bucket = max(0, min(100, bucket))
        try:
            tile.bar.add_css_class(f"nst-bar--w-{bucket}")
        except Exception:
            pass
        if state is not None:
            tile.set_state(state)
            try:
                tile.bar.add_css_class(_normalize_state(state))
            except Exception:
                pass
        try:
            tile.bar.set_size_request(-1, max(2, int(40 * pct / 100.0)))
        except Exception:
            pass
        try:
            if getattr(self, "_animate", True):
                tile.bar.add_css_class("nst-animate")
            else:
                tile.bar.remove_css_class("nst-animate")
        except Exception:
            pass
        try:
            tile.bar.set_tooltip_text(f"{pct:.0f}%")
        except Exception:
            pass

    def set_state(self, state):
        state = _normalize_state(state)
        if state is None:
            return self
        self._state = state
        for tile in self.tiles.values():
            try:
                tile.set_state(state)
            except Exception:
                pass
        for css_class in _STATE_CLASSES:
            try:
                self.remove_css_class(css_class)
            except Exception:
                pass
        for css_class in (state, f"nst-{state}", f"nst-state-{state}"):
            try:
                self.add_css_class(css_class)
            except Exception:
                pass
        return self

    def flash(self):
        try:
            self.add_css_class("flash")
            self.add_css_class("nst-flash")
        except Exception:
            pass
        for tile in self.tiles.values():
            try:
                tile.flash()
            except Exception:
                pass

        if GLib is not None:
            try:
                GLib.timeout_add(300, self._unflash)
            except Exception:
                pass
        return self

    def _unflash(self):
        try:
            self.remove_css_class("flash")
            self.remove_css_class("nst-flash")
        except Exception:
            pass
        for tile in self.tiles.values():
            for widget in (tile, tile.bar):
                for css_class in ("flash", "nst-flash"):
                    try:
                        widget.remove_css_class(css_class)
                    except Exception:
                        pass
        return False


__all__ = ["Tile", "TileGrid"]
