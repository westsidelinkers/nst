"""Expanded detail panel with hero, bars, latency, devices, actions."""

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

try:
    from nst.ui.heartbeat import HeartbeatGraph
except Exception:  # pragma: no cover - environment dependent
    HeartbeatGraph = None

try:
    from nst.ui.tiles import _normalize_state as _normalize_tile_state
except Exception:  # pragma: no cover - environment dependent
    def _normalize_tile_state(state):
        return None if state is None else str(state).strip().lower()

try:
    from nst.ui.tiles import _animate_size as _animate_bar_size
except Exception:  # pragma: no cover - environment dependent
    def _animate_bar_size(widget, target, apply, enabled=True):
        apply(target)


_STATE_CLASSES = {"good", "warn", "bad", "healthy", "warning", "error",
                  "critical", "ok", "nst-good", "nst-warn", "nst-bad"}
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
        if isinstance(value, bool):
            return float(int(value))
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


def _verdict_str(verdict):
    if verdict is None:
        return None
    v = getattr(verdict, "value", verdict)
    try:
        return str(v)
    except Exception:
        return None


class _BarRow:
    """Small container holding a label, musical bar and value label."""

    def __init__(self, name):
        self.name = name
        self.row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.label = Gtk.Label(label=str(name))
        self.label.set_xalign(0.0)
        self.bar = Gtk.Box()
        self.bar.add_css_class("nst-bar")
        self.bar.set_size_request(-1, 4)
        self.value = Gtk.Label(label="\u2014")
        self.value.set_xalign(1.0)
        self.row.append(self.label)
        self.row.append(self.bar)
        self.row.append(self.value)
        self.row.add_css_class("nst-expanded-bar-row")


