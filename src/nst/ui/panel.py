"""GTK4 layer-shell panel window."""

import logging

# Load the layer-shell CDLL *before* importing gi, per the plan/target names.
# Keep a guarded fallback so the module stays importable without the library.
_LAYER_SHELL_AVAILABLE = False
try:
    from ctypes import CDLL

    CDLL("libgtk4-layer-shell.so.0")
    _LAYER_SHELL_AVAILABLE = True
except Exception:  # pragma: no cover - environment dependent
    _LAYER_SHELL_AVAILABLE = False

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

try:
    from gi.repository import Gdk
except Exception:  # pragma: no cover
    Gdk = None

from nst.ui.tiles import TileGrid

try:
    from nst.ui.expanded import ExpandedPanel
except Exception:  # pragma: no cover - environment dependent
    ExpandedPanel = None

# Layer-shell is optional at import time; keep the module importable even
# when the library/version is unavailable or conflicts with the loaded Gtk.
Gtk4LayerShell = None
GtkLayerShell = None
if _LAYER_SHELL_AVAILABLE:
    try:
        gi.require_version("Gtk4LayerShell", "1.0")
        from gi.repository import Gtk4LayerShell
        GtkLayerShell = Gtk4LayerShell
    except Exception:  # pragma: no cover - environment dependent
        Gtk4LayerShell = None
        GtkLayerShell = None


logger = logging.getLogger("nst")


