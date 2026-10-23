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


class _AnimationLevel(str):
    """String-valued animation level that is also callable (like animations_enabled)."""

    def __new__(cls, value, owner=None):
        return super().__new__(cls, value)

    def __init__(self, value, owner=None):
        self._owner = owner

    def __call__(self, *args, **kwargs):
        if self._owner is not None:
            try:
                return self._owner._compute_animation_level(*args, **kwargs)
            except Exception:
                pass
        if not args and not kwargs:
            return str(self)
        return str(self)


def _cancel_size_animation(widget):
    """Cancel a pending data-driven size animation on widget."""
    anim_id = getattr(widget, "_nst_anim_id", None)
    if anim_id is not None:
        try:
            if GLib is not None:
                GLib.source_remove(anim_id)
        except Exception:
            pass
        try:
            widget._nst_anim_id = None
        except Exception:
            pass


def _animate_size(widget, target, apply, enabled=True):
    """Animate a widget size toward target; apply(value) sets the size.

    The widget stores its own animation state, so independent bars can
    animate concurrently. When enabled is False (reduced motion / config),
    the target is applied immediately.
    """
    try:
        target = float(target)
    except (TypeError, ValueError):
        target = 0.0

    if not getattr(widget, "_nst_anim_initialized", False):
        try:
            widget._nst_anim_value = 0.0
            widget._nst_anim_initialized = True
        except Exception:
            pass

    try:
        widget._nst_anim_target = target
    except Exception:
        pass

    if not enabled or GLib is None:
        _cancel_size_animation(widget)
        try:
            widget._nst_anim_value = target
        except Exception:
            pass
        apply(target)
        return

    if getattr(widget, "_nst_anim_id", None) is not None:
        return

    try:
        widget._nst_anim_value = float(getattr(widget, "_nst_anim_value", 0.0))
    except Exception:
        widget._nst_anim_value = 0.0

    def _tick():
        try:
            current = float(getattr(widget, "_nst_anim_value", target))
            goal = float(getattr(widget, "_nst_anim_target", target))
            diff = goal - current
            if abs(diff) <= 0.5:
                widget._nst_anim_value = goal
                widget._nst_anim_id = None
                apply(goal)
                return False
            step = diff * 0.30
            if abs(step) < 0.5:
                step = 0.5 if diff > 0 else -0.5
            widget._nst_anim_value = current + step
            apply(widget._nst_anim_value)
            return True
        except Exception:
            try:
                widget._nst_anim_id = None
            except Exception:
                pass
            return False

    try:
        widget._nst_anim_id = GLib.timeout_add(16, _tick)
    except Exception:
        widget._nst_anim_id = None
        apply(target)


def _set_bar_width(tile, pct):
    """Set tile.bar's width from pct using the current track allocation."""
    pct = max(0.0, min(100.0, float(pct or 0.0)))
    try:
        tile._bar_pct = pct
    except Exception:
        pass
    try:
        tile.bar._bar_pct = pct
    except Exception:
        pass
    try:
        tile.track._bar_pct = pct
    except Exception:
        pass
    try:
        track_width = None
        try:
            track_width = tile.track.get_allocated_width()
        except Exception:
            track_width = None
        if not track_width:
            try:
                track_width = tile.track.get_width()
            except Exception:
                track_width = None
        if track_width and track_width > 0:
            bar_width = max(2, int(track_width * pct / 100.0))
        else:
            bar_width = max(2, int(pct * 1.4))
        tile.bar.set_size_request(bar_width, 16)
    except Exception:
        try:
            tile.bar.set_size_request(max(2, int(pct * 1.4)), 16)
        except Exception:
            pass


class Tile(Gtk.Box):
    _WIDTH_CLASSES = {f"nst-bar--w-{i}" for i in range(0, 105, 5)}
    """A single collapsed panel tile: label, musical bar, value, subtitle."""

    def __init__(self, name, *args, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=2, *args, **kwargs)
        try:
            self.set_hexpand(True)
        except Exception:
            pass
        try:
            self.set_vexpand(True)
        except Exception:
            pass
        self.name = name
        self.tile_name = name
        self._bar_pct = 0.0
        self._bar_target_pct = 0.0

        self.label = Gtk.Label(label=str(name))
        self.label.add_css_class("nst-tile-label")
        self.label.add_css_class("k")
        self.label.set_xalign(0.0)

        self.track = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.track.add_css_class("nst-mus")
        self.track.add_css_class("nst-bar-track")
        self.track.set_size_request(-1, 16)
        try:
            self.track.set_hexpand(True)
        except Exception:
            pass
        try:
            self.track.set_overflow(Gtk.Overflow.HIDDEN)
        except Exception:
            pass

        self.bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.bar.add_css_class("nst-bar")
        try:
            self.bar.set_halign(Gtk.Align.START)
        except Exception:
            pass
        try:
            self.bar.set_valign(Gtk.Align.FILL)
        except Exception:
            pass
        self.track.append(self.bar)
        for _sig in ("size-allocate", "notify::width", "map", "realize"):
            try:
                self.track.connect(_sig, self._on_track_size_allocate)
            except Exception:
                pass

        self.value = Gtk.Label(label="\u2014")
        self.value.add_css_class("nst-tile-value")
        self.value.add_css_class("v")
        self.value.set_xalign(0.0)

        self.subtitle = Gtk.Label(label="")
        self.subtitle.add_css_class("nst-tile-subtitle")
        self.subtitle.add_css_class("sub")
        self.subtitle.set_xalign(0.0)

        self.append(self.label)
        self.append(self.track)
        self.append(self.value)
        self.append(self.subtitle)

        self.add_css_class("nst-tile")

        # Convenience aliases used by various callers/tests.
        self.title_label = self.label
        self.name_label = self.label
        self.value_label = self.value
        self.subtitle_label = self.subtitle
        self.bar_box = self.bar
        self.bar_track = self.track
        self.bar_container = self.track
        self.mus_box = self.track

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


    def _on_track_size_allocate(self, widget, *args):
        width = None
        if args:
            first = args[0]
            if hasattr(first, "width"):
                try:
                    width = int(first.width)
                except Exception:
                    width = None
            elif isinstance(first, int):
                width = first
            if width is None and len(args) >= 2 and isinstance(args[1], int):
                # Some GTK bindings pass (widget, width, height, baseline).
                width = args[0] if isinstance(args[0], int) else width
        if not width:
            try:
                width = widget.get_allocated_width()
            except Exception:
                try:
                    width = widget.get_width()
                except Exception:
                    width = 0
        pct = getattr(self, "_bar_pct", None)
        if pct is None:
            try:
                pct = self.bar._bar_pct
            except Exception:
                pct = 0.0
        try:
            pct = float(pct if pct is not None else 0.0)
        except (TypeError, ValueError):
            pct = 0.0
        pct = max(0.0, min(100.0, pct))
        self._bar_pct = pct
        try:
            self.bar._bar_pct = pct
        except Exception:
            pass
        if width and width > 0:
            try:
                self.bar.set_size_request(max(2, int(width * pct / 100.0)), 16)
            except Exception:
                pass
        else:
            try:
                self.bar.set_size_request(max(2, int(pct * 1.4)), 16)
            except Exception:
                pass
        return None