class BarsSection(Gtk.Box):
    """A vertical section that also behaves like a mapping of bar widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4, *args, **kwargs)
        self._bars = {}
        self.bars = self._bars

    def add_bar(self, name, bar_widget):
        self._bars[name] = bar_widget

    def __getitem__(self, key):
        return self._bars[key]

    def __contains__(self, key):
        return key in self._bars

    def __len__(self):
        return len(self._bars)

    def __iter__(self):
        return iter(self._bars)

    def items(self):
        return self._bars.items()

    def values(self):
        return self._bars.values()

    def keys(self):
        return self._bars.keys()


class ExpandedPanel(Gtk.Box):
    """Expanded detail panel: hero, heartbeat, bars, latency, devices, actions."""

    def __init__(self, *args, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10, *args, **kwargs)
        self.add_css_class("nst-expanded-panel")

        self._sample = None
        self._verdict = None
        self._probe_result = None
        self._devices = []
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

        # ---- Hero section ----
        self.hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.hero.add_css_class("nst-expanded-hero")
        self.hero_title = Gtk.Label(label="Throughput")
        self.hero_title.set_xalign(0.0)
        self.hero_value = Gtk.Label(label="\u2014")
        self.hero_value.add_css_class("nst-hero-value")
        self.hero_value.set_xalign(0.0)
        self.verdict_label = Gtk.Label(label="\u2014")
        self.verdict_label.add_css_class("nst-verdict")
        self.verdict_label.set_xalign(0.0)
        self.hero.append(self.hero_title)
        self.hero.append(self.hero_value)
        self.hero.append(self.verdict_label)
        # aliases
        self.hero_label = self.hero_value
        self.throughput_label = self.hero_value
        self.verdict_block = self.verdict_label
        self.hero_number = self.hero_value

        # ---- Heartbeat section ----
        if HeartbeatGraph is not None:
            try:
                self.heartbeat = HeartbeatGraph()
            except Exception:
                self.heartbeat = Gtk.Box()
        else:
            self.heartbeat = Gtk.Box()
        self.heartbeat.add_css_class("nst-expanded-heartbeat")
        self.heartbeat_graph = self.heartbeat
        self.graph = self.heartbeat

        # ---- Bars section ----
        self.bars = BarsSection()
        self.bars.add_css_class("nst-expanded-bars")

        bar_specs = [
            ("signal", "Signal"),
            ("link_rate", "Link rate"),
            ("delivered", "Delivered"),
            ("retransmits", "Retransmits"),
            ("bufferbloat", "Bufferbloat"),
        ]
        self._bar_rows = {}
        for key, label in bar_specs:
            row = _BarRow(label)
            self._bar_rows[key] = row
            self.bars.add_bar(key, row.bar)
            self.bars.append(row.row)
            setattr(self, f"bar_{key}", row.bar)
            setattr(self, f"bar_{key}_row", row.row)
            setattr(self, f"bar_{key}_label", row.label)
            setattr(self, f"bar_{key}_value", row.value)
        # convenience aliases
        self.bar_link = self.bar_link_rate
        self.bar_bloat = self.bar_bufferbloat

        # ---- Latency section ----
        self.latency = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.latency.add_css_class("nst-expanded-latency")
        self.latency_title = Gtk.Label(label="Latency")
        self.latency_title.set_xalign(0.0)
        self.latency.append(self.latency_title)

        latency_specs = [
            ("avg", "Avg", "ping_avg_ms"),
            ("max", "Max", "ping_max_ms"),
            ("jitter", "Jitter", "jitter_ms"),
            ("loss", "Loss", "ping_loss_pct"),
            ("dns", "DNS", "dns_ms"),
            ("gateway", "Gateway", "gateway_ms"),
            ("drops", "Drops", "rx_dropped_rate"),
            ("wan_bloat", "WAN bloat", "wan_bloat_ms"),
        ]
        self._latency_labels = {}
        for key, label, _ in latency_specs:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            lbl = Gtk.Label(label=label)
            lbl.set_xalign(0.0)
            val = Gtk.Label(label="\u2014")
            val.set_xalign(1.0)
            row.append(lbl)
            row.append(val)
            self.latency.append(row)
            self._latency_labels[key] = val
            setattr(self, f"latency_{key}_label", val)
            setattr(self, f"{key}_label", val)
            setattr(self, f"{key}_value_label", val)
        # extra aliases
        self.ping_avg_label = self.latency_avg_label
        self.ping_max_label = self.latency_max_label
        self.jitter_label = self.latency_jitter_label
        self.loss_label = self.latency_loss_label
        self.dns_label = self.latency_dns_label
        self.gateway_label = self.latency_gateway_label
        self.drops_label = self.latency_drops_label
        self.rx_drops_label = self.latency_drops_label
        self.wan_bloat_label = self.latency_wan_bloat_label
        self.bufferbloat_wan_label = self.latency_wan_bloat_label
        self.latency_section = self.latency

        # ---- Devices section ----
        self.devices = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.devices.add_css_class("nst-expanded-devices")
        self.devices_title = Gtk.Label(label="Devices")
        self.devices_title.set_xalign(0.0)
        self.devices.append(self.devices_title)
        self.devices_box = self.devices
        self.devices_list = self.devices
        self.device_labels = {}
        self.devices_section = self.devices

        # ---- Addons section ----
        self.addons = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.addons.add_css_class("nst-expanded-addons")
        self.addons_title = Gtk.Label(label="Addons")
        self.addons_title.set_xalign(0.0)
        self.addons.append(self.addons_title)
        self.addons_box = self.addons
        self.addons_section = self.addons
        self.module_widgets = {}
        self._modules = []

        # ---- Actions section ----
        self.actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.actions.add_css_class("nst-expanded-actions")
        self.run_speed_test_button = Gtk.Button(label="Run speed test now")
        self.copy_diagnostics_button = Gtk.Button(label="Copy diagnostics")
        self.open_terminal_button = Gtk.Button(label="Open in terminal")
        self.actions.append(self.run_speed_test_button)
        self.actions.append(self.copy_diagnostics_button)
        self.actions.append(self.open_terminal_button)
        self.buttons = [self.run_speed_test_button,
                        self.copy_diagnostics_button,
                        self.open_terminal_button]
        self.action_buttons = list(self.buttons)
        self.actions_row = self.actions

        # Wire optional callbacks.
        self._on_run_speed_test = None
        self._on_copy_diagnostics = None
        self._on_open_terminal = None
        try:
            self.run_speed_test_button.connect("clicked", lambda *_: self._fire("run"))
        except Exception:
            pass
        try:
            self.copy_diagnostics_button.connect("clicked", lambda *_: self._fire("copy"))
        except Exception:
            pass
        try:
            self.open_terminal_button.connect("clicked", lambda *_: self._fire("terminal"))
        except Exception:
            pass

        # ---- Assemble ----
        self.append(self.hero)
        self.append(self.heartbeat)
        self.append(self.bars)
        self.append(self.latency)
        self.append(self.devices)
        self.append(self.addons)
        self.append(self.actions)

        # Optional callbacks setters.
        self.on_run_speed_test = None
        self.on_copy_diagnostics = None
        self.on_open_terminal = None

    # ------------------------------------------------------------------ #
    # Callback plumbing
    # ------------------------------------------------------------------ #
    def _fire(self, kind):
        cb = None
        if kind == "run":
            cb = self.on_run_speed_test or self._on_run_speed_test
        elif kind == "copy":
            cb = self.on_copy_diagnostics or self._on_copy_diagnostics
        elif kind == "terminal":
            cb = self.on_open_terminal or self._on_open_terminal
        if callable(cb):
            try:
                cb()
            except Exception:
                pass

    def set_callbacks(self, run=None, copy=None, terminal=None):
        if run is not None:
            self.on_run_speed_test = run
            self._on_run_speed_test = run
        if copy is not None:
            self.on_copy_diagnostics = copy
            self._on_copy_diagnostics = copy
        if terminal is not None:
            self.on_open_terminal = terminal
            self._on_open_terminal = terminal

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _set_label(self, widget, text):
        if widget is None:
            return
        for method in ("set_label", "set_text", "set_markup"):
            try:
                getattr(widget, method)(str(text))
                return
            except Exception:
                continue
        try:
            widget.set_property("label", str(text))
        except Exception:
            pass

    def _set_bar(self, bar_widget, pct, state=None):
        if bar_widget is None:
            return
        pct = max(0.0, min(100.0, float(pct or 0.0)))
        for css_class in _WIDTH_CLASSES:
            try:
                bar_widget.remove_css_class(css_class)
            except Exception:
                pass
        bucket = int(round(pct / 5.0) * 5)
        bucket = max(0, min(100, bucket))
        try:
            bar_widget.add_css_class(f"nst-bar--w-{bucket}")
        except Exception:
            pass
        if state is not None:
            st = _normalize_state(state)
            for css_class in _STATE_CLASSES:
                try:
                    bar_widget.remove_css_class(css_class)
                except Exception:
                    pass
            for css_class in (st, f"nst-{st}", f"nst-state-{st}"):
                try:
                    bar_widget.add_css_class(css_class)
                except Exception:
                    pass
        try:
            _animate_bar_size(
                bar_widget,
                pct,
                lambda value: bar_widget.set_size_request(
                    -1, max(2, int(40 * float(value) / 100.0))
                ),
                enabled=getattr(self, "_animate", True),
            )
        except Exception:
            try:
                bar_widget.set_size_request(-1, max(2, int(40 * pct / 100.0)))
            except Exception:
                pass
        try:
            bar_widget.set_tooltip_text(f"{pct:.0f}%")
        except Exception:
            pass

    def _clear_box(self, box):
        try:
            child = box.get_first_child()
        except Exception:
            child = None
        while child is not None:
            try:
                nxt = child.get_next_sibling()
            except Exception:
                nxt = None
            try:
                box.remove(child)
            except Exception:
                pass
            child = nxt

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
    def update(self, sample=None, verdict=None, probe_result=None, devices=None, modules=None):
        self._sample = sample
        if verdict is not None:
            self._verdict = verdict
        if probe_result is not None:
            self._probe_result = probe_result
        if devices is not None:
            self._devices = list(devices)
        if modules is not None:
            self._modules = list(modules)
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

        # ---- Hero ----
        rx_bps = _to_float(_attr(sample, "rx_bps", "rx_rate_bps", "download_bps", default=0.0))
        tx_bps = _to_float(_attr(sample, "tx_bps", "tx_rate_bps", "upload_bps", default=0.0))
        rx_mbps = rx_bps / 1e6
        tx_mbps = tx_bps / 1e6
        self._set_label(self.hero_value, f"{rx_mbps:.1f} Mbps")
        vstr = _verdict_str(verdict if verdict is not None else self._verdict)
        if vstr is None:
            vstr = _verdict_str(self._verdict)
        self._set_label(self.verdict_label, vstr if vstr is not None else "\u2014")

        # heartbeat
        try:
            if self.heartbeat is not None and hasattr(self.heartbeat, "add_sample"):
                self.heartbeat.add_sample(rx_mbps)
        except Exception:
            pass

        # ---- Bars ----
        signal_dbm = _to_float(_attr(sample, "signal_dbm", "signal", default=0.0))
        signal_pct = max(0.0, min(100.0, (signal_dbm + 90.0) / 40.0 * 100.0))
        signal_state = "good" if signal_dbm >= -67 else ("warn" if signal_dbm >= -75 else "bad")
        row = self._bar_rows.get("signal")
        if row is not None:
            self._set_label(row.value, f"{signal_dbm:.0f} dBm")
            self._set_bar(row.bar, signal_pct, signal_state)

        link_rate = _to_float(_attr(sample, "rx_bitrate_mbps", "rx_bitrate", "link_rate_mbps",
                                   "link_rate", "tx_bitrate_mbps", "tx_bitrate", default=0.0))
        if link_rate <= 0:
            link_rate = _to_float(_attr(sample, "rx_bitrate", default=0.0))
        link_pct = 100.0 if link_rate >= 100 else max(0.0, link_rate)
        if link_rate > 100:
            link_pct = 100.0
        link_state = "good" if link_rate >= 100 else ("warn" if link_rate >= 30 else "bad")
        row = self._bar_rows.get("link_rate")
        if row is not None:
            self._set_label(row.value, f"{link_rate:.0f} Mbps")
            self._set_bar(row.bar, link_pct, link_state)

        delivered_pct = min(100.0, rx_mbps / 38.0 * 100.0) if rx_mbps else 0.0
        delivered_state = "good" if rx_mbps >= 15 else ("warn" if rx_mbps >= 5 else "bad")
        row = self._bar_rows.get("delivered")
        if row is not None:
            self._set_label(row.value, f"{rx_mbps:.1f} Mbps")
            self._set_bar(row.bar, delivered_pct, delivered_state)

        retransmits = _to_float(_attr(sample, "tx_retries", "retransmits", "tx_retry",
                                     default=0.0))
        try:
            retransmits = int(retransmits)
        except Exception:
            pass
        retrans_pct = min(100.0, float(retransmits) * 10.0) if retransmits else 0.0
        retrans_state = "good" if not retransmits else "bad"
        row = self._bar_rows.get("retransmits")
        if row is not None:
            self._set_label(row.value, str(retransmits))
            self._set_bar(row.bar, retrans_pct, retrans_state)

        # bufferbloat: prefer probe_result? then sample
        bloat = _attr(sample, "bufferbloat_lan_ms", "bufferbloat_ms", "bloat_ms", default=None)
        if bloat is None and self._probe_result is not None:
            bloat = _attr(self._probe_result, "bufferbloat_lan_ms", "delta_lan_ms",
                          "bufferbloat_ms", default=None)
        bloat_val = _to_float(bloat, 0.0) if bloat is not None else 0.0
        bloat_pct = min(100.0, bloat_val * 5.0)
        bloat_state = "good" if bloat_val <= 10 else ("warn" if bloat_val <= 30 else "bad")
        row = self._bar_rows.get("bufferbloat")
        if row is not None:
            self._set_label(row.value, f"{bloat_val:.1f} ms" if bloat is not None else "\u2014")
            self._set_bar(row.bar, bloat_pct, bloat_state)

        # ---- Latency ----
        def _set_lat(key, value, fmt=None):
            lbl = self._latency_labels.get(key)
            if lbl is None:
                return
            if value is None:
                self._set_label(lbl, "\u2014")
                return
            if fmt is not None:
                try:
                    self._set_label(lbl, fmt(value))
                    return
                except Exception:
                    pass
            self._set_label(lbl, str(value))

        ping_avg = _attr(sample, "ping_avg_ms", "ping_ms", "rtt_ms", default=None)
        ping_max = _attr(sample, "ping_max_ms", "ping_max", default=None)
        jitter = _attr(sample, "jitter_ms", "mdev_ms", default=None)
        loss = _attr(sample, "ping_loss_pct", "loss_pct", default=None)
        dns = _attr(sample, "dns_ms", default=None)
        gateway = _attr(sample, "gateway_ms", "gateway", default=None)
        drops = _attr(sample, "rx_dropped_rate", "rx_dropped_total", "drops", default=None)
        wan_bloat = _attr(sample, "bufferbloat_wan_ms", "wan_bloat_ms", default=None)
        if wan_bloat is None and self._probe_result is not None:
            wan_bloat = _attr(self._probe_result, "delta_wan_ms", "bufferbloat_wan_ms", default=None)

        _set_lat("avg", ping_avg, lambda v: f"{_to_float(v):.1f} ms")
        _set_lat("max", ping_max, lambda v: f"{_to_float(v):.1f} ms")
        _set_lat("jitter", jitter, lambda v: f"{_to_float(v):.1f} ms")
        _set_lat("loss", loss, lambda v: f"{_to_float(v):.1f}%")
        _set_lat("dns", dns, lambda v: f"{_to_float(v):.1f} ms")
        _set_lat("gateway", gateway, lambda v: f"{_to_float(v):.1f} ms")
        _set_lat("drops", drops, lambda v: f"{_to_float(v):.2f}")
        _set_lat("wan_bloat", wan_bloat, lambda v: f"{_to_float(v):.1f} ms")

        # ---- Devices ----
        self._clear_box(self.devices)
        # re-append title
        try:
            self.devices.append(self.devices_title)
        except Exception:
            pass
        self.device_labels = {}
        devs = self._devices if devices is None else list(devices)
        if not devs:
            devs = []
        if not devs:
            lbl = Gtk.Label(label="No devices")
            lbl.set_xalign(0.0)
            self.devices.append(lbl)
        else:
            for dev in devs:
                if isinstance(dev, dict):
                    name = dev.get("name") or dev.get("hostname") or dev.get("ip") or "device"
                    status = dev.get("status") or dev.get("state") or ""
                    ip = dev.get("ip") or dev.get("address") or ""
                else:
                    name = getattr(dev, "name", None) or getattr(dev, "hostname", None) or str(dev)
                    status = getattr(dev, "status", None) or getattr(dev, "state", None) or ""
                    ip = getattr(dev, "ip", None) or getattr(dev, "address", None) or ""
                text = str(name)
                if ip:
                    text += f"  ({ip})"
                if status:
                    text += f"  - {status}"
                lbl = Gtk.Label(label=text)
                lbl.set_xalign(0.0)
                self.devices.append(lbl)
                self.device_labels[str(name)] = lbl

        # ---- Addons ----
        try:
            self._clear_box(self.addons)
            try:
                self.addons.append(self.addons_title)
            except Exception:
                pass
            self.module_widgets = {}
            mods = self._modules
            for mod in mods:
                try:
                    try:
                        last = getattr(mod, "_nst_last_sample", object())
                        if last is not sample:
                            mod.update(sample)
                            try:
                                setattr(mod, "_nst_last_sample", sample)
                            except Exception:
                                pass
                    except Exception:
                        pass
                    widget = None
                    try:
                        widget = mod.render()
                    except Exception:
                        widget = None
                    if widget is not None:
                        try:
                            self.addons.append(widget)
                        except Exception:
                            pass
                        self.module_widgets[getattr(mod, "name", str(mod))] = widget
                except Exception:
                    pass
        except Exception:
            pass

        return self

    # aliases for update
    def refresh(self, *args, **kwargs):
        return self.update(*args, **kwargs)


    def set_modules(self, modules):
        self._modules = list(modules) if modules is not None else []
        return self


__all__ = ["ExpandedPanel", "BarsSection"]