class NetworkPanel(Gtk.Window):
    """Transparent layer-shell panel window."""

    def __init__(self, application=None, **kwargs):
        self.application = application
        self.app = application
        if application is not None:
            kwargs["application"] = application
        super().__init__(**kwargs)

        self.set_decorated(False)
        self.set_default_size(434, 172)

        self._sample = None
        self._verdict = None
        self._probe_result = None
        self._devices = []
        self._expanded_visible = False
        self._modules = []

        self.config = getattr(application, "config", None)
        self.run_probe_callback = None
        self.on_run_probe = None
        self.probe_callback = None
        self.toggle_callback = None

        self.tile_grid = TileGrid()
        try:
            self.tile_grid.config = self.config
        except Exception:
            pass
        self.tiles = self.tile_grid.tiles

        if ExpandedPanel is not None:
            try:
                self.expanded_panel = ExpandedPanel()
                try:
                    self.expanded_panel.config = self.config
                except Exception:
                    pass
            except Exception:
                self.expanded_panel = None
        else:
            self.expanded_panel = None
        self.expanded = self.expanded_panel

        # Heartbeat graph for the collapsed view.
        try:
            from nst.ui.heartbeat import HeartbeatGraph
            self.heartbeat = HeartbeatGraph()
        except Exception:
            self.heartbeat = Gtk.Box()
        try:
            self.heartbeat.add_css_class("nst-heartbeat")
            self.heartbeat.add_css_class("nst-heartbeat-container")
        except Exception:
            pass
        self.heartbeat_graph = self.heartbeat
        self.graph = self.heartbeat
        self.heartbeat_container = self.heartbeat
        self.heartbeat_box = self.heartbeat

        # Title row: status dot, Wi-Fi icon, SSID title, verdict chip.
        self.title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        try:
            self.title_row.add_css_class("nst-title-row")
        except Exception:
            pass

        self.status_dot = Gtk.Box()
        try:
            self.status_dot.add_css_class("nst-status-dot")
            self.status_dot.set_size_request(7, 7)
        except Exception:
            pass

        self.wifi_icon = Gtk.Label(label="\uf1eb")
        try:
            self.wifi_icon.add_css_class("nst-wifi-icon")
        except Exception:
            pass

        self.title_label = Gtk.Label(label="NST")
        try:
            self.title_label.add_css_class("nst-title")
            self.title_label.set_xalign(0.0)
        except Exception:
            pass

        self.verdict_label = Gtk.Label(label="\u2014")
        try:
            self.verdict_label.add_css_class("nst-verdict-chip")
        except Exception:
            pass

        for _w in (self.status_dot, self.wifi_icon, self.title_label, self.verdict_label):
            try:
                self.title_row.append(_w)
            except Exception:
                pass

        # Footer.
        self.footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        try:
            self.footer.add_css_class("nst-footer")
        except Exception:
            pass
        self.footer_label = Gtk.Label(label="")
        try:
            self.footer_label.set_xalign(0.0)
        except Exception:
            pass
        try:
            self.footer.append(self.footer_label)
        except Exception:
            pass

        # Collapsed view as a vertical box.
        self.collapsed_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        try:
            self.collapsed_box.add_css_class("nst-panel")
            self.collapsed_box.add_css_class("nst-collapsed")
        except Exception:
            pass
        for _w in (self.title_row, self.tile_grid, self.heartbeat, self.footer):
            try:
                self.collapsed_box.append(_w)
            except Exception:
                pass
        self.collapsed = self.collapsed_box
        self.collapsed_view = self.collapsed_box
        self.collapsed_container = self.collapsed_box
        self.content_box = self.collapsed_box
        self.main_box = self.collapsed_box

        # Four corner bracket widgets (targeting-reticle aesthetic).
        self.corner_brackets = []
        self.top_left_bracket = None
        self.top_right_bracket = None
        self.bottom_left_bracket = None
        self.bottom_right_bracket = None
        self.brackets = {}
        self._corner_overlay = None
        try:
            overlay = Gtk.Overlay()
            overlay.set_child(self.collapsed_box)
            specs = [
                ("\u250c", Gtk.Align.START, Gtk.Align.START, "top_left"),
                ("\u2510", Gtk.Align.END, Gtk.Align.START, "top_right"),
                ("\u2514", Gtk.Align.START, Gtk.Align.END, "bottom_left"),
                ("\u2518", Gtk.Align.END, Gtk.Align.END, "bottom_right"),
            ]
            for ch, halign, valign, key in specs:
                lbl = Gtk.Label(label=ch)
                try:
                    lbl.add_css_class("nst-corner-bracket")
                    lbl.add_css_class("nst-corner")
                except Exception:
                    pass
                try:
                    lbl.set_halign(halign)
                    lbl.set_valign(valign)
                except Exception:
                    pass
                try:
                    overlay.add_overlay(lbl)
                except Exception:
                    pass
                self.corner_brackets.append(lbl)
                setattr(self, key + "_bracket", lbl)
                self.brackets[key] = lbl
            self._corner_overlay = overlay
            self.set_child(overlay)
        except Exception:
            try:
                self.set_child(self.collapsed_box)
            except Exception:
                pass

        # Keyboard shortcuts.
        try:
            controller = Gtk.EventControllerKey()
            controller.connect("key-pressed", self._on_key_pressed)
            self.add_controller(controller)
            self._key_controller = controller
        except Exception:
            self._key_controller = None

        self._setup_layer_shell()

    def _layer_shell(self):
        return globals().get("Gtk4LayerShell") or globals().get("GtkLayerShell")

    def _setup_layer_shell(self):
        ls = self._layer_shell()
        if ls is None:
            return
        try:
            ls.init_for_window(self)
            ls.set_layer(self, ls.Layer.TOP)
            ls.set_namespace(self, "netstatus")
            ls.set_anchor(self, ls.Edge.BOTTOM, True)
            ls.set_anchor(self, ls.Edge.LEFT, True)
            ls.set_exclusive_zone(self, 0)
            ls.set_keyboard_mode(self, ls.KeyboardMode.NONE)
            ls.set_margin(self, ls.Edge.BOTTOM, 34)
        except Exception:
            pass

    def _trigger_probe(self):
        cb = None
        for attr in ("run_probe_callback", "on_run_probe", "probe_callback", "run_probe",
                     "_run_probe", "_on_run_probe", "on_probe", "_on_probe"):
            cb = getattr(self, attr, None)
            if callable(cb):
                break
        if cb is None and getattr(self, "application", None) is not None:
            app = self.application
            for name in ("run_probe_now", "run_probe", "trigger_probe", "on_run_probe",
                             "on_probe", "probe"):
                cb = getattr(app, name, None)
                if callable(cb):
                    break
        if cb is None and getattr(self, "app", None) is not None and self.app is not self.application:
            app = self.app
            for name in ("run_probe_now", "run_probe", "trigger_probe", "on_run_probe",
                         "on_probe", "probe"):
                cb = getattr(app, name, None)
                if callable(cb):
                    break
        if callable(cb):
            try:
                cb()
            except Exception as exc:
                logger.debug("Probe trigger failed: %s", exc)
        return True

    def _on_key_pressed(self, controller=None, keyval=0, keycode=0, state=0):
        # Normalize callers that pass (keyval, keycode, state) positionally.
        if isinstance(controller, int) and not isinstance(keyval, int):
            state = keycode
            keycode = keyval
            keyval = controller
            controller = None
        try:
            keyval = int(keyval)
        except (TypeError, ValueError):
            try:
                keyval = int(getattr(keyval, "value", keyval))
            except Exception:
                keyval = 0
        try:
            state = int(state or 0)
        except (TypeError, ValueError):
            state = 0

        ctrl = False
        if Gdk is not None:
            try:
                ctrl = bool(state & int(Gdk.ModifierType.CONTROL_MASK))
            except Exception:
                ctrl = bool(state & 4)
        else:
            ctrl = bool(state & 4)

        escape_val = None
        r_vals = set()
        e_vals = set()
        return_vals = set()
        if Gdk is not None:
            escape_val = getattr(Gdk, "KEY_Escape", None)
            for name in ("KEY_r", "KEY_R"):
                v = getattr(Gdk, name, None)
                if v is not None:
                    r_vals.add(v)
            for name in ("KEY_e", "KEY_E"):
                v = getattr(Gdk, name, None)
                if v is not None:
                    e_vals.add(v)
            for name in ("KEY_Return", "KEY_KP_Enter"):
                v = getattr(Gdk, name, None)
                if v is not None:
                    return_vals.add(v)
        if escape_val is None:
            escape_val = 0xFF1B
        if not r_vals:
            r_vals = {ord("r"), ord("R")}
        if not e_vals:
            e_vals = {ord("e"), ord("E")}

        if keyval == escape_val:
            try:
                self.show_collapsed()
            except Exception as exc:
                logger.debug("show_collapsed failed: %s", exc)
            self._expanded_visible = False
            return True

        if ctrl and keyval in r_vals:
            self._trigger_probe()
            return True

        if ctrl and keyval in e_vals:
            try:
                self.show_expanded()
            except Exception as exc:
                logger.debug("show_expanded failed: %s", exc)
            self._expanded_visible = True
            return True

        return False

    def handle_key(self, keyval, state=0, keycode=0):
        return self._on_key_pressed(None, keyval, keycode, state)

    def handle_key_press(self, keyval, state=0, keycode=0):
        return self.handle_key(keyval, state, keycode)

    def show_collapsed(self):
        self._expanded_visible = False
        self.set_default_size(434, 172)
        ls = self._layer_shell()
        if ls is not None:
            try:
                ls.set_keyboard_mode(self, ls.KeyboardMode.NONE)
                ls.set_anchor(self, ls.Edge.BOTTOM, True)
                ls.set_anchor(self, ls.Edge.LEFT, True)
                ls.set_margin(self, ls.Edge.BOTTOM, 34)
            except Exception:
                pass
        child = getattr(self, "_corner_overlay", None)
        if child is None:
            child = getattr(self, "tile_grid", None)
        if child is not None:
            try:
                self.set_child(child)
            except Exception:
                pass
        self.present()

    def show_expanded(self):
        self._expanded_visible = True
        self.set_default_size(560, 520)
        ls = self._layer_shell()
        if ls is not None:
            try:
                ls.set_keyboard_mode(self, ls.KeyboardMode.ON_DEMAND)
            except Exception:
                pass
        if getattr(self, "expanded_panel", None) is not None:
            try:
                self.expanded_panel.update(self._sample, self._verdict, self._probe_result, self._devices, self._modules)
            except Exception:
                pass
            try:
                self.set_child(self.expanded_panel)
            except Exception:
                pass
        self.present()

    def toggle_expanded(self):
        if getattr(self, "_expanded_visible", False):
            self.show_collapsed()
        else:
            self.show_expanded()
        return self

    def open_expanded(self):
        self.show_expanded()
        return self

    def close_expanded(self):
        self.show_collapsed()
        return self

    def update(self, sample=None, verdict=None, probe_result=None, devices=None, modules=None):
        self._sample = sample
        if modules is not None:
            self._modules = list(modules)
        if getattr(self, "tile_grid", None) is not None:
            try:
                self.tile_grid.config = self.config
            except Exception:
                pass
        if getattr(self, "expanded_panel", None) is not None:
            try:
                self.expanded_panel.config = self.config
            except Exception:
                pass
        if verdict is not None:
            self._verdict = verdict
        if probe_result is not None:
            self._probe_result = probe_result
        if devices is not None:
            self._devices = list(devices)
        if modules is not None:
            self._modules = list(modules)

        # Refresh collapsed title/verdict/heartbeat from sample/verdict.
        try:
            def _attr(obj, *names, default=None):
                if obj is None:
                    return default
                if isinstance(obj, dict):
                    for n in names:
                        if n in obj and obj[n] is not None:
                            return obj[n]
                    return default
                for n in names:
                    if hasattr(obj, n):
                        v = getattr(obj, n)
                        if v is not None:
                            return v
                return default

            # Title (SSID / interface).
            title_text = _attr(sample, "ssid", "ssid_name", "wifi_ssid", "interface", "iface", default=None)
            if title_text is None and self.config is not None:
                title_text = getattr(self.config, "interface", None) or getattr(self.config, "ssid", None)
            if title_text is not None and getattr(self, "title_label", None) is not None:
                try:
                    self.title_label.set_label(str(title_text))
                except Exception:
                    try:
                        self.title_label.set_text(str(title_text))
                    except Exception:
                        pass

            # Verdict chip.
            vstr = None
            if self._verdict is not None:
                vstr = getattr(self._verdict, "value", self._verdict)
            vstr = None if vstr is None else str(vstr)
            if vstr is not None and getattr(self, "verdict_label", None) is not None:
                try:
                    self.verdict_label.set_label(vstr)
                except Exception:
                    try:
                        self.verdict_label.set_text(vstr)
                    except Exception:
                        pass
                # State classes.
                state = vstr.strip().upper()
                mapping = {
                    "HEALTHY": "ok",
                    "ISP_LIMITED": "warn",
                    "HIGH_LATENCY": "warn",
                    "RADIO_DEGRADED": "bad",
                }
                cls = mapping.get(state, "warn")
                managed = {"ok", "good", "healthy", "warn", "warning", "bad", "error", "critical"}
                for c in managed:
                    try:
                        self.verdict_label.remove_css_class(c)
                    except Exception:
                        pass
                try:
                    self.verdict_label.add_css_class(cls)
                except Exception:
                    pass
                # status dot
                if getattr(self, "status_dot", None) is not None:
                    for c in managed:
                        try:
                            self.status_dot.remove_css_class(c)
                        except Exception:
                            pass
                    try:
                        self.status_dot.add_css_class(cls)
                    except Exception:
                        pass

            # Heartbeat.
            hb = getattr(self, "heartbeat", None)
            if hb is not None and hasattr(hb, "add_sample"):
                try:
                    rx_bps = _attr(sample, "rx_bps", "rx_rate_bps", "download_bps", default=0.0)
                    hb.add_sample(float(rx_bps or 0.0) / 1e6)
                except Exception:
                    pass
        except Exception:
            pass

        if getattr(self, "tile_grid", None) is not None:
            try:
                self.tile_grid.update(self._sample, self._verdict)
            except Exception:
                pass
        if getattr(self, "expanded_panel", None) is not None:
            try:
                self.expanded_panel.update(self._sample, self._verdict, self._probe_result, self._devices, self._modules)
            except Exception:
                pass

    def handle_key(self, keyval, state=0, keycode=0):
        return self._on_key_pressed(None, keyval, keycode, state)

    def handle_key_press(self, keyval, state=0, keycode=0):
        return self.handle_key(keyval, state, keycode)

    def set_verdict(self, verdict=None):
        try:
            self.update(self._sample, verdict, self._probe_result, self._devices, self._modules)
        except Exception:
            self._verdict = verdict