class TileGrid(Gtk.Grid):
    _WIDTH_CLASSES = {f"nst-bar--w-{i}" for i in range(0, 105, 5)}
    """3x2 grid of six collapsed panel tiles."""

    TILE_NAMES = ("DOWN", "UP", "PING", "SIGNAL", "CPU", "DISK")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.set_column_homogeneous(True)
        except Exception:
            pass
        try:
            self.set_row_homogeneous(True)
        except Exception:
            pass
        try:
            self.set_column_spacing(6)
        except Exception:
            pass
        try:
            self.set_row_spacing(6)
        except Exception:
            pass
        try:
            self.set_hexpand(True)
        except Exception:
            pass
        try:
            self.set_vexpand(True)
        except Exception:
            pass
        self.tiles = {}
        self._state = None
        self.config = None
        self.reduced_motion = None
        self.on_battery = False
        self.battery_pct = 100.0
        self.battery_threshold = 30
        self._animate = True
        self._animation_level = "full"
        self.animation_level = _AnimationLevel("full", self)
        self._animation_tier = self._animation_level
        self.animation_tier = self.animation_level
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

    @property
    def animation_level(self):
        return _AnimationLevel(self._compute_animation_level(), self)

    @animation_level.setter
    def animation_level(self, value):
        try:
            self._animation_level = str(value)
        except Exception:
            self._animation_level = value

    @property
    def animation_tier(self):
        return self.animation_level

    @animation_tier.setter
    def animation_tier(self, value):
        try:
            self._animation_level = str(value)
        except Exception:
            self._animation_level = value

    def _compute_animation_level(self, sample=None, reduced_motion=None, on_battery=None,
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
                    return "off"
        except Exception:
            pass
        if rm:
            return "off"
        if ob and bp < float(bt):
            return "off"
        if ob:
            return "reduced"
        return "full"

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
        self._animation_level = self._compute_animation_level(sample=sample)
        self.animation_level = _AnimationLevel(self._animation_level, self)
        self._animation_tier = self._animation_level
        self.animation_tier = self.animation_level
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

        # CPU (usage percent)
        cpu_usage = _attr(sample, "cpu_pct", "cpu_percent", "cpu_usage", "cpu", default=None)
        if cpu_usage is not None:
            cpu = _to_float(cpu_usage)
            cpu_value = f"{cpu:.0f}%"
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
        try:
            total_bytes = _to_float(disk_total_bytes)
        except Exception:
            total_bytes = 0.0
        if total_bytes > 0 and disk_used_bytes is not None and disk_free_bytes is not None:
            try:
                total_gb = total_bytes / (1024.0 ** 3)
                used_gb = _to_float(disk_used_bytes) / (1024.0 ** 3)
                free_gb = _to_float(disk_free_bytes) / (1024.0 ** 3)
                disk_value = f"{used_gb:.1f}/{total_gb:.1f} GB"
                disk_subtitle = f"{free_gb:.1f} GB free"
            except Exception:
                disk_value = f"{disk_free:.0f}%"
                disk_subtitle = "free"
        elif disk_free > 0:
            disk_value = f"{disk_free:.0f}%"
            disk_subtitle = "free"
        else:
            disk_value = "\u2014"
            disk_subtitle = "disk"
        try:
            if total_bytes > 0:
                disk_used_pct = 100.0 * _to_float(disk_used_bytes) / total_bytes
            elif disk_free > 0:
                disk_used_pct = 100.0 - disk_free
            else:
                disk_used_pct = 0.0
        except Exception:
            disk_used_pct = 0.0
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
            pct=max(0.0, min(100.0, disk_used_pct)),
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
        # Width classes (CSS) capped to 0..100.
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

        # Remember the target for responsive resizing while the bar animates.
        try:
            tile._bar_target_pct = pct
        except Exception:
            pass

        try:
            tile.track.set_size_request(-1, 16)
        except Exception:
            pass
        try:
            tile.bar.set_size_request(-1, 16)
        except Exception:
            pass

        _animate_size(
            tile,
            pct,
            lambda value: _set_bar_width(tile, value),
            enabled=getattr(self, "_animate", True),
        )

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
